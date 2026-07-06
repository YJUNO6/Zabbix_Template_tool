# 产品需求文档 (PRD)

## 项目名称
SNMP MIB 自动生成 Zabbix 6.4 模板网页工具

## 项目背景
运维人员在监控服务器硬件时，需要手动将厂商MIB文件中的OID逐条配置到Zabbix模板中，工作量大、易出错。本工具实现MIB文件自动解析 → 智能分类 → 一键导出Zabbix标准模板XML，大幅提升效率。

## 技术栈
- **后端**: Python FastAPI
- **前端**: Vue3 + Element Plus
- **MIB解析**: pysmi + pysnmp
- **XML生成**: lxml

## 核心功能模块

### 1. 文件上传模块
- 支持单个/批量上传 .mib / .txt 文件
- 支持输入厂商前缀OID过滤 (如联想 1.3.6.1.4.1.53184)
- 文件大小限制 50MB

### 2. 配置表单
| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| 模板前缀 | LW_Template | 模板标识前缀 |
| 模板显示名 | (自动) | 填入Zabbix的name字段 |
| 主机组 | 服务器模板、监控模板 | 固定两组，不可修改 |
| SNMP团体字 | public | {$SNMP_COMMUNITY}宏 |
| 状态类间隔 | 1m | health/status/state类 |
| 性能类间隔 | 5m | temperature/power/speed类 |
| 信息类间隔 | 1d | model/version/serial类 |
| 历史保留 | 7d | 全局统一 |
| 趋势保留 | 30d | 数值类30d，文本类0d |

### 3. 指标自动分类
根据OID名称关键词自动分为三类:

| 分类 | 关键词 | 采集间隔 | 值类型 | 趋势 |
|------|--------|---------|--------|------|
| 状态类 | health/status/state/fault/alarm | 1m | TEXT | 0d |
| 性能类 | temperature/power/speed/capacity/usage/rpm | 5m | FLOAT | 30d |
| 信息类 | model/version/serial/manufacturer/firmware | 1d | TEXT | 0d |

### 4. 自动发现规则 (LLD)
- 表格类OID(有SNMPINDEX) → 生成 discovery_rule + item_prototype
- 常规硬件发现: delay=10m
- 风扇/电源发现: delay=5m
- 发现key格式: 硬件类型.discovery (如 cpu.discovery)

### 5. 健康指标触发器
所有 `xx.health` 指标自动嵌套 trigger_prototype:
```
expression: last(/模板名/指标[{#SNMPINDEX}])<>"Normal"
name: [硬件设备]{HOST.NAME} XX {#SNMPINDEX} 健康状态异常
priority: HIGH
manual_close: YES
```

### 6. XML生成规则
- 根节点: `<zabbix_export version="6.4">`
- 顶层顺序: groups → templates → template → items → discovery_rules → macros
- UUID: 32位随机小写16进制，全局唯一
- SNMP类型: 固定 SNMP_AGENT
- 固定主机组: 服务器模板、监控模板

### 7. 翻译词库
- 内置200+运维标准中英词汇映射
- 前端可自定义新增/修改/删除
- 存储在SQLite数据库

### 8. 任务缓存
- SQLite存储历史解析任务
- 支持二次编辑、重新导出
- 支持删除任务

## API接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/upload | 上传MIB文件 |
| POST | /api/parse | 解析MIB文件 |
| GET | /api/config/defaults | 获取默认配置 |
| POST | /api/export | 导出XML文件 |
| POST | /api/export/preview | 预览XML内容 |
| GET | /api/preview/{task_id} | 获取解析预览数据 |
| GET | /api/translations | 获取翻译词库 |
| POST | /api/translations | 新增翻译 |
| DELETE | /api/translations/{en} | 删除翻译 |
| GET | /api/tasks | 历史任务列表 |
| GET | /api/tasks/{id} | 任务详情 |
| DELETE | /api/tasks/{id} | 删除任务 |
