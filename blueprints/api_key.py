"""
API密钥管理蓝图
使用数据库存储配置，密码使用哈希加密
支持 DeepSeek 和 Hunyuan 双模型配置

注意：API 密钥验证使用 requests 直接调用 DeepSeek 余额接口，
因为 OpenAI SDK 不支持查询余额功能
"""
from flask import Blueprint, request, jsonify
import hashlib
import requests
from database import get_db_connection

api_key_bp = Blueprint('api_key', __name__, url_prefix='/api')

# 模型选择策略
MODEL_STRATEGY_DEEPSEEK = "deepseek"      # 强制使用 DeepSeek
MODEL_STRATEGY_HUNYUAN = "hunyuan"        # 强制使用 Hunyuan
MODEL_STRATEGY_DYNAMIC = "dynamic"        # 动态切换（余额不足时自动切换到 Hunyuan）

# 余额阈值（元）
BALANCE_THRESHOLD = 0.3


def _validate_deepseek_key(api_key: str) -> tuple[bool, str]:
    """验证 DeepSeek API 密钥是否有效

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


def _validate_hunyuan_key(api_key: str) -> tuple[bool, str]:
    """验证 Hunyuan API 密钥是否有效

    通过发起一个简单的请求来验证
    """
    if not api_key:
        return False, "API 密钥不能为空"

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url="https://api.hunyuan.cloud.tencent.com/v1")
        
        # 发起一个简单的请求验证密钥
        response = client.chat.completions.create(
            model="hunyuan-lite",
            messages=[{"role": "user", "content": "test"}],
            max_tokens=1,
            stream=False
        )
        return True, ""
    except Exception as e:
        return False, f"Hunyuan API 密钥验证失败: {str(e)}"


def _hash_password(password: str) -> str:
    """对密码进行哈希处理"""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def _verify_password(password: str, hashed: str) -> bool:
    """验证密码"""
    return _hash_password(password) == hashed


def _ensure_config_table():
    """确保配置表包含所有需要的字段"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='system_config'")
        if not cursor.fetchone():
            # 创建表
            cursor.execute('''
                CREATE TABLE system_config (
                    id INTEGER PRIMARY KEY,
                    api_key TEXT DEFAULT '',
                    hunyuan_api_key TEXT DEFAULT '',
                    model_strategy TEXT DEFAULT 'dynamic',
                    admin_password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
            return
        
        # 检查并添加缺失的列
        cursor.execute("PRAGMA table_info(system_config)")
        columns = [row['name'] for row in cursor.fetchall()]
        
        if 'hunyuan_api_key' not in columns:
            cursor.execute("ALTER TABLE system_config ADD COLUMN hunyuan_api_key TEXT DEFAULT ''")
        if 'model_strategy' not in columns:
            cursor.execute("ALTER TABLE system_config ADD COLUMN model_strategy TEXT DEFAULT 'dynamic'")
        if 'created_at' not in columns:
            cursor.execute("ALTER TABLE system_config ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        if 'updated_at' not in columns:
            cursor.execute("ALTER TABLE system_config ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        
        conn.commit()
    except Exception as e:
        print(f"[API Config] 更新表结构失败: {e}")
    finally:
        conn.close()


def load_api_config():
    """从数据库加载API配置"""
    _ensure_config_table()
    
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT api_key, hunyuan_api_key, model_strategy, admin_password_hash 
            FROM system_config WHERE id = 1
        ''')
        row = cursor.fetchone()

        if row:
            return {
                "api_key": row['api_key'] or "",
                "hunyuan_api_key": row['hunyuan_api_key'] or "",
                "model_strategy": row['model_strategy'] or "dynamic",
                "admin_password_hash": row['admin_password_hash']
            }
        else:
            # 创建默认配置
            default_password = "admin123"
            password_hash = _hash_password(default_password)
            cursor.execute('''
                INSERT INTO system_config (id, api_key, hunyuan_api_key, model_strategy, admin_password_hash)
                VALUES (1, '', '', 'dynamic', ?)
            ''', (password_hash,))
            conn.commit()
            return {
                "api_key": "",
                "hunyuan_api_key": "",
                "model_strategy": "dynamic",
                "admin_password_hash": password_hash
            }
    except Exception as e:
        print(f"[API Config] 从数据库加载配置失败: {e}")
        # 返回默认配置
        return {
            "api_key": "",
            "hunyuan_api_key": "",
            "model_strategy": "dynamic",
            "admin_password_hash": _hash_password("admin123")
        }
    finally:
        conn.close()


def save_api_config(api_key: str = None, hunyuan_api_key: str = None, 
                    model_strategy: str = None, admin_password: str = None):
    """保存API配置到数据库

    Args:
        api_key: DeepSeek API密钥（可选）
        hunyuan_api_key: Hunyuan API密钥（可选）
        model_strategy: 模型选择策略（可选）
        admin_password: 管理员密码明文（可选，会哈希存储）
    """
    _ensure_config_table()
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 先查询现有配置
        cursor.execute('''
            SELECT api_key, hunyuan_api_key, model_strategy, admin_password_hash 
            FROM system_config WHERE id = 1
        ''')
        row = cursor.fetchone()

        if row:
            current_api_key = row['api_key'] or ""
            current_hunyuan_key = row['hunyuan_api_key'] or ""
            current_strategy = row['model_strategy'] or "dynamic"
            current_hash = row['admin_password_hash']
        else:
            current_api_key = ""
            current_hunyuan_key = ""
            current_strategy = "dynamic"
            current_hash = _hash_password("admin123")

        # 更新值
        new_api_key = api_key if api_key is not None else current_api_key
        new_hunyuan_key = hunyuan_api_key if hunyuan_api_key is not None else current_hunyuan_key
        new_strategy = model_strategy if model_strategy is not None else current_strategy
        new_hash = _hash_password(admin_password) if admin_password is not None else current_hash

        if row:
            cursor.execute('''
                UPDATE system_config 
                SET api_key = ?, hunyuan_api_key = ?, model_strategy = ?, admin_password_hash = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
            ''', (new_api_key, new_hunyuan_key, new_strategy, new_hash))
        else:
            cursor.execute('''
                INSERT INTO system_config (id, api_key, hunyuan_api_key, model_strategy, admin_password_hash)
                VALUES (1, ?, ?, ?, ?)
            ''', (new_api_key, new_hunyuan_key, new_strategy, new_hash))

        conn.commit()
        return True
    except Exception as e:
        print(f"[API Config] 保存配置失败: {e}")
        return False
    finally:
        conn.close()


def get_deepseek_balance(api_key: str) -> tuple[bool, float, str]:
    """查询 DeepSeek 余额

    Returns:
        (success, balance, message)
    """
    if not api_key:
        return False, 0.0, "API Key 未配置"
    
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
            data = response.json()
            if data.get('is_available') and data.get('balance_infos'):
                # 计算总余额（CNY）
                total_balance = 0.0
                for info in data['balance_infos']:
                    if info.get('currency') == 'CNY':
                        total_balance = float(info.get('total_balance', 0))
                        break
                return True, total_balance, ""
            else:
                return False, 0.0, "账户不可用"
        else:
            return False, 0.0, f"查询失败 (HTTP {response.status_code})"
            
    except Exception as e:
        return False, 0.0, f"查询失败: {str(e)}"


def should_use_deepseek() -> tuple[bool, str]:
    """判断是否可以使用 DeepSeek

    根据模型策略和余额决定是否使用 DeepSeek

    Returns:
        (use_deepseek, reason)
        use_deepseek: True 使用 DeepSeek, False 使用 Hunyuan
        reason: 原因说明
    """
    config = load_api_config()
    strategy = config.get('model_strategy', 'dynamic')
    
    # 强制使用 DeepSeek
    if strategy == MODEL_STRATEGY_DEEPSEEK:
        if not config.get('api_key'):
            return False, "DeepSeek API Key 未配置，已切换到 Hunyuan"
        return True, "强制使用 DeepSeek"
    
    # 强制使用 Hunyuan
    if strategy == MODEL_STRATEGY_HUNYUAN:
        if not config.get('hunyuan_api_key'):
            return False, "Hunyuan API Key 未配置"
        return False, "强制使用 Hunyuan"
    
    # 动态策略
    if strategy == MODEL_STRATEGY_DYNAMIC:
        # 检查 DeepSeek 配置
        if not config.get('api_key'):
            if config.get('hunyuan_api_key'):
                return False, "DeepSeek API Key 未配置，自动切换到 Hunyuan"
            return False, "未配置任何 API Key"
        
        # 查询余额
        success, balance, message = get_deepseek_balance(config['api_key'])
        if not success:
            if config.get('hunyuan_api_key'):
                return False, f"DeepSeek 余额查询失败: {message}，自动切换到 Hunyuan"
            return False, f"DeepSeek 余额查询失败: {message}"
        
        # 检查余额是否充足
        if balance < BALANCE_THRESHOLD:
            if config.get('hunyuan_api_key'):
                return False, f"DeepSeek 余额不足 ({balance}元 < {BALANCE_THRESHOLD}元)，自动切换到 Hunyuan"
            return True, f"DeepSeek 余额不足 ({balance}元)，但 Hunyuan 未配置，继续使用 DeepSeek"
        
        return True, f"DeepSeek 余额充足 ({balance}元)"
    
    return False, "未知的模型策略"


def _mask_api_key(api_key: str) -> str:
    """对API密钥进行掩码处理

    例如: sk-abc1234567890xyz → sk-abc1...xyz9
    """
    if not api_key:
        return "未配置"
    if len(api_key) < 12:
        return api_key[:3] + "..."
    return api_key[:6] + "..." + api_key[-4:]


@api_key_bp.route('/getApiKey', methods=['GET'])
def get_api_key():
    """获取API密钥配置（需要密码验证）- 返回掩码版本，防止泄露"""
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

    # 查询 DeepSeek 余额
    ds_balance = 0.0
    ds_available = False
    if config.get('api_key'):
        success, balance, _ = get_deepseek_balance(config['api_key'])
        if success:
            ds_balance = balance
            ds_available = True

    return jsonify({
        "code": 0,
        "data": {
            "api_key": _mask_api_key(config.get('api_key', '')),
            "hunyuan_api_key": _mask_api_key(config.get('hunyuan_api_key', '')),
            "model_strategy": config.get('model_strategy', 'dynamic'),
            "deepseek_balance": ds_balance,
            "deepseek_available": ds_available
        }
    }), 200


@api_key_bp.route('/updateApiKey', methods=['POST'])
def update_api_key():
    """更新 DeepSeek API 密钥"""
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
            "msg": "缺少新的 API 密钥"
        }), 400

    config = load_api_config()

    # 验证原密码
    if not _verify_password(old_password, config.get('admin_password_hash', '')):
        return jsonify({
            "code": 403,
            "msg": "原密码错误"
        }), 403

    # 验证新 API 密钥有效性
    is_valid, error_msg = _validate_deepseek_key(new_api_key)
    if not is_valid:
        return jsonify({
            "code": 400,
            "msg": f"API 密钥验证失败: {error_msg}"
        }), 400

    # 更新配置
    if save_api_config(api_key=new_api_key):
        return jsonify({
            "code": 0,
            "msg": "API 密钥更新成功",
            "data": {
                "api_key_updated": True
            }
        }), 200
    else:
        return jsonify({
            "code": 500,
            "msg": "保存配置失败"
        }), 500


@api_key_bp.route('/updateHunyuanApiKey', methods=['POST'])
def update_hunyuan_api_key():
    """更新 Hunyuan API 密钥"""
    data = request.get_json()
    if not data:
        return jsonify({
            "code": 400,
            "msg": "请求体不能为空"
        }), 400

    old_password = data.get('old_password')
    new_hunyuan_api_key = data.get('new_hunyuan_api_key')

    if not old_password:
        return jsonify({
            "code": 400,
            "msg": "缺少原密码"
        }), 400

    if not new_hunyuan_api_key:
        return jsonify({
            "code": 400,
            "msg": "缺少新的 Hunyuan API 密钥"
        }), 400

    config = load_api_config()

    # 验证原密码
    if not _verify_password(old_password, config.get('admin_password_hash', '')):
        return jsonify({
            "code": 403,
            "msg": "原密码错误"
        }), 403

    # 验证 Hunyuan API 密钥有效性
    is_valid, error_msg = _validate_hunyuan_key(new_hunyuan_api_key)
    if not is_valid:
        return jsonify({
            "code": 400,
            "msg": f"Hunyuan API 密钥验证失败: {error_msg}"
        }), 400

    # 更新配置
    if save_api_config(hunyuan_api_key=new_hunyuan_api_key):
        return jsonify({
            "code": 0,
            "msg": "Hunyuan API 密钥更新成功",
            "data": {
                "hunyuan_api_key_updated": True
            }
        }), 200
    else:
        return jsonify({
            "code": 500,
            "msg": "保存配置失败"
        }), 500


@api_key_bp.route('/updateModelStrategy', methods=['POST'])
def update_model_strategy():
    """更新模型选择策略"""
    data = request.get_json()
    if not data:
        return jsonify({
            "code": 400,
            "msg": "请求体不能为空"
        }), 400

    old_password = data.get('old_password')
    strategy = data.get('strategy')

    if not old_password:
        return jsonify({
            "code": 400,
            "msg": "缺少原密码"
        }), 400

    if not strategy:
        return jsonify({
            "code": 400,
            "msg": "缺少策略参数"
        }), 400

    if strategy not in [MODEL_STRATEGY_DEEPSEEK, MODEL_STRATEGY_HUNYUAN, MODEL_STRATEGY_DYNAMIC]:
        return jsonify({
            "code": 400,
            "msg": f"无效的策略，可选值: {MODEL_STRATEGY_DEEPSEEK}, {MODEL_STRATEGY_HUNYUAN}, {MODEL_STRATEGY_DYNAMIC}"
        }), 400

    config = load_api_config()

    # 验证原密码
    if not _verify_password(old_password, config.get('admin_password_hash', '')):
        return jsonify({
            "code": 403,
            "msg": "原密码错误"
        }), 403

    # 更新配置
    if save_api_config(model_strategy=strategy):
        return jsonify({
            "code": 0,
            "msg": "模型策略更新成功",
            "data": {
                "strategy": strategy
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
