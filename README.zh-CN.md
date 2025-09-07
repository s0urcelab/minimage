[English README](README.md)

# minimage 极简图床

一个极简的图床，一切功能仅通过API。

## 功能特性

- 🔐 带密码校验的图片上传
- 📁 本地文件存储（`/app/uploads` 目录）
- ⏰ 自动清理：图片到期后自动删除（可配置）
- 🔒 文件类型和大小限制（PNG, JPG, JPEG, GIF, BMP, WEBP）
- 🐳 容器化部署，健康检查


## 快速开始

### 使用Docker Compose（推荐）

1. 克隆或下载项目文件
2. 修改 `docker-compose.yml` 中的密码（可选）
3. 运行服务：

```bash
docker-compose up -d
```

服务将在 `http://localhost:5000` 启动

## API接口

### 1. 上传图片

```bash
curl -X POST \
  -H "X-Upload-Password: admin123" \
  -F "file=@image.jpg" \
  http://localhost:5000/upload
```

**响应：**
```json
{
  "success": true,
  "message": "上传成功",
  "filename": "20231201_143022_abc123.jpg",
  "url": "/image/20231201_143022_abc123.jpg",
  "size": 1024000,
  "expires_in": 300
}
```

### 2. 访问图片

**GET** `/image/<filename>`


### 3. 健康检查

**GET** `/health`


### 4. API文档

**GET** `/`

返回完整的API使用说明

## 配置说明

### 环境变量

- `UPLOAD_PASSWORD`: 上传密码，默认 `admin123`
- `MAX_FILE_SIZE_MB`: 文件体积限制（MB），默认 `10`
- `FILE_LIFETIME`: 文件过期时间（秒），默认 `300`
- `CLEANUP_INTERVAL`: 清理检查间隔（秒），默认 `60`
- `AUTO_CLEANUP_ENABLED`: 是否启用自动清理（`true/false`），默认 `false`

## 许可证

[MIT](LICENSE)

