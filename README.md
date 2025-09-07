[中文 (Chinese)](README.zh-CN.md)

# minimage

A minimalist image hosting service with API only.

## Features

- Password-protected image upload 
- Local file storage (mounted at `/app/uploads`)
- Optional auto-cleanup for expired files (configurable)
- File type and size validation (PNG, JPG, JPEG, GIF, BMP, WEBP)
- Dockerized, healthcheck


## Quick Start

### Using Docker Compose (recommended)

1) Clone this repo and optionally edit the password in `docker-compose.yml`

2) Start service:

```bash
docker compose up -d
```

Service will be available at `http://localhost:5000`.

## API

### 1. Upload

```bash
curl -X POST \
  -H "X-Upload-Password: admin123" \
  -F "file=@image.jpg" \
  http://localhost:5000/upload
```

Response:
```json
{
  "success": true,
  "message": "uploaded",
  "filename": "20231201_143022_abc123.jpg",
  "url": "/image/20231201_143022_abc123.jpg",
  "size": 1024000,
  "expires_in": 300
}
```

### 2. Get Image

GET `/image/<filename>`

### 3. Healthcheck

GET `/health`

### 4. Index

GET `/` returns basic metadata and config.

## Configuration

Environment variables:
- `UPLOAD_PASSWORD`: upload password (default: `admin123`)
- `MAX_FILE_SIZE_MB`: max upload size in MB (default: `10`)
- `FILE_LIFETIME`: file expiration in seconds (default: `300`)
- `CLEANUP_INTERVAL`: cleanup interval in seconds (default: `60`)
- `AUTO_CLEANUP_ENABLED`: enable auto cleanup (`true/false`), default `false`

## License

[MIT](LICENSE)
