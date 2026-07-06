# SNMP MIB to Zabbix 6.4 Template Tool

MIB文件自动解析 → 智能分类 → 一键导出Zabbix标准模板XML

## 环境要求

| 软件 | 版本 | 下载地址 |
|------|------|---------|
| Python | 3.9+ | https://python.org |
| Node.js | 16+ | https://nodejs.org |

## 一键启动

```cmd
cd src
start.bat
```

双击 `src/start.bat` 或在命令行执行，自动完成：
1. 安装后端Python依赖
2. 启动后端服务 (端口8000)
3. 安装前端Node依赖
4. 启动前端服务 (端口5173)

启动后打开浏览器访问: **http://localhost:5173**

## 手动启动

如果一键脚本有问题，可以分两步手动启动：

**终端1 - 启动后端:**
```cmd
cd src\backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

**终端2 - 启动前端:**
```cmd
cd src\frontend
npm install
npm run dev
```

## 访问地址

| 页面 | 地址 | 说明 |
|------|------|------|
| 前端主页 | http://localhost:5173 | MIB上传、配置、预览、导出 |
| API文档 | http://localhost:8000/docs | 后端接口文档(Swagger) |
| 后端健康检查 | http://localhost:8000/health | 检查后端是否运行 |

## 功能说明

1. **上传MIB** - 拖入.mib文件，输入厂商OID前缀
2. **自动解析** - 识别所有OID，自动分类(状态/性能/信息)
3. **选择发现规则** - 勾选需要的表，可进一步选择每个表的监控项原型
4. **调整配置** - 修改模板名、采集间隔、SNMP团体字等
5. **导出XML** - 下载标准Zabbix 6.4 XML，直接导入Zabbix

## 相关文档

- [产品需求文档](docs/PRD.md)
- [使用说明](docs/使用说明.md)
- [测试指南](docs/测试指南.md)
- [开发笔记](notes/开发笔记.md)
- [AI开发规范](AGENTS.md)
