# 使用Python 3.11官方镜像作为基础镜像
FROM python:3.11-slim

# Python 运行时优化
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 设置工作目录
WORKDIR /app

RUN apt-get update \ 
    && apt-get install -y --no-install-recommends curl gosu \ 
    && rm -rf /var/lib/apt/lists/*

# 创建上传目录
RUN mkdir -p /app/data/uploads

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY app.py .
COPY gunicorn.conf.py .
COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

# 默认执行权限
ENV PUID=0 PGID=0 UMASK=022

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:9527/health || exit 1

ARG IMAGE_VERSION=latest
ENV IMAGE_VERSION=${IMAGE_VERSION}

# 暴露端口
EXPOSE 9527

# 使用启动脚本，支持运行时 PUID/PGID/UMASK 覆盖
ENTRYPOINT ["/entrypoint.sh"]

# CMD ["gunicorn", "-k", "gevent", "-w", "1", "-b", "0.0.0.0:9527", "app:app"]

