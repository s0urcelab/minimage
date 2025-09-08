[中文 (Chinese)](README.zh-CN.md)

# minimage

A minimalist image hosting service with API only.

## Features

- Auth-protected image upload
- Local file storage (mounted at `/app/uploads`)
- Optional auto-cleanup for expired files (configurable)
- File type and size validation (PNG, JPG, JPEG, GIF, BMP, WEBP)
- Dockerized, healthcheck


## Quick Start

### Using Docker Compose (recommended)

1) Clone this repo and optionally edit the auth in `docker-compose.yml`

2) Start service:

```bash
PUID=$(id -u) PGID=$(id -g) UMASK=022 docker compose up -d

# or you can docker run
docker run -d -p 9527:9527 \
  -e PUID=$(id -u) \
  -e PGID=$(id -g) \
  -e UMASK=022 \
  -v $(pwd)/uploads:/app/uploads ghcr.io/your-username/minimage:latest
```

Service will be available at `http://localhost:9527`.

## API

### 1. Upload

```bash
curl -X POST \
  -H "X-Upload-Auth: admin123" \
  -F "file=@image.jpg" \
  -F "expires_in=300" \
  http://localhost:9527/upload
```

Parameters:
- Header `X-Upload-Auth` (required): must match `UPLOAD_AUTH_TOKEN`
- Form `file` (required): the image file
- Form or query `expires_in` (optional): seconds; `0` means never expire; default to `FILE_LIFETIME`

Response (200):
```json
{
  "success": true,
  "message": "upload complete",
  "data": {
    "filename": "a3d3c2c1-1a2b-3c4d-5e6f.jpg",
    "url": "/image/a3d3c2c1-1a2b-3c4d-5e6f.jpg",
    "size": 1024000,
    "expires_in": 300
  }
}
```

### 2. Get Image

GET `/image/<filename>`

- Returns the raw image.
- 404 if not found or expired.

### 3. Delete

```bash
curl -X POST \
  -H "X-Upload-Auth: admin123" \
  -F "filename=a3d3c2c1-1a2b-3c4d-5e6f.jpg" \
  http://localhost:9527/delete
```

Response (200): `{ "success": true, "message": "delete complete" }`



### 5. Index

GET `/` returns service metadata and runtime config, for example:

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

## Configuration

Environment variables:
- `UPLOAD_AUTH_TOKEN`: upload auth token (default: `admin123`)
- `MAX_FILE_SIZE_MB`: max upload size in MB (default: `10`)
- `FILE_LIFETIME`: default file expiration in seconds (default: `0`)
- `CLEANUP_INTERVAL`: cleanup interval in seconds (default: `600`)
- `PUID`: process user ID inside container for file ownership (default: `0`)
- `PGID`: process group ID inside container for file ownership (default: `0`)
- `UMASK`: file creation mask for uploads/logs (default: `022`)

## License

[MIT](LICENSE)
