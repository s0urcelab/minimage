[English README](README.md)

# minimage 极简图床

一个极简的图床，一切功能仅通过API。

## 功能特性

- 🔐 带鉴权校验的图片上传
- 📁 本地文件存储（`/app/uploads` 目录）
- ⏰ 自动清理：图片到期后自动删除（可配置）
- 🔒 文件类型和大小限制（PNG, JPG, JPEG, GIF, BMP, WEBP）
- 🐳 容器化部署，健康检查


## 快速开始

### 使用Docker Compose（推荐）

1. 克隆或下载项目文件
2. 修改 `docker-compose.yml` 中的鉴权值（可选）
3. 运行服务：

```bash
PUID=$(id -u) PGID=$(id -g) UMASK=022 docker-compose up -d

# 或直接运行容器
docker run -d -p 9527:9527 \
  -e PUID=$(id -u) \
  -e PGID=$(id -g) \
  -e UMASK=022 \
  -v $(pwd)/uploads:/app/uploads ghcr.io/your-username/minimage:latest
```

服务将在 `http://localhost:9527` 启动

## API接口

### 1. 上传图片

```bash
curl -X POST \
  -H "X-Upload-Auth: admin123" \
  -F "file=@image.jpg" \
  -F "expires_in=300" \
  http://localhost:9527/upload
```

**参数：**
- Header `X-Upload-Auth`（必填）：需与环境变量 `UPLOAD_AUTH_TOKEN` 一致
- Form `file`（必填）：图片文件
- Form/Query `expires_in`（可选）：有效期（秒）；传 `0` 表示永久有效；未传使用默认值

**响应（200）：**
```json
{
  "success": true,
  "message": "上传成功",
  "data": {
    "filename": "a3d3c2c1-1a2b-3c4d-5e6f.jpg",
    "url": "/i/a3d3c2c1-1a2b-3c4d-5e6f.jpg",
    "size": 1024000,
    "expires_in": 300
  }
}
```

### 2. 访问图片

**GET** `/i/<filename>`

- 返回原始图片内容
- 文件不存在或已过期将返回 404


### 3. 删除图片

```bash
curl -X POST \
  -H "X-Upload-Auth: admin123" \
  -F "filename=a3d3c2c1-1a2b-3c4d-5e6f.jpg" \
  http://localhost:9527/delete
```

响应（200）：`{ "success": true, "message": "删除成功" }`



### 5. 根路径元信息

**GET** `/`

返回服务元信息及运行配置示例：
```json
{
  "name": "minimage",
  "version": "latest",
  "features": {
    "default_file_lifetime_seconds": 300,
    "cleanup_interval_seconds": 600,
    "max_file_size_mb": 10
  }
}
```

## 配置说明

### 环境变量

- `UPLOAD_AUTH_TOKEN`: 上传鉴权token，默认 `admin123`
- `MAX_FILE_SIZE_MB`: 文件体积限制（MB），默认 `10`
- `FILE_LIFETIME`: 默认文件过期时间（秒），默认 `0`
- `CLEANUP_INTERVAL`: 清理检查间隔（秒），默认 `600`
- `PUID`: 容器内运行用户的 UID（用于生成文件的所有权），默认 `0`
- `PGID`: 容器内运行用户的 GID（用于生成文件的所有权），默认 `0`
- `UMASK`: 进程文件创建掩码（影响上传文件/日志的权限），默认 `022`

## 许可证

[MIT](LICENSE)

