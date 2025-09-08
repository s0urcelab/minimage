#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import uuid
import threading
import time
import sqlite3
from flask import Flask, request, jsonify, send_file, abort, g
from werkzeug.exceptions import HTTPException
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
UPLOAD_AUTH_TOKEN = os.getenv('UPLOAD_AUTH_TOKEN', 'admin123') # 鉴权token
FILE_LIFETIME = int(os.getenv('FILE_LIFETIME', 0))  # 默认过期时间，秒（默认永久有效）
CLEANUP_INTERVAL = int(os.getenv('CLEANUP_INTERVAL', str(10 * 60)))  # 清理检查间隔，秒（默认10分钟）
DB_PATH = os.getenv('DB_PATH', 'images.db')

# 确保上传目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 仅启动一次清理线程（兼容 Gunicorn 多进程/多线程场景）
_cleanup_started = False
_cleanup_lock = threading.Lock()
def get_db():
    """获取当前请求上下文的 SQLite 连接，使用 Flask g 进行生命周期管理。"""
    if 'db' not in g:
        db = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
        g.db = db
    return g.db

def close_db(e=None):
    """在应用上下文结束时关闭连接。"""
    db = g.pop('db', None)
    if db is not None:
        db.close()
        
@app.teardown_appcontext
def _teardown_close_db(exception):
    close_db(exception)

def init_database():
    """初始化SQLite数据库及 image 表。

    表结构：
    - filename TEXT PRIMARY KEY
    - expires_in INTEGER  // 0 表示永久有效
    - created_at INTEGER  // Unix 时间戳（秒）
    """
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS image (
                filename TEXT PRIMARY KEY,
                expires_in INTEGER NOT NULL,
                created_at INTEGER NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()

def insert_image_record(filename: str, expires_in: int, created_at: int, conn: sqlite3.Connection = None) -> None:
    """插入或替换一条图片记录。"""
    db = conn or get_db()
    db.execute(
        "INSERT OR REPLACE INTO image (filename, expires_in, created_at) VALUES (?, ?, ?)",
        (filename, expires_in, created_at),
    )
    db.commit()

def get_image_record(filename: str, conn: sqlite3.Connection = None):
    """根据文件名查询图片记录，不存在返回 None。"""
    db = conn or get_db()
    cur = db.execute(
        "SELECT filename, expires_in, created_at FROM image WHERE filename = ?",
        (filename,),
    )
    row = cur.fetchone()
    return dict(row) if row else None

def delete_image_record(filename: str, conn: sqlite3.Connection = None) -> None:
    """删除图片记录。"""
    db = conn or get_db()
    db.execute("DELETE FROM image WHERE filename = ?", (filename,))
    db.commit()

def list_expired_images(now_ts: int, conn: sqlite3.Connection = None):
    """列出已过期的图片文件名列表（不包含永久有效的记录）。"""
    db = conn or get_db()
    cur = db.execute(
        "SELECT filename FROM image WHERE expires_in > 0 AND (created_at + expires_in) <= ?",
        (now_ts,),
    )
    return [r[0] for r in cur.fetchall()]

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
    # 组合文件名（仅uuid与扩展名）
    if ext:
        return f"{unique_id}.{ext}"
    else:
        return f"{unique_id}"

def cleanup_old_files():
    """后台清理过期文件任务：根据数据库记录判断是否过期。"""
    # 清理线程使用独立连接，避免依赖 Flask 上下文
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    while True:
        try:
            now_ts = int(time.time())
            deleted_count = 0
            if not os.path.exists(UPLOAD_FOLDER):
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            # 查询已过期的文件列表（使用线程内连接）
            expired_files = list_expired_images(now_ts, conn)
            for name in expired_files:
                file_path = os.path.join(UPLOAD_FOLDER, name)
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                    delete_image_record(name, conn)
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
    logger.info(f"清理任务已启动，默认过期时间: {'永久有效' if int(FILE_LIFETIME) == 0 else f'{FILE_LIFETIME}s'}，检查间隔: {CLEANUP_INTERVAL}s")

# 初始化数据库并无条件启动清理线程
init_database()
ensure_cleanup_started_once()

@app.route('/upload', methods=['POST'])
def upload_file():
    """
    上传图片接口
    需要在Header中提供 X-Upload-Auth 进行校验
    """
    try:
        # 检查Header中的鉴权
        auth = request.headers.get('X-Upload-Auth')
        if not auth or auth != UPLOAD_AUTH_TOKEN:
            return jsonify({
                'success': False,
                'message': '鉴权token错误或未提供'
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
        
        # 读取有效期参数（秒）：表单字段 expires_in；未提供则使用默认 FILE_LIFETIME
        # 传入 0 表示永久有效
        expires_in_param = request.form.get('expires_in') or request.args.get('expires_in')
        try:
            if expires_in_param is None or str(expires_in_param).strip() == '':
                expires_in = FILE_LIFETIME
            else:
                expires_in = int(expires_in_param)
                if expires_in < 0:
                    return jsonify({'success': False, 'message': 'expires_in 不能为负数'}), 400
        except ValueError:
            return jsonify({'success': False, 'message': 'expires_in 必须是整数'}), 400

        # 生成安全的文件名
        original_filename = secure_filename(file.filename)
        new_filename = generate_filename(original_filename)
        file_path = os.path.join(UPLOAD_FOLDER, new_filename)
        
        # 保存文件
        file.save(file_path)
        
        # 写入数据库记录
        created_at = int(time.time())
        insert_image_record(new_filename, expires_in, created_at)
        
        logger.info(f"文件上传成功: {original_filename} -> {new_filename}")
        
        return jsonify({
            'success': True,
            'message': '上传成功',
            'data': {
                'filename': new_filename,
                'url': f"/i/{new_filename}",
                'size': file_size,
                'expires_in': expires_in
            }
        })
        
    except Exception as e:
        logger.error(f"上传文件时发生错误: {str(e)}")
        return jsonify({
            'success': False,
            'message': '上传出错'
        }), 500

@app.route('/i/<filename>')
def get_image(filename):
    """
    获取图片接口
    通过文件名访问已上传的图片
    """
    try:
        # 安全检查：确保文件名不包含路径分隔符
        if '/' in filename or '\\' in filename:
            abort(404)
        
        # 查询数据库记录，若不存在或已过期，返回404
        rec = get_image_record(filename)
        now_ts = int(time.time())
        if (rec is None) or (rec['expires_in'] > 0 and (rec['created_at'] + rec['expires_in']) <= now_ts):
            abort(404)

        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if not os.path.exists(file_path):
            abort(404)

        return send_file(file_path)
        
    except HTTPException:
        # 直接抛出由 abort 触发的 HTTP 异常（如 404）
        raise
    except Exception as e:
        logger.error(f"获取图片发生错误: {str(e)}")
        abort(500)

# 新增删除接口
@app.route('/delete', methods=['POST'])
def delete_file():
    """
    删除指定文件接口（POST /delete）
    请求参数：filename
    采用与上传相同的 X-Upload-Auth 鉴权。
    """
    try:
        auth = request.headers.get('X-Upload-Auth')
        if not auth or auth != UPLOAD_AUTH_TOKEN:
            return jsonify({'success': False, 'message': '鉴权token错误或未提供'}), 401

        # 仅支持表单字段
        filename = request.form.get('filename')
        if not filename:
            return jsonify({'success': False, 'message': '缺少参数 filename'}), 400

        # 安全检查
        if '/' in filename or '\\' in filename:
            return jsonify({'success': False, 'message': '非法文件名'}), 400

        # 删除文件与记录
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)
            delete_image_record(filename)

        return jsonify({'success': True, 'message': '删除成功'})
    except Exception as e:
        logger.error(f"删除文件时发生错误: {e}")
        return jsonify({'success': False, 'message': '删除失败'}), 500

@app.route('/')
def index():
    """根路径：返回meta信息"""
    return jsonify({
        'name': 'minimage',
        'version': os.getenv('IMAGE_VERSION', 'latest'),
        'features': {
            'default_file_lifetime_seconds': FILE_LIFETIME,
            'cleanup_interval_seconds': CLEANUP_INTERVAL,
            'max_file_size_mb': MAX_FILE_SIZE_MB,
        },
    })

@app.route('/health')
def health_check():
    """健康检查接口"""
    return index()

if __name__ == '__main__':
    port = 9527
    logger.info(f"应用启动，端口: {port}")
    logger.info(f"鉴权Token: {UPLOAD_AUTH_TOKEN}")
    logger.info(f"上传目录: {UPLOAD_FOLDER}")
    logger.info(f"数据库: {DB_PATH}")
    
    app.run(host='0.0.0.0', port=port, debug=False)
