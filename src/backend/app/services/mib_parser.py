"""
MIB解析引擎
使用 pysmi 1.5+ 解析MIB文件，提取OID节点信息
"""
import os
import time
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from pysmi.reader import FileReader
from pysmi.searcher import StubSearcher
from pysmi.writer import PyFileWriter
from pysmi.compiler import MibCompiler
from pysmi.parser.smiv2 import SmiV2Parser
from pysmi.codegen import JsonCodeGen

from ..models.schemas import ParsedOID, MIBParseResult, ItemCategory, DiscoveryGroup
from ..core.classify import auto_classify_oid
from ..core.config import UPLOAD_DIR, DATA_DIR

# 内置标准OID根定义 (来自RFC/SNMPv2-SMI等标准MIB)
# 当上传的MIB文件 IMPORTS 这些符号时，可以直接解析
WELL_KNOWN_OIDS = {
    # RFC1155-SMI / RFC1213-MIB 根节点
    "iso": "1",
    "org": "1.3",
    "dod": "1.3.6",
    "internet": "1.3.6.1",
    "mgmt": "1.3.6.1.2",
    "mib-2": "1.3.6.1.2.1",
    "transmission": "1.3.6.1.2.1.10",
    "experimental": "1.3.6.1.3",
    "private": "1.3.6.1.4",
    "enterprises": "1.3.6.1.4.1",
    "security": "1.3.6.1.5",
    "snmpV2": "1.3.6.1.6",
    # 常见厂商
    "ibm": "1.3.6.1.4.1.2",
    "hp": "1.3.6.1.4.1.11",
    "cisco": "1.3.6.1.4.1.9",
    "dell": "1.3.6.1.4.1.674",
    "lenovo": "1.3.6.1.4.1.53184",
    "huawei": "1.3.6.1.4.1.2011",
    "h3c": "1.3.6.1.4.1.25506",
    "zte": "1.3.6.1.4.1.3902",
    "intel": "1.3.6.1.4.1.343",
    "microsoft": "1.3.6.1.4.1.311",
    "vmware": "1.3.6.1.4.1.6876",
    # SNMPv2-SMI 常用节点
    "zeroDotZero": "0.0",
    "snmpModules": "1.3.6.1.6.3",
}


class MIBParser:
    """MIB文件解析器 (pysmi 1.5+)"""

    def __init__(self):
        self._compiled_dir = DATA_DIR / "compiled_mibs"
        self._compiled_dir.mkdir(exist_ok=True)
        # 合并内置OID到解析上下文
        self._builtin_oids = dict(WELL_KNOWN_OIDS)

    def parse_uploaded_files(self, filenames: List[str], vendor_oid: str = "") -> MIBParseResult:
        """
        解析上传的MIB文件
        参数:
            filenames: 已上传到UPLOAD_DIR的文件名列表
            vendor_oid: 厂商前缀OID (如 1.3.6.1.4.1.53184)
        返回:
            MIBParseResult 解析结果
        """
        start_time = time.time()
        task_id = f"task_{int(time.time())}"

        try:
            upload_dir = str(UPLOAD_DIR)
            compiled_dir = str(self._compiled_dir)

            # 1. 使用pysmi编译MIB文件
            parser = SmiV2Parser()
            codegen = JsonCodeGen()
            writer = PyFileWriter(compiled_dir)

            compiler = MibCompiler(parser, codegen, writer)
            compiler.add_sources(FileReader(upload_dir))
            compiler.add_searchers(StubSearcher())

            compiled_modules = []
            compile_errors = []

            for filename in filenames:
                module_name = Path(filename).stem.upper()
                try:
                    results = compiler.compile(module_name)
                    for mib_name, status in results.items():
                        if str(status) == "compiled":
                            compiled_modules.append(mib_name)
                        else:
                            compile_errors.append(f"{mib_name}: {status}")
                except Exception as e:
                    compile_errors.append(f"{filename}: {str(e)}")

            # 2. 尝试从编译后的JSON提取OID
            all_oids = []
            seen_oids = set()

            for module_name in compiled_modules:
                oids = self._extract_oids_from_json(module_name, vendor_oid)
                for oid in oids:
                    if oid.oid not in seen_oids:
                        seen_oids.add(oid.oid)
                        all_oids.append(oid)

            # 3. 如果JSON提取失败，尝试直接解析MIB文本 (fallback)
            if not all_oids:
                for filename in filenames:
                    filepath = UPLOAD_DIR / filename
                    oids = self._parse_mib_text(filepath, vendor_oid)
                    for oid in oids:
                        if oid.oid not in seen_oids:
                            seen_oids.add(oid.oid)
                            all_oids.append(oid)

            # 4. 如果仍然没有OID，返回失败
            if not all_oids:
                error_detail = '; '.join(compile_errors) if compile_errors else '无有效MIB模块'
                return MIBParseResult(
                    task_id=task_id,
                    filename=",".join(filenames),
                    success=False,
                    message=f"MIB解析失败: {error_detail}",
                )

            # 4. 自动分类
            for oid in all_oids:
                auto_classify_oid(oid)

            # 5. 分离静态项和发现项
            static_items = [o for o in all_oids if not o.is_indexed]
            indexed_items = [o for o in all_oids if o.is_indexed]

            # 6. 按MIB表分组聚合索引项 (每个表一个发现规则)
            discovery_items: Dict[str, List[ParsedOID]] = {}
            for item in indexed_items:
                table_key = self._get_table_key(item.oid)
                if table_key not in discovery_items:
                    discovery_items[table_key] = []
                discovery_items[table_key].append(item)

            elapsed = time.time() - start_time

            return MIBParseResult(
                task_id=task_id,
                filename=",".join(filenames),
                success=True,
                message=f"解析成功，共发现 {len(all_oids)} 个OID节点",
                parsed_oids=all_oids,
                static_items=static_items,
                discovery_items=discovery_items,
                total_oids=len(all_oids),
                parse_time=round(elapsed, 2),
            )

        except Exception as e:
            return MIBParseResult(
                task_id=task_id,
                filename=",".join(filenames),
                success=False,
                message=f"解析异常: {str(e)}",
            )

    def _extract_oids_from_json(self, module_name: str, vendor_oid: str = "") -> List[ParsedOID]:
        """从pysmi编译后的JSON文件提取OID"""
        oids = []
        json_file = self._compiled_dir / f"{module_name}.json"

        if not json_file.exists():
            return oids

        try:
            import json
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # pysmi JSON格式: {oid_tuple: {name, syntax, ...}, ...}
            for oid_key, info in data.items():
                if not isinstance(info, dict):
                    continue

                # 构建OID字符串
                oid_str = self._normalize_oid(oid_key)
                if not oid_str:
                    continue

                # 过滤厂商OID
                if vendor_oid and not oid_str.startswith(vendor_oid):
                    continue

                name = info.get("name", "")
                description = info.get("description", "")
                syntax = info.get("syntax", "")
                access = info.get("access", "read-only")
                status = info.get("status", "current")

                # 检测是否为表格成员
                is_indexed = self._check_indexed(info)

                parsed = ParsedOID(
                    oid=oid_str,
                    name=str(name),
                    description=str(description),
                    syntax=str(syntax),
                    access=str(access),
                    status=str(status),
                    is_indexed=is_indexed,
                )
                oids.append(parsed)

        except Exception as e:
            print(f"解析JSON {module_name} 失败: {e}")

        return oids

    def _parse_mib_text(self, filepath: Path, vendor_oid: str = "") -> List[ParsedOID]:
        """
        优化版MIB文本解析
        核心优化: 一次性扫描构建 name→(parent,subid) 查找表，再批量解析OID，避免重复正则
        """
        oids = []
        if not filepath.exists():
            return oids

        try:
            content = filepath.read_text(encoding="utf-8", errors="ignore")

            # === 第一遍扫描: 构建 name→(parent, subid) 查找表 ===
            # 同时提取所有定义，避免后续重复正则搜索
            oid_defs = {}  # name -> (parent, subid)
            obj_type_defs = {}  # name -> {syntax, access, status, desc, parent, subid}

            # 匹配所有 ::= { parent subid } 定义
            # 分两种: 数字序列 和 名称引用
            def_pattern = re.compile(
                r'(\w+)\s+(?:MODULE-IDENTITY|OBJECT(?:-TYPE)?)\s+'
                r'(?:.*?SYNTAX\s+(\S+?))??'
                r'(?:.*?MAX-ACCESS\s+(\w+?))??'
                r'(?:.*?STATUS\s+(\w+?))??'
                r'(?:.*?DESCRIPTION\s+"([^"]*?)")??'
                r'.*?::=\s*\{\s*([\w\d\s.]+?)\s*\}',
                re.DOTALL | re.IGNORECASE
            )

            for m in def_pattern.finditer(content):
                name = m.group(1)
                syntax = m.group(2) or ""
                access = m.group(3) or "read-only"
                status = m.group(4) or "current"
                desc = m.group(5) or ""
                body = m.group(6).strip()

                # 解析 ::= { ... } 内容
                parts = body.split()
                if not parts:
                    continue

                # 数字序列: { 1 3 6 1 4 1 53184 }
                if all(p.isdigit() for p in parts):
                    oid_defs[name] = (".".join(parts), "")
                    obj_type_defs[name] = {"syntax": syntax, "access": access, "status": status, "desc": desc}
                # 名称引用: { enterprises 53184 } 或 { sensorTable 1 }
                elif len(parts) >= 2 and parts[-1].isdigit():
                    parent = " ".join(parts[:-1])
                    subid = parts[-1]
                    oid_defs[name] = (parent, subid)
                    obj_type_defs[name] = {"syntax": syntax, "access": access, "status": status, "desc": desc}
                elif len(parts) == 1:
                    # 只有名称，没有子ID
                    oid_defs[name] = (parts[0], "")

            # === 第二遍: 批量解析OID (带缓存) ===
            resolved_cache = {}

            def resolve(name: str, depth: int = 0) -> str:
                """递归解析OID，带缓存"""
                if depth > 15:
                    return name
                if name in resolved_cache:
                    return resolved_cache[name]

                # 内置OID
                name_lower = name.lower().strip()
                for kn, ko in self._builtin_oids.items():
                    if kn.lower() == name_lower:
                        resolved_cache[name] = ko
                        return ko

                # 纯数字
                if re.match(r'^[\d\s.]+$', name):
                    result = name.replace(" ", ".")
                    resolved_cache[name] = result
                    return result

                # 查找表
                if name in oid_defs:
                    parent, subid = oid_defs[name]
                    parent_oid = resolve(parent, depth + 1)
                    if subid:
                        result = f"{parent_oid}.{subid}"
                    else:
                        result = parent_oid
                    resolved_cache[name] = result
                    return result

                resolved_cache[name] = name
                return name

            # 预解析所有OID
            for name in oid_defs:
                resolve(name)

            # === 第三遍: 构建ParsedOID列表 ===
            seen_oids = set()
            for name, (parent, subid) in oid_defs.items():
                oid_str = resolved_cache.get(name, name)

                # 过滤厂商OID
                if vendor_oid and not oid_str.startswith(vendor_oid):
                    continue

                # 去重
                if oid_str in seen_oids:
                    continue
                seen_oids.add(oid_str)

                info = obj_type_defs.get(name, {})
                oids.append(ParsedOID(
                    oid=oid_str,
                    name=name,
                    description=info.get("desc", ""),
                    syntax=info.get("syntax", ""),
                    access=info.get("access", "read-only"),
                    status=info.get("status", "current"),
                    is_indexed=False,
                ))

            # === 检测表格索引 ===
            self._detect_table_indices_fast(content, oids, oid_defs, resolved_cache)

        except Exception as e:
            print(f"文本解析 {filepath.name} 失败: {e}")

        return oids

    def _detect_table_indices_fast(self, content: str, oids: List[ParsedOID],
                                     oid_defs: dict, resolved_cache: dict):
        """
        优化版表格索引检测
        使用预构建的查找表，避免重复正则
        """
        # 找所有 Entry 定义及其 INDEX
        entry_pattern = re.compile(
            r'(\w+Entry)\s+OBJECT-TYPE\s+'
            r'.*?INDEX\s*\{([^}]+)\}'
            r'.*?::=\s*\{\s*(\w+)\s+(\d+)\s*\}',
            re.DOTALL | re.IGNORECASE
        )

        table_prefixes = set()

        for match in entry_pattern.finditer(content):
            parent_name = match.group(3)
            subid = match.group(4)
            parent_oid = resolved_cache.get(parent_name, "")
            if parent_oid:
                table_prefixes.add(f"{parent_oid}.{subid}")

        # 只在内容包含AUGMENTS时才跑正则 (避免600ms空扫描)
        if "AUGMENTS" in content.upper():
            augments_pattern = re.compile(
                r'(\w+Entry)\s+OBJECT-TYPE\s+'
                r'.*?AUGMENTS\s*\{([^}]+)\}'
                r'.*?::=\s*\{\s*(\w+)\s+(\d+)\s*\}',
                re.DOTALL | re.IGNORECASE
            )
            for match in augments_pattern.finditer(content):
                parent_name = match.group(3)
                subid = match.group(4)
                parent_oid = resolved_cache.get(parent_name, "")
                if parent_oid:
                    table_prefixes.add(f"{parent_oid}.{subid}")

        # 备选: 找 Entry OBJECT IDENTIFIER
        if not table_prefixes:
            for name, (parent, subid) in oid_defs.items():
                if "entry" in name.lower() and subid:
                    parent_oid = resolved_cache.get(parent, "")
                    if parent_oid:
                        table_prefixes.add(f"{parent_oid}.{subid}")

        # 标记所有以 table_prefix 开头的 OID 为 indexed
        if table_prefixes:
            for oid in oids:
                for prefix in table_prefixes:
                    if oid.oid.startswith(prefix + ".") or oid.oid == prefix:
                        oid.is_indexed = True
                        break

    def _detect_table_indices(self, content: str, oids: List[ParsedOID]):
        """
        检测表格索引关系
        策略: 找到 INDEX/AUGMENTS 定义 → 定位 Entry OID → 找到 Table OID(父级) → 标记该表下所有列为 indexed
        """
        # 1. 找到 Entry 定义: xxxEntry OBJECT-TYPE ... ::= { xxxTable 1 }
        #    和它的 INDEX { columnName } 子句
        entry_pattern = re.compile(
            r'(\w+Entry)\s+OBJECT-TYPE\s+'
            r'.*?INDEX\s*\{([^}]+)\}'
            r'.*?::=\s*\{\s*(\w+)\s+(\d+)\s*\}',
            re.DOTALL | re.IGNORECASE
        )

        # 也处理 AUGMENTS
        augments_pattern = re.compile(
            r'(\w+Entry)\s+OBJECT-TYPE\s+'
            r'.*?AUGMENTS\s*\{([^}]+)\}'
            r'.*?::=\s*\{\s*(\w+)\s+(\d+)\s*\}',
            re.DOTALL | re.IGNORECASE
        )

        # 收集所有表格的 Entry OID 前缀
        table_prefixes = set()

        for match in entry_pattern.finditer(content):
            entry_name = match.group(1)
            parent_name = match.group(3)
            subid = match.group(4)
            # Entry 的 OID 前缀: parent.subid
            # 找到 parent 的 OID
            parent_oid = self._find_oid_definition(parent_name, content)
            if parent_oid:
                entry_prefix = f"{parent_oid}.{subid}"
                table_prefixes.add(entry_prefix)

        for match in augments_pattern.finditer(content):
            entry_name = match.group(1)
            parent_name = match.group(3)
            subid = match.group(4)
            parent_oid = self._find_oid_definition(parent_name, content)
            if parent_oid:
                entry_prefix = f"{parent_oid}.{subid}"
                table_prefixes.add(entry_prefix)

        # 2. 如果没找到 Entry 定义，用备选策略: 找所有 xxxEntry ::= { xxxTable 1 }
        if not table_prefixes:
            entry_simple = re.compile(
                r'(\w+Entry)\s+OBJECT\s+IDENTIFIER\s+::=\s*\{\s*(\w+)\s+(\d+)\s*\}',
                re.IGNORECASE
            )
            for match in entry_simple.finditer(content):
                parent_name = match.group(2)
                subid = match.group(3)
                parent_oid = self._find_oid_definition(parent_name, content)
                if parent_oid:
                    table_prefixes.add(f"{parent_oid}.{subid}")

        # 3. 标记所有以 table_prefix 开头的 OID 为 indexed
        if table_prefixes:
            for oid in oids:
                for prefix in table_prefixes:
                    if oid.oid.startswith(prefix + ".") or oid.oid == prefix:
                        oid.is_indexed = True
                        break

    def _get_table_key(self, oid: str) -> str:
        """
        从OID提取表标识 (取Entry的父级作为表key)
        例: 1.3.6.1.4.1.53184.1.2.1.3 → 1.3.6.1.4.1.53184.1.2
        """
        parts = oid.split(".")
        try:
            # 找到 53184 后面的部分
            idx = parts.index("53184")
            # 表结构: 53184.N.2.1.M → 表key = 53184.N.2
            if idx + 3 <= len(parts):
                return ".".join(parts[:idx + 3])
        except ValueError:
            pass
        # fallback: 去掉最后一级
        return ".".join(parts[:-1]) if len(parts) > 1 else oid

    def _check_indexed(self, info: dict) -> bool:
        """检查JSON中的OID是否为表格成员"""
        # 检查是否有index或augments标记
        if info.get("index") or info.get("augments"):
            return True
        if "Table" in str(info.get("name", "")) or "Entry" in str(info.get("name", "")):
            return True
        return False

    def _normalize_oid(self, oid_key: str) -> str:
        """将OID键值标准化为点分格式"""
        # 如果已经是点分格式
        if isinstance(oid_key, str) and re.match(r'^[\d.]+$', oid_key):
            return oid_key

        # 如果是元组格式 "(1, 3, 6, 1, ...)"
        if isinstance(oid_key, str):
            numbers = re.findall(r'\d+', oid_key)
            if numbers:
                return ".".join(numbers)

        # 如果是列表/元组
        if isinstance(oid_key, (list, tuple)):
            return ".".join(str(x) for x in oid_key)

        return ""


# 全局解析器实例
mib_parser = MIBParser()


def parse_mib_files(filenames: List[str], vendor_oid: str = "") -> MIBParseResult:
    """便捷函数: 解析MIB文件"""
    return mib_parser.parse_uploaded_files(filenames, vendor_oid)
