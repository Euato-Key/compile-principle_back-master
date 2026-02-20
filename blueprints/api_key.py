"""
API密钥管理蓝图
使用数据库存储配置，密码使用哈希加密
"""
from flask import Blueprint, request, jsonify
import hashlib
import requests
from database import get_db_connection

api_key_bp = Blueprint('api_key', __name__, url_prefix='/api')


def _validate_api_key(api_key: str) -> tuple[bool, str]:
    """验证 API 密钥是否有效

    通过调用 DeepSeek 余额查询接口验证密钥

    Returns:
        (is_valid, error_message)
    """
    if not api_key or not api_key.startswith('sk-'):
        return False, "API 密钥格式不正确，应以 'sk-' 开头"

    try:
        response = requests.get(
            'https://api.deepseek.com/user/balance',
            headers={
                'Accept': 'application/json',
                'Authorization': f'Bearer {api_key}'
            },
            timeout=10
        )

        if response.status_code == 200:
            return True, ""
        elif response.status_code == 401:
            return False, "API 密钥无效或已过期"
        else:
            error_data = response.json() if response.text else {}
            error_msg = error_data.get('error', {}).get('message', f'验证失败 (HTTP {response.status_code})')
            return False, error_msg

    except requests.exceptions.Timeout:
        return False, "验证超时，请检查网络连接"
    except requests.exceptions.RequestException as e:
        return False, f"网络错误: {str(e)}"
    except Exception as e:
        return False, f"验证失败: {str(e)}"

def _hash_password(password: str) -> str:
    """对密码进行哈希处理"""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def _verify_password(password: str, hashed: str) -> bool:
    """验证密码"""
    return _hash_password(password) == hashed


def load_api_config():
    """从数据库加载API配置"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('SELECT api_key, admin_password_hash FROM system_config WHERE id = 1')
        row = cursor.fetchone()

        if row:
            return {
                "api_key": row['api_key'],
                "admin_password_hash": row['admin_password_hash']
            }
        else:
            # 创建默认配置
            default_password = "admin123"
            password_hash = _hash_password(default_password)
            cursor.execute('''
                INSERT INTO system_config (id, api_key, admin_password_hash)
                VALUES (1, '', ?)
            ''', (password_hash,))
            conn.commit()
            return {
                "api_key": "",
                "admin_password_hash": password_hash
            }
    except Exception as e:
        print(f"[API Config] 从数据库加载配置失败: {e}")
        # 返回默认配置
        return {
            "api_key": "",
            "admin_password_hash": _hash_password("admin123")
        }
    finally:
        conn.close()


def save_api_config(api_key: str = None, admin_password: str = None):
    """保存API配置到数据库

    Args:
        api_key: API密钥（可选）
        admin_password: 管理员密码明文（可选，会哈希存储）
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 先查询现有配置
        cursor.execute('SELECT api_key, admin_password_hash FROM system_config WHERE id = 1')
        row = cursor.fetchone()

        if row:
            current_api_key = row['api_key']
            current_hash = row['admin_password_hash']
        else:
            current_api_key = ""
            current_hash = _hash_password("admin123")

        # 更新值
        new_api_key = api_key if api_key is not None else current_api_key
        new_hash = _hash_password(admin_password) if admin_password is not None else current_hash

        if row:
            cursor.execute('''
                UPDATE system_config 
                SET api_key = ?, admin_password_hash = ?
                WHERE id = 1
            ''', (new_api_key, new_hash))
        else:
            cursor.execute('''
                INSERT INTO system_config (id, api_key, admin_password_hash)
                VALUES (1, ?, ?)
            ''', (new_api_key, new_hash))

        conn.commit()
        return True
    except Exception as e:
        print(f"[API Config] 保存配置失败: {e}")
        return False
    finally:
        conn.close()


def _mask_api_key(api_key: str) -> str:
    """对API密钥进行掩码处理

    例如: sk-abc1234567890xyz → sk-abc1...xyz9
    """
    if not api_key:
        return "未配置"
    if len(api_key) < 12:
        # 密钥太短，只显示前3位
        return api_key[:3] + "..."
    # 显示前6位和后4位，中间用...代替
    return api_key[:6] + "..." + api_key[-4:]


@api_key_bp.route('/getApiKey', methods=['GET'])
def get_api_key():
    """获取API密钥（需要密码验证）- 返回掩码版本，防止泄露"""
    password = request.headers.get('X-Admin-Password')
    if not password:
        return jsonify({
            "code": 401,
            "msg": "缺少管理员密码"
        }), 401

    config = load_api_config()
    if not _verify_password(password, config.get('admin_password_hash', '')):
        return jsonify({
            "code": 403,
            "msg": "密码错误"
        }), 403

    # 返回掩码版本的API密钥，防止在响应中泄露完整密钥
    masked_key = _mask_api_key(config.get('api_key', ''))

    return jsonify({
        "code": 0,
        "data": {
            "api_key": masked_key
        }
    }), 200


@api_key_bp.route('/updateApiKey', methods=['POST'])
def update_api_key():
    """更新API密钥（需要密码验证，会先验证密钥有效性）"""
    data = request.get_json()
    if not data:
        return jsonify({
            "code": 400,
            "msg": "请求体不能为空"
        }), 400

    old_password = data.get('old_password')
    new_api_key = data.get('new_api_key')

    if not old_password:
        return jsonify({
            "code": 400,
            "msg": "缺少原密码"
        }), 400

    if not new_api_key:
        return jsonify({
            "code": 400,
            "msg": "缺少新的API密钥"
        }), 400

    config = load_api_config()

    # 验证原密码
    if not _verify_password(old_password, config.get('admin_password_hash', '')):
        return jsonify({
            "code": 403,
            "msg": "原密码错误"
        }), 403

    # 验证新 API 密钥有效性
    is_valid, error_msg = _validate_api_key(new_api_key)
    if not is_valid:
        return jsonify({
            "code": 400,
            "msg": f"API 密钥验证失败: {error_msg}"
        }), 400

    # 更新配置
    if save_api_config(api_key=new_api_key):
        return jsonify({
            "code": 0,
            "msg": "API密钥更新成功",
            "data": {
                "api_key_updated": True
            }
        }), 200
    else:
        return jsonify({
            "code": 500,
            "msg": "保存配置失败"
        }), 500


@api_key_bp.route('/updateAdminPassword', methods=['POST'])
def update_admin_password():
    """单独更新管理员密码"""
    data = request.get_json()
    if not data:
        return jsonify({
            "code": 400,
            "msg": "请求体不能为空"
        }), 400

    old_password = data.get('old_password')
    new_password = data.get('new_password')

    if not old_password or not new_password:
        return jsonify({
            "code": 400,
            "msg": "缺少原密码或新密码"
        }), 400

    config = load_api_config()

    # 验证原密码
    if not _verify_password(old_password, config.get('admin_password_hash', '')):
        return jsonify({
            "code": 403,
            "msg": "原密码错误"
        }), 403

    # 更新密码
    if save_api_config(admin_password=new_password):
        return jsonify({
            "code": 0,
            "msg": "密码修改成功"
        }), 200
    else:
        return jsonify({
            "code": 500,
            "msg": "保存配置失败"
        }), 500


@api_key_bp.route('/admin/verify-password', methods=['POST'])
def verify_admin_password():
    """验证管理员密码"""
    data = request.get_json()
    if not data:
        return jsonify({
            "code": 400,
            "msg": "请求体不能为空"
        }), 400

    password = data.get('password')
    if not password:
        return jsonify({
            "code": 400,
            "msg": "缺少密码"
        }), 400

    config = load_api_config()

    if _verify_password(password, config.get('admin_password_hash', '')):
        return jsonify({
            "code": 0,
            "msg": "验证成功"
        }), 200
    else:
        return jsonify({
            "code": 403,
            "msg": "密码错误"
        }), 403
