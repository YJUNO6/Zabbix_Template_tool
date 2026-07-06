"""
指标分类引擎
根据OID名称/描述自动分类为三大类型，分配采集间隔、值类型、单位等
"""
import re
from typing import Tuple
from ..models.schemas import (
    ParsedOID, ItemCategory, DiscoveryGroup,
    CATEGORY_DELAY, DISCOVERY_DELAY, DISCOVERY_DELAY_DEFAULT,
    VALUE_TYPE_FLOAT, VALUE_TYPE_TEXT, UNIT_KEYWORDS
)
from .translate import translate_name, split_camel_case


# === 分类关键词规则 ===

# 状态类关键词 (health/status/state/fault/normal/alarm)
STATUS_KEYWORDS = {
    "health", "status", "state", "fault", "normal", "alarm",
    "operational", "availability", "condition", "presence",
    "redundancy", "online", "offline", "enabled", "disabled",
    "ok", "fail", "failed", "warning", "critical",
}

# 性能数值类关键词
PERFORMANCE_KEYWORDS = {
    "temperature", "temp", "power", "speed", "capacity", "usage",
    "rpm", "mhz", "ghz", "watt", "voltage", "current",
    "load", "utilization", "rate", "percent", "ratio",
    "latency", "iops", "bandwidth", "throughput",
    "frequency", "clock", "free", "used", "size",
    "count", "total", "reading", "consumption", "cores",
    "threads", "hz", "bytes", "packets", "errors",
}

# 静态信息类关键词
INFO_KEYWORDS = {
    "model", "version", "serial", "manufacturer", "firmware",
    "slot", "name", "partnumber", "description", "location",
    "asset", "uuid", "bios", "mac", "address",
    "vendor", "revision", "build", "release",
    # 通用文本字段
    "type", "table", "entry", "index", "num", "number", "id",
    "sn", "cause", "boot", "policy", "identify", "dsc", "extra",
    "oem", "info", "data", "label", "labelname", "text", "string",
    "desc", "detail", "family", "brand", "product", "category",
    "class", "group", "set", "mode", "code", "color", "led",
}

# 硬件分组关键词映射
DISCOVERY_GROUP_KEYWORDS = {
    DiscoveryGroup.CPU: {"cpu", "processor", "core", "thread", "socket"},
    DiscoveryGroup.MEMORY: {"memory", "ram", "dimm", "ecc"},
    DiscoveryGroup.DISK: {"disk", "drive", "storage", "hdd", "ssd", "nvme"},
    DiscoveryGroup.FAN: {"fan", "cooling", "heatsink"},
    DiscoveryGroup.POWER: {"power", "psu", "wattage"},
    DiscoveryGroup.SENSOR: {"sensor", "thermal", "temperature", "temp"},
    DiscoveryGroup.RAID: {"raid", "array", "controller"},
    DiscoveryGroup.NIC: {"nic", "network", "interface", "port", "ethernet"},
    DiscoveryGroup.GPU: {"gpu", "graphics"},
    DiscoveryGroup.PCIE: {"pcie", "pci"},
    DiscoveryGroup.VOLUME: {"volume", "partition", "logical"},
    DiscoveryGroup.SYSTEM: {"system", "server", "chassis", "board", "entire"},
}

# 单位关键词到标准单位的映射
UNIT_MAP = {
    "temperature": "℃", "temp": "℃", "celsius": "℃",
    "power": "W", "watt": "W", "wattage": "W",
    "speed": "RPM", "rpm": "RPM",
    "frequency": "MHz", "mhz": "MHz", "ghz": "GHz", "clock": "MHz",
    "capacity": "GB", "size": "GB", "memory": "GB", "ram": "GB",
    "usage": "%", "utilization": "%", "rate": "%", "percent": "%", "load": "%",
    "voltage": "V",
    "current": "A",
    "latency": "ms",
    "bandwidth": "Mbps",
    "throughput": "Mbps",
    "iops": "IOPS",
}


def classify_oid(oid_name: str, oid_description: str = "") -> Tuple[ItemCategory, DiscoveryGroup]:
    """
    根据OID名称和描述自动分类
    返回: (指标分类, 硬件分组)
    """
    name_lower = oid_name.lower().strip()
    desc_lower = oid_description.lower().strip()
    combined = f"{name_lower} {desc_lower}"

    # 判断指标分类 (传原始名以便驼峰拆分)
    category = _determine_category(oid_name, combined)

    # 判断硬件分组
    group = _determine_group(name_lower, combined)

    return category, group


def _determine_category(name: str, combined: str) -> ItemCategory:
    """判断指标分类: 状态/性能/信息"""
    # 拆分为单词列表 (驼峰/下划线/横杠分割)
    words = set(split_camel_case(name))
    words.add(name)  # 也加入完整名

    # 优先匹配状态类
    for kw in STATUS_KEYWORDS:
        if kw in words:
            return ItemCategory.STATUS

    # 匹配信息类
    for kw in INFO_KEYWORDS:
        if kw in words:
            return ItemCategory.INFO

    # 匹配性能类
    for kw in PERFORMANCE_KEYWORDS:
        if kw in words:
            return ItemCategory.PERFORMANCE

    # 描述中有线索
    desc_words = set(re.split(r'[_\-\s]+', combined.lower()))
    if desc_words & STATUS_KEYWORDS:
        return ItemCategory.STATUS
    if desc_words & INFO_KEYWORDS:
        return ItemCategory.INFO

    # 默认归为信息类(文本/字符) — 宁可多给TEXT也不要错误给FLOAT
    return ItemCategory.INFO


def _determine_group(name: str, combined: str) -> DiscoveryGroup:
    """判断硬件分组"""
    for group, keywords in DISCOVERY_GROUP_KEYWORDS.items():
        for kw in keywords:
            if kw in name:
                return group
    return DiscoveryGroup.SYSTEM


def detect_unit(oid_name: str, syntax: str = "") -> str:
    """根据OID名称和语法自动检测单位"""
    name_lower = oid_name.lower()

    # 从名称关键词推断单位
    for keyword, unit in UNIT_MAP.items():
        if keyword in name_lower:
            return unit

    # 从syntax字段推断
    if syntax:
        syntax_lower = syntax.lower()
        if "celsius" in syntax_lower or "temperature" in syntax_lower:
            return "℃"
        if "counter" in syntax_lower:
            return ""
        if "gauge" in syntax_lower:
            return ""
        if "displaystring" in syntax_lower:
            return ""

    return ""


def determine_value_type(category: ItemCategory, oid_name: str, syntax: str = "") -> int:
    """
    判断值类型
    状态类和信息类 → TEXT(4)
    性能数值类 → FLOAT(0)
    """
    if category == ItemCategory.STATUS:
        return VALUE_TYPE_TEXT
    if category == ItemCategory.INFO:
        return VALUE_TYPE_TEXT
    return VALUE_TYPE_FLOAT


def determine_trends(category: ItemCategory, value_type: int) -> str:
    """
    判断趋势保留时间
    TEXT类型(序列号/型号等) → 0d
    FLOAT类型 → 30d
    """
    if value_type == VALUE_TYPE_TEXT:
        return "0d"
    return "30d"


def generate_zabbix_key(oid_name: str, discovery_group: DiscoveryGroup, is_indexed: bool = False) -> str:
    """
    生成标准化Zabbix key
    规则: 全小写、分层点分隔、禁止中文/大写/特殊符号
    格式:
      静态: 硬件类型.指标名 (如 cpu.health, power.current)
      动态: 硬件类型.指标名[{#SNMPINDEX}] (如 cpu.health[{#SNMPINDEX}])
    """
    # 驼峰拆分后用点连接，保留更多语义信息避免key冲突
    parts = split_camel_case(oid_name)
    if not parts:
        parts = [oid_name.lower().strip()]

    # 清理每个部分
    cleaned_parts = []
    for p in parts:
        c = re.sub(r'[^a-z0-9]', '', p.lower())
        if c:
            cleaned_parts.append(c)

    name_joined = ".".join(cleaned_parts) if cleaned_parts else "unknown"

    # 确定硬件前缀
    group_prefix = discovery_group.value if discovery_group != DiscoveryGroup.SYSTEM else ""

    # 构建key: 前缀.名称
    if group_prefix and not name_joined.startswith(group_prefix):
        key = f"{group_prefix}.{name_joined}"
    else:
        key = name_joined

    # 去掉连续的点
    key = re.sub(r'\.+', '.', key).strip('.')

    # 如果key为空，使用默认
    if not key:
        key = "unknown.item"

    # 动态实例加索引占位符
    if is_indexed:
        key = f"{key}[{{#SNMPINDEX}}]"

    return key


def auto_classify_oid(oid: ParsedOID) -> ParsedOID:
    """
    对单个OID进行完整的自动分类
    填充所有自动推断的字段
    """
    # 1. 分类
    category, group = classify_oid(oid.name, oid.description)
    oid.category = category
    oid.discovery_group = group

    # 2. 采集间隔
    oid.delay = CATEGORY_DELAY.get(category, "5m")

    # 3. 值类型
    oid.value_type = determine_value_type(category, oid.name, oid.syntax)

    # 4. 单位
    if oid.value_type == VALUE_TYPE_FLOAT:
        oid.unit = detect_unit(oid.name, oid.syntax)

    # 5. 趋势保留
    oid.trends = determine_trends(category, oid.value_type)

    # 6. 是否为健康状态指标
    oid.is_health = any(kw in oid.name.lower() for kw in ["health", "healthy"])

    # 7. Zabbix key — 使用OID父节点编号来避免通用名冲突
    oid.zabbix_key = generate_zabbix_key_with_context(oid.name, oid.oid, group, oid.is_indexed)

    # 8. 中文名翻译
    oid.chinese_name = translate_name(oid.name)

    return oid


def generate_zabbix_key_with_context(oid_name: str, oid: str, discovery_group: DiscoveryGroup, is_indexed: bool = False) -> str:
    """
    生成Zabbix key，对通用名(如Index/Description)加入父OID编号避免冲突
    """
    # 检查是否为通用名 (仅含一个单词，容易冲突)
    parts = split_camel_case(oid_name)
    is_generic = len(parts) <= 1 or oid_name.lower() in ("index", "description", "name", "type", "status", "maxspeed")

    if is_generic and oid:
        # 从OID中提取父节点编号，如 1.3.6.1.4.1.53184.18.2.1.1 → 18
        oid_parts = oid.split(".")
        # 找到 53184 后面的那个数字作为表标识
        try:
            idx = oid_parts.index("53184")
            if idx + 1 < len(oid_parts):
                table_id = oid_parts[idx + 1]
                # 用 table_id 作为前缀
                base_key = generate_zabbix_key(oid_name, discovery_group, is_indexed=False)
                if is_indexed:
                    return f"t{table_id}.{base_key}[{{#SNMPINDEX}}]"
                return f"t{table_id}.{base_key}"
        except (ValueError, IndexError):
            pass

    return generate_zabbix_key(oid_name, discovery_group, is_indexed)
