FROM python:3.12-slim

WORKDIR /app

# 安装系统依赖 (lxml编译需要)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libxml2-dev \
    libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖 (利用Docker缓存层)
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt

# 源码通过 volume 挂载，这里只创建数据目录
RUN mkdir -p /app/data /app/uploads /app/data/compiled_mibs

EXPOSE 8000

# --reload: 代码修改后自动重启，开发用
# 生产环境去掉 --reload，改用 --workers 4
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
