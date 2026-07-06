"""
Zabbix 6.4 XML模板生成引擎
严格遵循参考XML固定层级结构，使用lxml生成标准zabbix_export格式
"""
import uuid
import hashlib
import re
from typing import List, Dict, Optional
from lxml import etree
from copy import deepcopy

from ..models.schemas import (
    ParsedOID, TemplateConfig, MIBParseResult, ItemCategory, DiscoveryGroup,
    VALUE_TYPE_FLOAT, VALUE_TYPE_TEXT, ValidateResult,
    DISCOVERY_DELAY, DISCOVERY_DELAY_DEFAULT, CATEGORY_DELAY
)
from ..core.config import FIXED_GROUPS


def generate_uuid() -> str:
    """生成32位小写16进制UUID (全局唯一)"""
    return uuid.uuid4().hex


class ZabbixXMLGenerator:
    """Zabbix 6.4 XML模板生成器"""

    def __init__(self, config: TemplateConfig):
        self.config = config
        self.template_id = config.get_template_id()
        self._used_uuids = set()

    def generate(self, parse_result: MIBParseResult) -> str:
        """
        生成完整的Zabbix 6.4 XML模板
        严格遵循Zabbix 6.4官方模板结构:
        template_groups → templates → template → items → discovery_rules → macros
        注意: Zabbix 6.4 不需要 <date> 标签, 顶层分组用 <template_groups>
        """
        # 构建XML树
        root = etree.Element("zabbix_export")
        version = etree.SubElement(root, "version")
        version.text = "6.4"

        # 1. template_groups (Zabbix 6.4 用 template_groups 不是 groups)
        self._build_template_groups(root)

        # 2. templates → template
        templates_elem = etree.SubElement(root, "templates")
        template_elem = etree.SubElement(templates_elem, "template")

        t_uuid = etree.SubElement(template_elem, "uuid")
        t_uuid.text = self._unique_uuid()

        t_template = etree.SubElement(template_elem, "template")
        t_template.text = self.template_id

        t_name = etree.SubElement(template_elem, "name")
        t_name.text = self.config.template_name or self.template_id

        # template下的groups
        t_groups = etree.SubElement(template_elem, "groups")
        for group_name in FIXED_GROUPS:
            g = etree.SubElement(t_groups, "group")
            gn = etree.SubElement(g, "name")
            gn.text = group_name

        # 3. items (静态指标)
        items_elem = etree.SubElement(template_elem, "items")
        for item in parse_result.static_items:
            self._build_static_item(items_elem, item)

        # 4. discovery_rules
        discovery_elem = etree.SubElement(template_elem, "discovery_rules")
        for group_name, group_items in parse_result.discovery_items.items():
            self._build_discovery_rule(discovery_elem, group_name, group_items)

        # 5. macros
        self._build_macros(template_elem)

        # 格式化输出
        return self._format_xml(root)

    def _build_template_groups(self, root: etree.Element):
        """构建template_groups节点 (Zabbix 6.4 用 template_groups/template_group)"""
        groups = etree.SubElement(root, "template_groups")
        for group_name in FIXED_GROUPS:
            g = etree.SubElement(groups, "template_group")
            uuid_elem = etree.SubElement(g, "uuid")
            uuid_elem.text = self._unique_uuid()
            name_elem = etree.SubElement(g, "name")
            name_elem.text = group_name

    def _build_static_item(self, parent: etree.Element, item: ParsedOID):
        """
        构建静态Item节点
        字段顺序: uuid/name/type/snmp_oid/key/delay/history/trends/value_type/units/tags
        """
        item_elem = etree.SubElement(parent, "item")

        # uuid
        u = etree.SubElement(item_elem, "uuid")
        u.text = self._unique_uuid()

        # name (中文名)
        n = etree.SubElement(item_elem, "name")
        n.text = item.chinese_name or item.name

        # type (固定SNMP_AGENT)
        t = etree.SubElement(item_elem, "type")
        t.text = "SNMP_AGENT"

        # snmp_oid
        soid = etree.SubElement(item_elem, "snmp_oid")
        soid.text = item.oid

        # key
        k = etree.SubElement(item_elem, "key")
        k.text = item.zabbix_key

        # delay
        d = etree.SubElement(item_elem, "delay")
        d.text = self.config.info_delay if item.category == ItemCategory.INFO else \
                 self.config.status_delay if item.category == ItemCategory.STATUS else \
                 self.config.performance_delay

        # history
        h = etree.SubElement(item_elem, "history")
        h.text = self.config.history_days

        # trends (数值型30d, 文本型0)
        tr = etree.SubElement(item_elem, "trends")
        tr.text = "0" if item.value_type == VALUE_TYPE_TEXT else self.config.trends_days

        # value_type (Zabbix 6.4 用文字: FLOAT/CHAR/LOG/UNSIGNED/TEXT)
        vt = etree.SubElement(item_elem, "value_type")
        vt.text = self._value_type_name(item.value_type)

        # units (仅FLOAT类型)
        if item.value_type == VALUE_TYPE_FLOAT and item.unit:
            un = etree.SubElement(item_elem, "units")
            un.text = item.unit

        # tags
        self._build_tags(item_elem, item.discovery_group)

    def _build_discovery_rule(self, parent: etree.Element, group_name: str, items: List[ParsedOID]):
        """
        构建自动发现规则
        group_name: 现在是表OID前缀 (如 1.3.6.1.4.1.53184.1.2)
        字段: uuid/name/type/snmp_oid/key/delay/lifetime/item_prototypes
        """
        if not items:
            return

        # 从items推断表名和硬件分类
        table_name = self._get_table_display_name(items)
        hw_group = items[0].discovery_group if items else DiscoveryGroup.OTHER

        dr = etree.SubElement(parent, "discovery_rule")

        # uuid
        u = etree.SubElement(dr, "uuid")
        u.text = self._unique_uuid()

        # name (表的中文名)
        n = etree.SubElement(dr, "name")
        n.text = table_name

        # type
        t = etree.SubElement(dr, "type")
        t.text = "SNMP_AGENT"

        # snmp_oid (发现OID = 表的Entry OID)
        soid = etree.SubElement(dr, "snmp_oid")
        soid.text = self._get_discovery_oid(items)

        # key (表名.discovery, 确保唯一)
        discovery_key = self._generate_discovery_key(items, hw_group)
        k = etree.SubElement(dr, "key")
        k.text = discovery_key

        # delay (风扇/电源5m, 其余10m)
        d = etree.SubElement(dr, "delay")
        d.text = DISCOVERY_DELAY.get(hw_group, DISCOVERY_DELAY_DEFAULT)

        # lifetime (资源保留期限)
        lt = etree.SubElement(dr, "lifetime")
        lt.text = "3d"

        # item_prototypes
        ip_elem = etree.SubElement(dr, "item_prototypes")
        for item in items:
            self._build_item_prototype(ip_elem, item, group_name)

    def _build_item_prototype(self, parent: etree.Element, item: ParsedOID, group_name: str):
        """
        构建item_prototype
        字段: uuid/name/type/snmp_oid/key/delay/history/trends/value_type/units/tags/trigger_prototypes
        """
        ip = etree.SubElement(parent, "item_prototype")

        # uuid
        u = etree.SubElement(ip, "uuid")
        u.text = self._unique_uuid()

        # name (带{#SNMPINDEX}占位符)
        n = etree.SubElement(ip, "name")
        n.text = (item.chinese_name or item.name) + " {#SNMPINDEX}"

        # type
        t = etree.SubElement(ip, "type")
        t.text = "SNMP_AGENT"

        # snmp_oid (带索引)
        soid = etree.SubElement(ip, "snmp_oid")
        soid.text = f"{item.oid}.{{#SNMPINDEX}}" if not item.oid.endswith("{#SNMPINDEX}") else item.oid

        # key (带索引)
        k = etree.SubElement(ip, "key")
        k.text = item.zabbix_key  # 已经包含[{#SNMPINDEX}]

        # delay
        d = etree.SubElement(ip, "delay")
        d.text = self.config.info_delay if item.category == ItemCategory.INFO else \
                 self.config.status_delay if item.category == ItemCategory.STATUS else \
                 self.config.performance_delay

        # history
        h = etree.SubElement(ip, "history")
        h.text = self.config.history_days

        # trends (数值型30d, 文本型0)
        tr = etree.SubElement(ip, "trends")
        tr.text = "0" if item.value_type == VALUE_TYPE_TEXT else self.config.trends_days

        # value_type (Zabbix 6.4 用文字: FLOAT/CHAR/LOG/UNSIGNED/TEXT)
        vt = etree.SubElement(ip, "value_type")
        vt.text = self._value_type_name(item.value_type)

        # units (仅FLOAT)
        if item.value_type == VALUE_TYPE_FLOAT and item.unit:
            un = etree.SubElement(ip, "units")
            un.text = item.unit

        # tags (用item自带的硬件分类)
        self._build_tags(ip, item.discovery_group)

        # trigger_prototypes (仅health健康类指标)
        if item.is_health:
            self._build_trigger_prototype(ip, item)

    def _build_trigger_prototype(self, parent: etree.Element, item: ParsedOID):
        """
        构建触发器原型
        expression: last(/模板名/指标[{#SNMPINDEX}])<>"Normal"
        priority: HIGH
        manual_close: YES
        """
        tp_elem = etree.SubElement(parent, "trigger_prototypes")
        tp = etree.SubElement(tp_elem, "trigger_prototype")

        # uuid
        u = etree.SubElement(tp, "uuid")
        u.text = self._unique_uuid()

        # expression — lxml会自动转义 < > 等特殊字符，这里直接用原始字符
        expr = etree.SubElement(tp, "expression")
        expr.text = f'last(/{self.template_id}/{item.zabbix_key})<>"Normal"'

        # name (用item自带的硬件分类中文名)
        group_cn = self._get_group_chinese_name(item.discovery_group.value)
        name_elem = etree.SubElement(tp, "name")
        name_elem.text = f"[{group_cn}] " + "{HOST.NAME}" + f" {item.chinese_name or item.name} " + "{#SNMPINDEX}" + " 健康状态异常"

        # priority
        pri = etree.SubElement(tp, "priority")
        pri.text = "HIGH"

        # manual_close
        mc = etree.SubElement(tp, "manual_close")
        mc.text = "YES"

    def _build_tags(self, parent: etree.Element, group: DiscoveryGroup):
        """构建tags节点"""
        tags = etree.SubElement(parent, "tags")
        tag = etree.SubElement(tags, "tag")
        tag_name = etree.SubElement(tag, "tag")
        tag_name.text = "Application"
        tag_value = etree.SubElement(tag, "value")
        tag_value.text = self._get_group_chinese_name(group.value)

    def _build_macros(self, template_elem: etree.Element):
        """构建macros节点"""
        macros = etree.SubElement(template_elem, "macros")
        macro = etree.SubElement(macros, "macro")
        m_name = etree.SubElement(macro, "macro")
        m_name.text = "{$SNMP_COMMUNITY}"
        m_value = etree.SubElement(macro, "value")
        m_value.text = self.config.snmp_community

    def _value_type_name(self, value_type: int) -> str:
        """将数值类型转为Zabbix 6.4文字格式"""
        type_map = {
            0: "FLOAT",
            1: "CHAR",
            2: "LOG",
            3: "UNSIGNED",
            4: "TEXT",
        }
        return type_map.get(value_type, "CHAR")

    def _get_group_chinese_name(self, group_name: str) -> str:
        """获取硬件分组的中文名"""
        name_map = {
            "system": "系统", "cpu": "CPU", "memory": "内存",
            "disk": "磁盘", "fan": "风扇", "power": "电源",
            "sensor": "传感器", "raid": "RAID", "nic": "网卡",
            "gpu": "GPU", "pcie": "PCIe", "volume": "逻辑卷",
            "other": "其他",
        }
        return name_map.get(group_name, group_name)

    def _generate_discovery_key(self, items: List[ParsedOID], hw_group: DiscoveryGroup) -> str:
        """生成唯一的发现规则key"""
        # 用Entry名作为key的一部分
        entry_keyword = ""
        for item in items:
            name_lower = item.name.lower()
            if "entry" in name_lower:
                # 提取Entry前缀, 如 FRUEntry → fru, SNMPServerEntry → snmpserver
                entry_keyword = name_lower.replace("entry", "").strip()
                break

        if not entry_keyword:
            # 用第一个非Index列名
            for item in items:
                if "index" not in item.name.lower():
                    from ..core.classify import split_camel_case
                    parts = split_camel_case(item.name)
                    entry_keyword = "".join(p.lower() for p in parts[:2])
                    break

        if not entry_keyword:
            entry_keyword = hw_group.value

        return f"{entry_keyword}.discovery"

    def _get_table_display_name(self, items: List[ParsedOID]) -> str:
        """从items推断表的显示名 (中文)"""
        # 找Entry名 (通常包含Entry的item)
        entry_name = ""
        for item in items:
            if "entry" in item.name.lower() or "table" in item.name.lower():
                entry_name = item.chinese_name or item.name
                break

        # 用第一个非Entry的列名作为表名
        if not entry_name:
            for item in items:
                if "index" not in item.name.lower() and "entry" not in item.name.lower():
                    entry_name = item.chinese_name or item.name
                    break

        # 如果还是没有，用硬件分类
        if not entry_name:
            hw_group = items[0].discovery_group if items else DiscoveryGroup.OTHER
            entry_name = self._get_group_chinese_name(hw_group.value)

        return entry_name

    def _get_discovery_oid(self, items: List[ParsedOID]) -> str:
        """从item列表推断发现规则的根OID"""
        if not items:
            return ""
        # 取公共前缀 (去掉最后一个.{#SNMPINDEX})
        first_oid = items[0].oid
        # 移除末尾的索引部分
        parts = first_oid.split(".")
        # 找到公共父OID
        if len(parts) > 1:
            return ".".join(parts[:-1])
        return first_oid

    def _unique_uuid(self) -> str:
        """生成不重复的UUID"""
        for _ in range(100):
            new_uuid = generate_uuid()
            if new_uuid not in self._used_uuids:
                self._used_uuids.add(new_uuid)
                return new_uuid
        # 极小概率fallback
        fallback = generate_uuid()
        self._used_uuids.add(fallback)
        return fallback

    def _format_xml(self, root: etree.Element) -> str:
        """格式化XML输出，确保缩进和换行规范"""
        rough_string = etree.tostring(root, encoding="unicode", xml_declaration=False)
        # 添加XML声明
        xml_declaration = '<?xml version="1.0" encoding="UTF-8"?>\n'

        # 使用lxml的indent功能格式化
        etree.indent(root, space="    ")
        formatted = etree.tostring(root, encoding="unicode", xml_declaration=False)

        return xml_declaration + formatted


def validate_xml_structure(xml_content: str) -> ValidateResult:
    """
    校验生成的XML结构完整性
    检查必填标签、uuid唯一性、key格式、delay取值
    """
    errors = []
    warnings = []

    try:
        root = etree.fromstring(xml_content.encode("utf-8"))
    except etree.XMLSyntaxError as e:
        return ValidateResult(valid=False, errors=[f"XML语法错误: {str(e)}"])

    # 1. 检查根节点
    if root.tag != "zabbix_export":
        errors.append("根节点必须为 zabbix_export")

    version = root.find("version")
    if version is None or version.text != "6.4":
        errors.append("version必须为6.4")

    # 2. 检查template_groups (Zabbix 6.4 用 template_groups 不是 groups)
    groups = root.find("template_groups")
    if groups is None:
        errors.append("缺少template_groups节点")
    else:
        group_names = [g.find("name").text for g in groups.findall("template_group") if g.find("name") is not None]
        for required_group in FIXED_GROUPS:
            if required_group not in group_names:
                errors.append(f"缺少固定主机组: {required_group}")

    # 3. 检查templates
    templates = root.find("templates")
    if templates is None:
        errors.append("缺少templates节点")

    # 4. 校验uuid唯一性
    all_uuids = [elem.text for elem in root.iter("uuid")]
    if len(all_uuids) != len(set(all_uuids)):
        errors.append("存在重复的uuid")

    # 5. 校验uuid格式 (32位16进制)
    for u in all_uuids:
        if not re.match(r'^[0-9a-f]{32}$', u):
            errors.append(f"uuid格式错误: {u}")
            break

    # 6. 校验key格式 (全小写、点分隔、无中文)
    for key_elem in root.iter("key"):
        key_text = key_elem.text or ""
        if re.search(r'[A-Z]', key_text) and "{#SNMPINDEX}" not in key_text:
            warnings.append(f"key包含大写字母: {key_text}")
        if re.search(r'[一-鿿]', key_text):
            errors.append(f"key包含中文: {key_text}")

    # 7. 校验delay取值
    valid_delays = {"1m", "5m", "10m", "1d"}
    for delay_elem in root.iter("delay"):
        if delay_elem.text not in valid_delays:
            errors.append(f"delay取值非法: {delay_elem.text}，仅允许 {valid_delays}")

    # 8. 校验SNMP_AGENT类型
    for type_elem in root.iter("type"):
        if type_elem.text and type_elem.text not in ("SNMP_AGENT", "EXTERNAL", "CALCULATED", "INTERNAL", "AGENT", "TRAP", "DEPENDENT"):
            errors.append(f"type值异常: {type_elem.text}")

    # 9. 校验value_type格式 (Zabbix 6.4 用文字)
    valid_value_types = {"FLOAT", "CHAR", "LOG", "UNSIGNED", "TEXT"}
    for vt_elem in root.iter("value_type"):
        if vt_elem.text and vt_elem.text not in valid_value_types:
            warnings.append(f"value_type建议用文字格式(FLOAT/CHAR/TEXT): {vt_elem.text}")

    return ValidateResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )
