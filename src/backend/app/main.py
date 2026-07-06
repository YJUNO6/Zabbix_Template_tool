"""
SNMP MIB 自动生成 Zabbix 6.4 模板工具
FastAPI 后端入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .api.routes import router
from .core.database import init_app
from .core.config import CORS_ORIGINS, API_HOST, API_PORT

# 创建FastAPI应用
app = FastAPI(
    title="SNMP MIB to Zabbix Template Tool",
    description="MIB文件解析 → 自动生成Zabbix 6.4标准模板XML",
    version="1.0.0",
)

# CORS跨域配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册API路由
app.include_router(router)


@app.on_event("startup")
async def startup():
    """应用启动初始化"""
    init_app()
    print("=" * 50)
    print("SNMP MIB → Zabbix Template Tool")
    print(f"API Server: http://{API_HOST}:{API_PORT}")
    print(f"API Docs:   http://{API_HOST}:{API_PORT}/docs")
    print("=" * 50)


@app.get("/")
async def root():
    return {
        "name": "SNMP MIB → Zabbix 6.4 Template Tool",
        "version": "1.0.0",
        "docs": "/docs",
        "api": "/api",
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


# 启动入口
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=API_HOST, port=API_PORT, reload=True)
