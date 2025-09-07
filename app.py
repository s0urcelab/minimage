#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import hashlib
import uuid
import threading
import time
from datetime import datetime
from flask import Flask, request, jsonify, send_file, abort
from werkzeug.utils import secure_filename
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 配置
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
MAX_FILE_SIZE_MB = int(os.getenv('MAX_FILE_SIZE_MB', '10')) # 最大文件大小
MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024
UPLOAD_PASSWORD = os.getenv('UPLOAD_PASSWORD', 'admin123')  # 默认密码，可通过环境变量修改
FILE_LIFETIME = int(os.getenv('FILE_LIFETIME', str(5 * 60)))  # 过期时间，秒，默认5分钟
CLEANUP_INTERVAL = int(os.getenv('CLEANUP_INTERVAL', '60'))  # 清理检查间隔，秒
# 自动清理开关（默认关闭）：true/false, 1/0, yes/no, on/off
AUTO_CLEANUP_ENABLED = os.getenv('AUTO_CLEANUP_ENABLED', 'false').strip().lower() in {'1', 'true', 'yes', 'on'}

# 确保上传目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 仅启动一次清理线程（兼容 Gunicorn 多进程/多线程场景）
_cleanup_started = False
_cleanup_lock = threading.Lock()

def ensure_cleanup_started_once():
    """确保清理线程仅启动一次。

    在 Gunicorn 下，多个 worker 可能并发初始化应用，此处通过进程内锁与标志位防重入。
    """
    global _cleanup_started
    if _cleanup_started:
        return
    with _cleanup_lock:
        if not _cleanup_started:
            start_cleanup_thread()
            _cleanup_started = True

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def generate_filename(original_filename):
    """生成唯一的文件名"""
    # 获取文件扩展名
    ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
    
    # 生成唯一ID
    unique_id = str(uuid.uuid4())
    
    # 添加时间戳
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 组合文件名
    if ext:
        return f"{timestamp}_{unique_id}.{ext}"
    else:
        return f"{timestamp}_{unique_id}"

def cleanup_old_files():
    """后台清理过期文件任务：按修改时间判断是否超时"""
    while True:
        try:
            now_ts = time.time()
            deleted_count = 0
            if not os.path.exists(UPLOAD_FOLDER):
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            for name in os.listdir(UPLOAD_FOLDER):
                file_path = os.path.join(UPLOAD_FOLDER, name)
                try:
                    if not os.path.isfile(file_path):
                        continue
                    mtime = os.path.getmtime(file_path)
                    if now_ts - mtime > FILE_LIFETIME:
                        os.remove(file_path)
                        deleted_count += 1
                        logger.info(f"已删除过期文件: {name}")
                except Exception as file_err:
                    logger.error(f"检查/删除文件 {name} 时发生错误: {file_err}")
            if deleted_count:
                logger.info(f"本次清理删除 {deleted_count} 个过期文件")
        except Exception as e:
            logger.error(f"清理任务发生错误: {e}")
        time.sleep(CLEANUP_INTERVAL)

def start_cleanup_thread():
    """启动守护线程执行定时清理任务"""
    t = threading.Thread(target=cleanup_old_files, daemon=True)
    t.start()
    logger.info(
        f"清理任务已启动，过期时间: {FILE_LIFETIME}s，检查间隔: {CLEANUP_INTERVAL}s")

# 在应用初始化后按需启动清理线程
if AUTO_CLEANUP_ENABLED:
    ensure_cleanup_started_once()

@app.route('/upload', methods=['POST'])
def upload_file():
    """
    上传图片接口
    需要在Header中提供X-Upload-Password进行校验
    """
    try:
        # 检查Header中的密码
        password = request.headers.get('X-Upload-Password')
        if not password or password != UPLOAD_PASSWORD:
            return jsonify({
                'success': False,
                'message': '密码错误或未提供密码'
            }), 401
        
        # 检查是否有文件
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'message': '没有选择文件'
            }), 400
        
        file = request.files['file']
        
        # 检查文件名
        if file.filename == '':
            return jsonify({
                'success': False,
                'message': '没有选择文件'
            }), 400
        
        # 检查文件类型
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'message': f'不支持的文件类型，支持的格式: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400
        
        # 检查文件大小
        file.seek(0, 2)  # 移动到文件末尾
        file_size = file.tell()
        file.seek(0)  # 重置到文件开头
        
        if file_size > MAX_FILE_SIZE:
            return jsonify({
                'success': False,
                'message': f'文件过大，最大支持 {MAX_FILE_SIZE_MB}MB'
            }), 400
        
        # 生成安全的文件名
        original_filename = secure_filename(file.filename)
        new_filename = generate_filename(original_filename)
        file_path = os.path.join(UPLOAD_FOLDER, new_filename)
        
        # 保存文件
        file.save(file_path)
        
        # 生成访问URL
        file_url = f"/image/{new_filename}"
        
        logger.info(f"文件上传成功: {original_filename} -> {new_filename}")
        
        return jsonify({
            'success': True,
            'message': '上传成功',
            'filename': new_filename,
            'url': file_url,
            'size': file_size,
            'expires_in': FILE_LIFETIME
        })
        
    except Exception as e:
        logger.error(f"上传文件时发生错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': '服务器内部错误'
        }), 500

@app.route('/image/<filename>')
def get_image(filename):
    """
    获取图片接口
    通过文件名访问已上传的图片
    """
    try:
        # 安全检查：确保文件名不包含路径分隔符
        if '/' in filename or '\\' in filename:
            abort(404)
        
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            abort(404)
        
        # 返回文件
        return send_file(file_path)
        
    except Exception as e:
        logger.error(f"获取图片时发生错误: {str(e)}")
        abort(500)

@app.route('/health')
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'healthy',
        'message': '图床服务运行正常'
    })

@app.route('/')
def index():
    """根路径，返回API使用说明"""
    return jsonify({
        'name': 'minimage',
        'version': os.getenv('IMAGE_VERSION', 'latest'),
        'features': {
            'auto_cleanup': AUTO_CLEANUP_ENABLED,
            'file_lifetime_seconds': FILE_LIFETIME,
            'cleanup_interval_seconds': CLEANUP_INTERVAL,
            'max_file_size_mb': MAX_FILE_SIZE_MB
        },
        'endpoints': {
            'upload': {
                'method': 'POST',
                'url': '/upload',
                'description': '上传图片，需要在Header中提供X-Upload-Password',
                'headers': {
                    'X-Upload-Password': '上传密码'
                },
                'params': {
                    'file': '图片文件'
                }
            },
            'get_image': {
                'method': 'GET',
                'url': '/image/<filename>',
                'description': '获取图片'
            },
            'health': {
                'method': 'GET',
                'url': '/health',
                'description': '健康检查'
            }
        }
    })

if __name__ == '__main__':
    port = 5000
    logger.info(f"图床应用启动，端口: {port}")
    logger.info(f"上传密码: {UPLOAD_PASSWORD}")
    logger.info(f"上传目录: {UPLOAD_FOLDER}")
    
    app.run(host='0.0.0.0', port=port, debug=False)
