"""
数据模型定义
定义MIB解析结果、模板配置、导出任务等核心数据结构
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from enum import Enum
from datetime import datetime


class ItemCategory(str, Enum):
    """指标三大分类"""
    STATUS = "status"          # 状态类: health/status/state/fault/normal/alarm
    PERFORMANCE = "performance"  # 性能数值类: temperature/power/speed/capacity/usage/rpm
    INFO = "info"              # 静态信息类: model/version/serial/manufacturer/firmware


class DiscoveryGroup(str, Enum):
    """自动发现硬件分组"""
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    FAN = "fan"
    POWER = "power"
    SENSOR = "sensor"
    RAID = "raid"
    NIC = "nic"
    GPU = "gpu"
    PCIE = "pcie"
    VOLUME = "volume"
    SYSTEM = "system"
    OTHER = "other"


# 分类对应的默认采集间隔
CATEGORY_DELAY = {
    ItemCategory.STATUS: "1m",
    ItemCategory.PERFORMANCE: "5m",
    ItemCategory.INFO: "1d",
}

# 硬件分组对应的发现规则间隔
# 电源和风扇为5m，其余常规硬件为10m
DISCOVERY_DELAY = {
    DiscoveryGroup.FAN: "5m",
    DiscoveryGroup.POWER: "5m",
    # 其余默认10m
}
DISCOVERY_DELAY_DEFAULT = "10m"

# 值类型映射: 0=FLOAT, 4=TEXT
VALUE_TYPE_FLOAT = 0
VALUE_TYPE_TEXT = 4

# 单位映射关键词
UNIT_KEYWORDS = {
    "gb": "GB", "mb": "MB", "tb": "TB",
    "mhz": "MHz", "ghz": "GHz",
    "w": "W", "kw": "KW",
    "celsius": "℃", "temperature": "℃",
    "rpm": "RPM",
    "percent": "%", "usage": "%", "rate": "%",
}


class ParsedOID(BaseModel):
    """解析后的单个OID节点"""
    oid: str                           # 完整OID路径
    name: str                          # OID名称 (英文)
    description: str = ""              # 描述信息
    syntax: str = ""                   # 数据类型语法
    access: str = "read-only"          # 访问权限
    status: str = "current"            # 状态
    is_indexed: bool = False           # 是否为表格索引OID
    index_root_oid: str = ""           # 索引根OID (如果是表格成员)
    parent_oid: str = ""               # 父节点OID

    # 自动分类结果
    category: ItemCategory = ItemCategory.PERFORMANCE
    discovery_group: DiscoveryGroup = DiscoveryGroup.OTHER
    zabbix_key: str = ""               # 生成的标准化zabbix key
    chinese_name: str = ""             # 中文翻译名
    delay: str = "5m"                  # 采集间隔
    value_type: int = VALUE_TYPE_FLOAT # 值类型
    unit: str = ""                     # 单位
    trends: str = "30d"                # 趋势保留
    is_health: bool = False            # 是否为健康状态指标


class TemplateConfig(BaseModel):
    """模板配置信息"""
    template_prefix: str = "LW_Template"  # 模板前缀
    template_name: str = ""               # 模板显示名称
    device_model: str = ""                # 设备型号
    snmp_community: str = "public"        # SNMP团体字
    vendor_oid: str = ""                  # 厂商前缀OID

    # 自定义采集间隔
    status_delay: str = "1m"
    performance_delay: str = "5m"
    info_delay: str = "1d"

    # 保留策略
    history_days: str = "7d"
    trends_days: str = "30d"

    def get_template_id(self) -> str:
        """生成完整模板标识名"""
        if self.device_model:
            return f"{self.template_prefix}_{self.device_model}"
        return f"{self.template_prefix}_Custom"


class MIBParseResult(BaseModel):
    """MIB解析结果"""
    task_id: str
    filename: str
    success: bool
    message: str = ""
    parsed_oids: List[ParsedOID] = []
    static_items: List[ParsedOID] = []      # 无索引的静态指标
    discovery_items: Dict[str, List[ParsedOID]] = {}  # 按硬件分组的索引指标
    total_oids: int = 0
    parse_time: float = 0.0


class ExportTask(BaseModel):
    """导出任务记录"""
    task_id: str
    created_at: datetime
    config: TemplateConfig
    parse_result: MIBParseResult
    xml_content: Optional[str] = None
    status: str = "pending"  # pending/completed/failed


class TranslationEntry(BaseModel):
    """中英翻译词条"""
    english: str
    chinese: str
    category: Optional[ItemCategory] = None


class ValidateResult(BaseModel):
    """校验结果"""
    valid: bool
    errors: List[str] = []
    warnings: List[str] = []
