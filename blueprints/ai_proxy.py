"""
DeepSeek AI 代理蓝图
代理前端请求到 DeepSeek API，隐藏 API Key 并统计 Token 用量
"""
from flask import Blueprint, request, jsonify, Response, stream_with_context
import requests
import json
import time
from datetime import datetime
from database import get_db_connection
from blueprints.api_key import load_api_config

ai_proxy_bp = Blueprint('ai_proxy', __name__, url_prefix='/api')

# DeepSeek API 配置
DEEPSEEK_BASE_URL = 'https://api.deepseek.com'
DEEPSEEK_CHAT_URL = f'{DEEPSEEK_BASE_URL}/chat/completions'


def get_api_key():
    """从数据库获取 API Key"""
    config = load_api_config()
    return config.get('api_key', '')


def record_token_usage(module_type: str, model: str, input_tokens: int, output_tokens: int, 
                       total_tokens: int, is_stream: bool = False):
    """记录 Token 使用量到数据库"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO token_usage 
            (module, model, input_tokens, output_tokens, total_tokens, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (module_type, model, input_tokens, output_tokens, total_tokens, datetime.now()))
        conn.commit()
    except Exception as e:
        print(f"[AI Proxy] 记录 Token 用量失败: {e}")
    finally:
        conn.close()


@ai_proxy_bp.route('/ai/chat', methods=['POST'])
def ai_chat():
    """
    代理 AI 聊天请求（非流式）
    适用于 AI 报告生成等场景
    
    请求体示例:
    {
        "messages": [...],
        "model": "deepseek-chat",
        "temperature": 0.3,
        "max_tokens": 6000,
        "response_format": {"type": "json_object"},
        "module": "fa"  // 可选，用于统计
    }
    """
    api_key = get_api_key()
    if not api_key:
        return jsonify({
            "code": 500,
            "msg": "API Key 未配置"
        }), 500
    
    # 获取前端请求体
    request_data = request.get_json() or {}
    module = request_data.pop('module', 'unknown')  # 取出 module 用于统计
    
    # 构建请求体（过滤掉自定义字段）
    payload = {
        "model": request_data.get("model", "deepseek-chat"),
        "messages": request_data.get("messages", []),
        "temperature": request_data.get("temperature", 0.3),
        "max_tokens": request_data.get("max_tokens", 4096),
        "stream": False
    }
    
    # 可选参数
    if "response_format" in request_data:
        payload["response_format"] = request_data["response_format"]
    if "top_p" in request_data:
        payload["top_p"] = request_data["top_p"]
    if "frequency_penalty" in request_data:
        payload["frequency_penalty"] = request_data["frequency_penalty"]
    if "presence_penalty" in request_data:
        payload["presence_penalty"] = request_data["presence_penalty"]
    if "thinking" in request_data:
        payload["thinking"] = request_data["thinking"]
    
    try:
        # 发送请求到 DeepSeek
        start_time = time.time()
        response = requests.post(
            DEEPSEEK_CHAT_URL,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}'
            },
            json=payload,
            timeout=120  # 120秒超时
        )
        
        if not response.ok:
            error_data = response.json() if response.text else {}
            return jsonify({
                "code": response.status_code,
                "msg": error_data.get('error', {}).get('message', f'DeepSeek API 错误: {response.status_code}')
            }), response.status_code
        
        # 解析响应
        data = response.json()
        
        # 记录 Token 用量
        usage = data.get('usage', {})
        if usage:
            record_token_usage(
                module_type=module,
                model=payload["model"],
                input_tokens=usage.get('prompt_tokens', 0),
                output_tokens=usage.get('completion_tokens', 0),
                total_tokens=usage.get('total_tokens', 0),
                is_stream=False
            )
        
        # 返回给前端
        return jsonify({
            "code": 0,
            "data": data
        }), 200
        
    except requests.exceptions.Timeout:
        return jsonify({
            "code": 504,
            "msg": "请求超时，请稍后重试"
        }), 504
    except Exception as e:
        print(f"[AI Proxy] 请求失败: {e}")
        return jsonify({
            "code": 500,
            "msg": f"请求失败: {str(e)}"
        }), 500


@ai_proxy_bp.route('/ai/chat/stream', methods=['POST'])
def ai_chat_stream():
    """
    代理 AI 聊天请求（流式）
    适用于 AI 助手实时对话
    
    请求体示例:
    {
        "messages": [...],
        "model": "deepseek-chat",
        "temperature": 0.3,
        "module": "fa"  // 可选，用于统计
    }
    """
    api_key = get_api_key()
    if not api_key:
        return jsonify({
            "code": 500,
            "msg": "API Key 未配置"
        }), 500
    
    # 获取前端请求体
    request_data = request.get_json() or {}
    module = request_data.pop('module', 'unknown')  # 取出 module 用于统计
    model = request_data.get("model", "deepseek-chat")
    
    # 构建请求体
    payload = {
        "model": model,
        "messages": request_data.get("messages", []),
        "temperature": request_data.get("temperature", 0.3),
        "max_tokens": request_data.get("max_tokens", 4096),
        "stream": True  # 强制流式
    }
    
    # 可选参数
    if "top_p" in request_data:
        payload["top_p"] = request_data["top_p"]
    if "frequency_penalty" in request_data:
        payload["frequency_penalty"] = request_data["frequency_penalty"]
    if "presence_penalty" in request_data:
        payload["presence_penalty"] = request_data["presence_penalty"]
    if "thinking" in request_data:
        payload["thinking"] = request_data["thinking"]
    
    try:
        # 发送流式请求到 DeepSeek
        deepseek_response = requests.post(
            DEEPSEEK_CHAT_URL,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}'
            },
            json=payload,
            stream=True,
            timeout=300  # 流式请求更长超时
        )
        
        if not deepseek_response.ok:
            error_data = deepseek_response.json() if deepseek_response.text else {}
            return jsonify({
                "code": deepseek_response.status_code,
                "msg": error_data.get('error', {}).get('message', f'DeepSeek API 错误: {deepseek_response.status_code}')
            }), deepseek_response.status_code
        
        # 用于统计的变量
        total_input_tokens = 0
        total_output_tokens = 0
        
        def generate():
            nonlocal total_input_tokens, total_output_tokens
            
            for chunk in deepseek_response.iter_content(chunk_size=1024):
                if chunk:
                    # 尝试解析 chunk 获取 usage 信息
                    try:
                        lines = chunk.decode('utf-8').strip().split('\n')
                        for line in lines:
                            if line.startswith('data: '):
                                data_str = line[6:]  # 去掉 "data: "
                                if data_str == '[DONE]':
                                    continue
                                data = json.loads(data_str)
                                usage = data.get('usage')
                                if usage:
                                    total_input_tokens = usage.get('prompt_tokens', 0)
                                    total_output_tokens = usage.get('completion_tokens', 0)
                    except:
                        pass
                    
                    yield chunk
            
            # 流结束后记录 Token 用量
            if total_input_tokens > 0 or total_output_tokens > 0:
                record_token_usage(
                    module_type=module,
                    model=model,
                    input_tokens=total_input_tokens,
                    output_tokens=total_output_tokens,
                    total_tokens=total_input_tokens + total_output_tokens,
                    is_stream=True
                )
        
        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no'
            }
        )
        
    except requests.exceptions.Timeout:
        return jsonify({
            "code": 504,
            "msg": "请求超时，请稍后重试"
        }), 504
    except Exception as e:
        print(f"[AI Proxy] 流式请求失败: {e}")
        return jsonify({
            "code": 500,
            "msg": f"请求失败: {str(e)}"
        }), 500


@ai_proxy_bp.route('/ai/models', methods=['GET'])
def get_available_models():
    """获取可用的模型列表"""
    return jsonify({
        "code": 0,
        "data": [
            {
                "id": "deepseek-chat",
                "name": "DeepSeek Chat",
                "description": "通用对话模型"
            },
            {
                "id": "deepseek-reasoner",
                "name": "DeepSeek Reasoner",
                "description": "推理模型，支持 thinking 模式"
            }
        ]
    }), 200


@ai_proxy_bp.route('/ai/token-usage', methods=['GET'])
def get_token_usage():
    """
    获取 Token 使用统计
    
    查询参数:
    - start_date: 开始日期 (YYYY-MM-DD)
    - end_date: 结束日期 (YYYY-MM-DD)
    - module: 模块筛选 (可选)
    """
    from datetime import datetime, timedelta
    
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    module = request.args.get('module')
    
    # 默认查询最近 30 天
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')
    if not start_date:
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 构建查询条件
        conditions = ["DATE(created_at) BETWEEN ? AND ?"]
        params = [start_date, end_date]
        
        if module:
            conditions.append("module = ?")
            params.append(module)
        
        where_clause = " AND ".join(conditions)
        
        # 查询总体统计
        cursor.execute(f'''
            SELECT 
                COUNT(*) as total_requests,
                SUM(input_tokens) as total_input_tokens,
                SUM(output_tokens) as total_output_tokens,
                SUM(total_tokens) as total_tokens
            FROM token_usage
            WHERE {where_clause}
        ''', params)
        
        summary = cursor.fetchone()
        
        # 查询按模块统计
        cursor.execute(f'''
            SELECT 
                module,
                COUNT(*) as requests,
                SUM(input_tokens) as input_tokens,
                SUM(output_tokens) as output_tokens,
                SUM(total_tokens) as total_tokens
            FROM token_usage
            WHERE {where_clause}
            GROUP BY module
            ORDER BY total_tokens DESC
        ''', params)
        
        module_stats = [dict(row) for row in cursor.fetchall()]
        
        # 查询按日期统计（最近 30 天）
        cursor.execute(f'''
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as requests,
                SUM(total_tokens) as total_tokens
            FROM token_usage
            WHERE {where_clause}
            GROUP BY DATE(created_at)
            ORDER BY date DESC
            LIMIT 30
        ''', params)
        
        daily_stats = [dict(row) for row in cursor.fetchall()]
        
        # 查询按模型统计
        cursor.execute(f'''
            SELECT 
                model,
                COUNT(*) as requests,
                SUM(total_tokens) as total_tokens
            FROM token_usage
            WHERE {where_clause}
            GROUP BY model
            ORDER BY total_tokens DESC
        ''', params)
        
        model_stats = [dict(row) for row in cursor.fetchall()]
        
        return jsonify({
            "code": 0,
            "data": {
                "summary": {
                    "total_requests": summary['total_requests'] or 0,
                    "total_input_tokens": summary['total_input_tokens'] or 0,
                    "total_output_tokens": summary['total_output_tokens'] or 0,
                    "total_tokens": summary['total_tokens'] or 0
                },
                "module_stats": module_stats,
                "daily_stats": daily_stats,
                "model_stats": model_stats,
                "date_range": {
                    "start_date": start_date,
                    "end_date": end_date
                }
            }
        }), 200
        
    except Exception as e:
        print(f"[AI Proxy] 查询 Token 用量失败: {e}")
        return jsonify({
            "code": 500,
            "msg": f"查询失败: {str(e)}"
        }), 500
    finally:
        conn.close()


@ai_proxy_bp.route('/ai/balance', methods=['GET'])
def get_balance_proxy():
    """
    代理查询 DeepSeek 余额（后端发起请求，保护 API Key）
    """
    api_key = get_api_key()
    if not api_key:
        return jsonify({
            "code": 500,
            "msg": "API Key 未配置"
        }), 500
    
    try:
        response = requests.get(
            'https://api.deepseek.com/user/balance',
            headers={
                'Accept': 'application/json',
                'Authorization': f'Bearer {api_key}'
            },
            timeout=30
        )
        
        if not response.ok:
            error_data = response.json() if response.text else {}
            return jsonify({
                "code": response.status_code,
                "msg": error_data.get('error', {}).get('message', f'查询余额失败: {response.status_code}')
            }), response.status_code
        
        data = response.json()
        return jsonify({
            "code": 0,
            "data": data
        }), 200
        
    except requests.exceptions.Timeout:
        return jsonify({
            "code": 504,
            "msg": "查询超时，请稍后重试"
        }), 504
    except Exception as e:
        print(f"[AI Proxy] 查询余额失败: {e}")
        return jsonify({
            "code": 500,
            "msg": f"查询失败: {str(e)}"
        }), 500
