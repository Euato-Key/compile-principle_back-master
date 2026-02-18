"""
API密钥管理蓝图
"""
from flask import Blueprint, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import json
import os

# API密钥文件路径
API_KEY_FILE = os.path.join(os.path.dirname(__file__), '..', 'deepseek-api-key.json')

api_key_bp = Blueprint('api_key', __name__, url_prefix='/api')


def load_api_config():
    """加载API配置，如果不存在则创建默认配置"""
    default_config = {"api_key": "", "admin_password": "admin123"}
    try:
        with open(API_KEY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"API配置文件不存在，创建默认配置: {API_KEY_FILE}")
        save_api_config(default_config)
        return default_config
    except Exception as e:
        print(f"加载API配置失败: {e}")
        return default_config


def save_api_config(config):
    """保存API配置"""
    try:
        with open(API_KEY_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"保存API配置失败: {e}")
        return False


@api_key_bp.route('/getApiKey', methods=['GET'])
def get_api_key():
    """获取API密钥（需要密码验证）"""
    password = request.headers.get('X-Admin-Password')
    if not password:
        return jsonify({
            "code": 401,
            "msg": "缺少管理员密码"
        }), 401

    config = load_api_config()
    if password != config.get('admin_password'):
        return jsonify({
            "code": 403,
            "msg": "密码错误"
        }), 403

    return jsonify({
        "code": 0,
        "data": {
            "api_key": config.get('api_key', '')
        }
    }), 200


@api_key_bp.route('/updateApiKey', methods=['POST'])
def update_api_key():
    """更新API密钥（需要密码验证）"""
    data = request.get_json()
    if not data:
        return jsonify({
            "code": 400,
            "msg": "请求体不能为空"
        }), 400

    old_password = data.get('old_password')
    new_api_key = data.get('new_api_key')
    new_password = data.get('new_password')  # 可选：同时修改密码

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
    if old_password != config.get('admin_password'):
        return jsonify({
            "code": 403,
            "msg": "原密码错误"
        }), 403

    # 更新API密钥
    config['api_key'] = new_api_key

    # 如果提供了新密码，同时更新密码
    if new_password:
        config['admin_password'] = new_password

    if save_api_config(config):
        return jsonify({
            "code": 0,
            "msg": "API密钥更新成功",
            "data": {
                "api_key_updated": True,
                "password_updated": bool(new_password)
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
    if old_password != config.get('admin_password'):
        return jsonify({
            "code": 403,
            "msg": "原密码错误"
        }), 403

    # 更新密码
    config['admin_password'] = new_password

    if save_api_config(config):
        return jsonify({
            "code": 0,
            "msg": "密码修改成功"
        }), 200
    else:
        return jsonify({
            "code": 500,
            "msg": "保存配置失败"
        }), 500
