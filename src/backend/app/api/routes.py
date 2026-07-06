"""
API路由定义
文件上传、MIB解析、模板配置、XML导出、翻译管理、任务缓存
"""
import os
import json
import uuid
from pathlib import Path
from typing import List, Optional, Dict
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from ..models.schemas import (
    TemplateConfig, MIBParseResult, ExportTask,
    TranslationEntry, ValidateResult
)
from ..core.config import UPLOAD_DIR, ALLOWED_EXTENSIONS, DEFAULTS
from ..core.database import (
    save_task, get_task, list_tasks, delete_task,
    save_translation, list_translations, delete_translation,
    save_classify_rule, list_classify_rules
)
from ..core.translate import get_all_translations
from ..services.mib_parser import parse_mib_files
from ..services.xml_generator import ZabbixXMLGenerator, validate_xml_structure

router = APIRouter(prefix="/api", tags=["mib-tool"])


# ===== 文件上传 =====

@router.post("/upload")
async def upload_mib_files(files: List[UploadFile] = File(...)):
    """
    上传MIB文件
    支持 .mib .txt 格式，单个或批量
    """
    uploaded = []
    errors = []

    for file in files:
        # 检查文件扩展名
        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            errors.append(f"{file.filename}: 不支持的文件格式 {ext}")
            continue

        # 保存文件
        save_path = UPLOAD_DIR / file.filename
        try:
            content = await file.read()
            # 检查文件大小
            if len(content) > 50 * 1024 * 1024:  # 50MB
                errors.append(f"{file.filename}: 文件过大(>50MB)")
                continue
            with open(save_path, "wb") as f:
                f.write(content)
            uploaded.append(file.filename)
        except Exception as e:
            errors.append(f"{file.filename}: 上传失败 - {str(e)}")

    return {
        "success": len(uploaded) > 0,
        "uploaded": uploaded,
        "errors": errors,
        "message": f"成功上传 {len(uploaded)} 个文件" + (f"，{len(errors)} 个失败" if errors else ""),
    }


# ===== MIB解析 =====

class ParseRequest(BaseModel):
    filenames: List[str]
    vendor_oid: str = ""
    config: Optional[dict] = None


@router.post("/parse")
async def parse_mib(request: ParseRequest):
    """
    解析已上传的MIB文件
    返回解析结果: 静态指标列表、LLD自动发现实例、分类统计
    """
    # 检查文件是否存在
    for filename in request.filenames:
        if not (UPLOAD_DIR / filename).exists():
            raise HTTPException(status_code=404, detail=f"文件不存在: {filename}")

    result = parse_mib_files(request.filenames, request.vendor_oid)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)

    # 保存完整的模板配置 (用于复用)
    config_data = request.config or {}
    config_data["vendor_oid"] = request.vendor_oid

    save_task(
        task_id=result.task_id,
        filename=",".join(request.filenames),
        config_json=json.dumps(config_data, ensure_ascii=False),
        parse_result_json=result.json(),
        status="parsed",
        message=result.message,
    )

    return result


# ===== 模板配置 =====

@router.get("/config/defaults")
async def get_default_config():
    """获取默认配置"""
    return DEFAULTS


# ===== 发现规则选择 =====

@router.get("/discovery-rules/{task_id}")
async def get_discovery_rules(task_id: str):
    """
    获取任务可生成的发现规则列表
    供用户选择后再导出
    """
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if not task["parse_result_json"]:
        raise HTTPException(status_code=400, detail="任务无解析结果")

    parse_result = MIBParseResult.parse_raw(task["parse_result_json"])

    rules = []
    for table_key, items in parse_result.discovery_items.items():
        # 取第一个item推断表名
        entry_name = ""
        hw_group = "system"
        for item in items:
            if "entry" in item.name.lower():
                entry_name = item.chinese_name or item.name
                hw_group = item.discovery_group.value
                break
        if not entry_name:
            for item in items:
                if "index" not in item.name.lower():
                    entry_name = item.chinese_name or item.name
                    hw_group = item.discovery_group.value
                    break

        # 统计指标类型
        status_count = sum(1 for i in items if i.category.value == "status")
        perf_count = sum(1 for i in items if i.category.value == "performance")
        info_count = sum(1 for i in items if i.category.value == "info")
        has_trigger = any(i.is_health for i in items)

        rules.append({
            "table_key": table_key,
            "name": entry_name,
            "hw_group": hw_group,
            "item_count": len(items),
            "status_count": status_count,
            "perf_count": perf_count,
            "info_count": info_count,
            "has_trigger": has_trigger,
            "sample_items": [
                {"name": i.chinese_name or i.name, "key": i.zabbix_key, "category": i.category.value}
                for i in items[:5]
            ],
        })

    return {
        "task_id": task_id,
        "total_rules": len(rules),
        "rules": rules,
    }


@router.get("/discovery-rules/{task_id}/prototypes")
async def get_prototypes(task_id: str, table_key: str):
    """
    获取指定发现规则下的所有监控项原型
    供用户选择哪些原型需要生成
    """
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if not task["parse_result_json"]:
        raise HTTPException(status_code=400, detail="任务无解析结果")

    parse_result = MIBParseResult.parse_raw(task["parse_result_json"])

    items = parse_result.discovery_items.get(table_key, [])
    if not items:
        raise HTTPException(status_code=404, detail=f"未找到发现规则: {table_key}")

    prototypes = []
    for item in items:
        prototypes.append({
            "oid": item.oid,
            "name": item.chinese_name or item.name,
            "english_name": item.name,
            "zabbix_key": item.zabbix_key,
            "category": item.category.value,
            "delay": item.delay,
            "value_type": "FLOAT" if item.value_type == 0 else "TEXT",
            "unit": item.unit or "",
            "trends": item.trends,
            "is_health": item.is_health,
        })

    return {
        "task_id": task_id,
        "table_key": table_key,
        "total": len(prototypes),
        "prototypes": prototypes,
    }


# ===== XML导出 =====

class ExportRequest(BaseModel):
    task_id: str
    config: TemplateConfig
    selected_rules: Optional[List[str]] = None  # 选中的发现规则table_key列表，None=全部
    rule_prototypes: Optional[Dict[str, List[str]]] = None  # 每个规则选中的原型OID列表


@router.post("/export")
async def export_zabbix_xml(request: ExportRequest):
    """
    导出Zabbix 6.4 XML模板
    selected_rules: 选中的发现规则table_key列表，None或空=全部导出
    rule_prototypes: 每个规则内选中的原型OID列表，{table_key: [oid1, oid2, ...]}
    """
    # 获取解析结果
    task = get_task(request.task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在，请先解析MIB文件")

    if not task["parse_result_json"]:
        raise HTTPException(status_code=400, detail="任务无解析结果")

    parse_result = MIBParseResult.parse_raw(task["parse_result_json"])

    # 过滤发现规则
    if request.selected_rules is not None:
        filtered = {
            k: v for k, v in parse_result.discovery_items.items()
            if k in request.selected_rules
        }
        parse_result.discovery_items = filtered

    # 过滤每个规则内的原型
    if request.rule_prototypes:
        for table_key, selected_oids in request.rule_prototypes.items():
            if table_key in parse_result.discovery_items:
                parse_result.discovery_items[table_key] = [
                    item for item in parse_result.discovery_items[table_key]
                    if item.oid in selected_oids
                ]

    # 生成XML
    generator = ZabbixXMLGenerator(request.config)
    xml_content = generator.generate(parse_result)

    # 校验XML结构
    validation = validate_xml_structure(xml_content)
    if not validation.valid:
        raise HTTPException(
            status_code=400,
            detail=f"XML结构校验失败: {'; '.join(validation.errors)}"
        )

    # 更新任务记录
    save_task(
        task_id=request.task_id,
        filename=task["filename"],
        config_json=request.config.json(),
        parse_result_json=task["parse_result_json"],
        xml_content=xml_content,
        status="exported",
        message="XML导出成功",
    )

    # 返回XML文件下载
    filename = f"{request.config.get_template_id()}_zabbix6.4.xml"
    return Response(
        content=xml_content.encode("utf-8"),
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/export/preview")
async def preview_xml(request: ExportRequest):
    """
    预览XML内容 (不触发下载)
    """
    task = get_task(request.task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if not task["parse_result_json"]:
        raise HTTPException(status_code=400, detail="任务无解析结果")

    parse_result = MIBParseResult.parse_raw(task["parse_result_json"])

    # 如果指定了选中的发现规则，过滤掉未选中的
    if request.selected_rules is not None:
        filtered = {
            k: v for k, v in parse_result.discovery_items.items()
            if k in request.selected_rules
        }
        parse_result.discovery_items = filtered

    # 过滤每个规则内的原型
    if request.rule_prototypes:
        for table_key, selected_oids in request.rule_prototypes.items():
            if table_key in parse_result.discovery_items:
                parse_result.discovery_items[table_key] = [
                    item for item in parse_result.discovery_items[table_key]
                    if item.oid in selected_oids
                ]

    generator = ZabbixXMLGenerator(request.config)
    xml_content = generator.generate(parse_result)

    validation = validate_xml_structure(xml_content)

    return {
        "xml_preview": xml_content[:5000] + ("..." if len(xml_content) > 5000 else ""),
        "xml_length": len(xml_content),
        "validation": validation.dict(),
    }


# ===== 预览数据 =====

@router.get("/preview/{task_id}")
async def get_preview_data(task_id: str, page: int = 1, page_size: int = 20):
    """
    获取解析结果的分页预览
    支持静态指标列表、LLD发现实例、触发器规则预览
    """
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if not task["parse_result_json"]:
        raise HTTPException(status_code=400, detail="任务无解析结果")

    parse_result = MIBParseResult.parse_raw(task["parse_result_json"])

    # 静态指标分页
    start = (page - 1) * page_size
    end = start + page_size
    static_page = parse_result.static_items[start:end]

    return {
        "task_id": task_id,
        "total_oids": parse_result.total_oids,
        "static_items": {
            "total": len(parse_result.static_items),
            "page": page,
            "page_size": page_size,
            "items": [item.dict() for item in static_page],
        },
        "discovery_groups": {
            group_name: {
                "count": len(items),
                "items": [item.dict() for item in items[:5]],  # 预览前5个
            }
            for group_name, items in parse_result.discovery_items.items()
        },
        "health_triggers": [
            item.dict() for item in parse_result.parsed_oids if item.is_health
        ],
    }


# ===== 翻译管理 =====

@router.get("/translations")
async def get_translations():
    """获取全部翻译 (内置+自定义)"""
    builtin = get_all_translations()
    custom = list_translations()
    return {
        "builtin_count": len(builtin),
        "custom": custom,
        "all": builtin,
    }


@router.post("/translations")
async def add_translation(entry: TranslationEntry):
    """新增/修改翻译词条"""
    save_translation(entry.english, entry.chinese, entry.category or "")
    return {"success": True, "message": f"已保存: {entry.english} → {entry.chinese}"}


@router.delete("/translations/{english}")
async def remove_translation(english: str):
    """删除自定义翻译词条"""
    deleted = delete_translation(english)
    if not deleted:
        raise HTTPException(status_code=404, detail="词条不存在")
    return {"success": True, "message": f"已删除: {english}"}


# ===== 分类规则管理 =====

@router.get("/classify-rules")
async def get_classify_rules():
    """获取分类规则"""
    return list_classify_rules()


@router.post("/classify-rules")
async def add_classify_rule(keyword: str = Form(...), category: str = Form(...), delay: str = Form(...)):
    """新增分类规则"""
    save_classify_rule(keyword, category, delay)
    return {"success": True}


# ===== 任务管理 =====

@router.get("/tasks")
async def get_task_list(limit: int = 50):
    """列出历史任务"""
    return list_tasks(limit)


@router.get("/tasks/{task_id}")
async def get_task_detail(task_id: str):
    """获取任务详情"""
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@router.delete("/tasks/{task_id}")
async def remove_task(task_id: str):
    """删除任务"""
    deleted = delete_task(task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"success": True, "message": "任务已删除"}
