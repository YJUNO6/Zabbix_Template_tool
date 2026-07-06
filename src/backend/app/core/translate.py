"""
中英翻译映射库
内置运维标准词汇映射，支持自定义扩展
MIB英文节点名称 → 标准中文监控名称
"""
import json
from pathlib import Path
from typing import Dict, Optional
from ..core.config import DATA_DIR

# 内置标准翻译映射库
BUILTIN_TRANSLATIONS: Dict[str, str] = {
    # === 系统级 ===
    "health": "健康状态",
    "healthstatus": "健康状态",
    "status": "运行状态",
    "state": "状态",
    "fault": "故障状态",
    "normal": "正常状态",
    "alarm": "告警状态",
    "overall": "综合状态",
    "operational": "运行状态",
    "availability": "可用性",

    # === 设备信息 ===
    "model": "型号",
    "version": "版本",
    "serial": "序列号",
    "serialnumber": "序列号",
    "manufacturer": "制造商",
    "firmware": "固件版本",
    "bios": "BIOS版本",
    "name": "名称",
    "slotname": "插槽名称",
    "slot": "插槽",
    "partnumber": "部件编号",
    "part": "部件",
    "number": "编号",
    "description": "描述",
    "location": "位置",
    "asset": "资产标签",
    "uuid": "UUID",
    "device": "设备",
    "host": "主机",
    "server": "服务器",
    "chassis": "机箱",
    "baseboard": "底板",
    "riser": "转接卡",

    # === 通用结构 ===
    "table": "表",
    "entry": "条目",
    "index": "索引",
    "num": "编号",
    "number": "编号",
    "count": "数量",
    "total": "总计",
    "list": "列表",
    "info": "信息",
    "data": "数据",
    "value": "值",
    "level": "等级",
    "type": "类型",
    "class": "类别",
    "group": "组",
    "set": "集",
    "item": "项目",
    "id": "ID",
    "code": "编码",

    # === 机箱/底盘 ===
    "chassis": "机箱",
    "fru": "FRU",
    "board": "主板",
    "oem": "OEM",
    "product": "产品",
    "baseboard": "底板",
    "backplane": "背板",
    "riser": "转接卡",

    # === 状态/控制 ===
    "enable": "启用",
    "disable": "禁用",
    "active": "活跃",
    "inactive": "非活跃",
    "present": "在位",
    "absent": "不在位",
    "ok": "正常",
    "fail": "失败",
    "failed": "已失败",
    "good": "良好",
    "bad": "异常",
    "high": "高",
    "low": "低",
    "critical": "严重",
    "major": "主要",
    "minor": "次要",
    "warning": "警告",

    # === 物理/硬件 ===
    "slot": "插槽",
    "port": "端口",
    "connector": "连接器",
    "cable": "线缆",
    "led": "指示灯",
    "button": "按钮",
    "switch": "开关",
    "chassis": "机箱",
    "enclosure": "机柜",
    "bay": "仓位",

    # === 电源相关 ===
    "supply": "供应",
    "input": "输入",
    "output": "输出",
    "battery": "电池",
    "ups": "UPS",

    # === 读数/测量 ===
    "reading": "读数",
    "threshold": "阈值",
    "minimum": "最小值",
    "maximum": "最大值",
    "average": "平均值",
    "peak": "峰值",
    "current": "当前",
    "nominal": "标称",

    # === CPU ===
    "cpu": "CPU",
    "processor": "处理器",
    "core": "核心",
    "thread": "线程",
    "socket": "插槽",
    "cache": "缓存",
    "frequency": "频率",
    "clock": "时钟",

    # === 内存 ===
    "memory": "内存",
    "ram": "内存",
    "dimm": "内存条",
    "ecc": "ECC",

    # === 磁盘/存储 ===
    "disk": "磁盘",
    "drive": "硬盘",
    "storage": "存储",
    "raid": "RAID",
    "array": "阵列",
    "volume": "逻辑卷",
    "partition": "分区",
    "capacity": "容量",
    "free": "可用空间",
    "used": "已用空间",

    # === 网络 ===
    "nic": "网卡",
    "network": "网络",
    "interface": "接口",
    "port": "端口",
    "link": "链路",
    "mac": "MAC地址",
    "speed": "速率",
    "bandwidth": "带宽",
    "throughput": "吞吐量",

    # === 风扇/散热 ===
    "fan": "风扇",
    "cooling": "散热",
    "heatsink": "散热器",

    # === 电源 ===
    "power": "电源",
    "psu": "电源",
    "wattage": "功率",
    "voltage": "电压",
    "current": "电流",

    # === 温度/传感器 ===
    "temperature": "温度",
    "temp": "温度",
    "sensor": "传感器",
    "thermal": "热力",

    # === 性能指标 ===
    "usage": "使用率",
    "utilization": "利用率",
    "load": "负载",
    "rate": "比率",
    "percent": "百分比",
    "ratio": "比例",
    "latency": "延迟",
    "iops": "IOPS",

    # === 转速/频率单位 ===
    "rpm": "转速",
    "mhz": "频率(MHz)",
    "ghz": "频率(GHz)",

    # === GPU ===
    "gpu": "GPU",
    "graphics": "显卡",

    # === PCIe ===
    "pcie": "PCIe",
    "pci": "PCI",

    # === 告警/事件 ===
    "warning": "警告",
    "critical": "严重",
    "error": "错误",
    "event": "事件",
    "log": "日志",

    # === 电源管理 ===
    "redundancy": "冗余",
    "input": "输入",
    "output": "输出",
}

# 自定义翻译文件路径
CUSTOM_TRANSLATIONS_FILE = DATA_DIR / "custom_translations.json"


def load_custom_translations() -> Dict[str, str]:
    """加载用户自定义翻译"""
    if CUSTOM_TRANSLATIONS_FILE.exists():
        try:
            with open(CUSTOM_TRANSLATIONS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def save_custom_translations(translations: Dict[str, str]):
    """保存用户自定义翻译"""
    with open(CUSTOM_TRANSLATIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(translations, f, ensure_ascii=False, indent=2)


def get_all_translations() -> Dict[str, str]:
    """获取全部翻译 (内置 + 自定义，自定义优先)"""
    merged = dict(BUILTIN_TRANSLATIONS)
    merged.update(load_custom_translations())
    return merged


def split_camel_case(name: str) -> list:
    """
    拆分驼峰命名
    sensorTable -> ['sensor', 'table']
    ChassisSerialNumber -> ['chassis', 'serial', 'number']
    SensorReading -> ['sensor', 'reading']
    HealthStatus -> ['health', 'status']
    """
    import re
    # 在大写字母前插入分隔符，然后分割
    # 处理连续大写: FRUTable -> FRU, Table
    s1 = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', name)
    # 处理普通驼峰: sensorTable -> sensor_Table
    s2 = re.sub(r'([a-z\d])([A-Z])', r'\1_\2', s1)
    # 分割并转小写
    words = [w.lower() for w in re.split(r'[_\-\s]+', s2) if w]
    return words


def translate_name(english_name: str) -> str:
    """
    将英文OID名称翻译为中文
    策略：整体匹配 → 驼峰拆分逐词匹配 → 前缀剥离匹配
    """
    translations = get_all_translations()
    name_lower = english_name.lower().strip()

    # 1. 整体匹配
    if name_lower in translations:
        return translations[name_lower]

    # 2. 驼峰拆分后逐词翻译
    words = split_camel_case(english_name)
    translated_parts = []
    all_translated = True
    i = 0
    while i < len(words):
        word = words[i]
        # 尝试两词组合匹配 (如 serial+number -> 序列号)
        if i + 1 < len(words):
            compound = word + words[i + 1]
            if compound in translations:
                translated_parts.append(translations[compound])
                i += 2
                continue
        if word in translations:
            translated_parts.append(translations[word])
        else:
            translated_parts.append(word)
            all_translated = False
        i += 1

    if all_translated and translated_parts:
        return "".join(translated_parts)

    # 3. 如果部分翻译了，也返回翻译结果 (至少比全英文好)
    result = "".join(translated_parts)
    if result != name_lower:
        return result

    # 4. 去掉常见前缀后匹配
    prefixes_to_strip = ["ent", "hw", "lenovo", "server", "system", "sys"]
    for prefix in prefixes_to_strip:
        if name_lower.startswith(prefix) and name_lower[len(prefix):] in translations:
            return translations[name_lower[len(prefix):]]

    # 5. 保留原名
    return english_name
