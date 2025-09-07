# 使用Python 3.11官方镜像作为基础镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装运行所需工具（curl用于健康检查）
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# 创建上传目录
RUN mkdir -p /app/uploads

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY app.py .

# 创建非root用户运行应用
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app
USER app

# 暴露端口
EXPOSE 5000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

ARG IMAGE_VERSION=latest
ENV IMAGE_VERSION=${IMAGE_VERSION}

# 使用 Gunicorn + gevent
CMD ["gunicorn", "-k", "gevent", "-w", "1", "-b", "0.0.0.0:5000", "app:app"]
