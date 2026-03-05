"""
AI 代理蓝图
支持 DeepSeek 和 Hunyuan 双模型，自动根据余额和策略切换
使用 OpenAI SDK 调用 API
"""
from flask import Blueprint, request, jsonify, Response, stream_with_context
import json
import time
from datetime import datetime
from database import get_db_connection
from blueprints.api_key import load_api_config, should_use_deepseek
from openai import OpenAI

ai_proxy_bp = Blueprint('ai_proxy', __name__, url_prefix='/api')

# API 配置
DEEPSEEK_BASE_URL = 'https://api.deepseek.com'
HUNYUAN_BASE_URL = 'https://api.hunyuan.cloud.tencent.com/v1'

# 模型映射
DEEPSEEK_MODELS = ['deepseek-chat', 'deepseek-reasoner']
HUNYUAN_MODELS = ['hunyuan-lite', 'hunyuan-standard', 'hunyuan-standard-256K', 'hunyuan-pro']


def get_deepseek_client():
    """获取 DeepSeek 客户端"""
    config = load_api_config()
    api_key = config.get('api_key', '')
    if not api_key:
        return None
    return OpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL)


def get_hunyuan_client():
    """获取 Hunyuan 客户端"""
    config = load_api_config()
    api_key = config.get('hunyuan_api_key', '')
    if not api_key:
        return None
    return OpenAI(api_key=api_key, base_url=HUNYUAN_BASE_URL)


def get_available_client():
    """获取可用的客户端
    
    Returns:
        (client, provider, reason)
        client: OpenAI 客户端或 None
        provider: 'deepseek' 或 'hunyuan'
        reason: 选择原因
    """
    use_deepseek, reason = should_use_deepseek()
    
    if use_deepseek:
        client = get_deepseek_client()
        if client:
            return client, 'deepseek', reason
        # DeepSeek 客户端获取失败，尝试 Hunyuan
        client = get_hunyuan_client()
        if client:
            return client, 'hunyuan', f"{reason}，但 DeepSeek 客户端初始化失败，已切换到 Hunyuan"
        return None, None, "DeepSeek 和 Hunyuan 都未配置"
    else:
        client = get_hunyuan_client()
        if client:
            return client, 'hunyuan', reason
        # Hunyuan 未配置，尝试 DeepSeek
        client = get_deepseek_client()
        if client:
            return client, 'deepseek', f"{reason}，但 Hunyuan 未配置，继续使用 DeepSeek"
        return None, None, "Hunyuan 和 DeepSeek 都未配置"


def convert_model_name(model: str, provider: str) -> str:
    """转换模型名称
    
    如果请求的模型不属于当前 provider，使用默认模型
    """
    if provider == 'deepseek':
        if model in DEEPSEEK_MODELS:
            return model
        return 'deepseek-chat'  # 默认 DeepSeek 模型
    else:  # hunyuan
        if model in HUNYUAN_MODELS:
            return model
        return 'hunyuan-lite'  # 默认 Hunyuan 模型（免费）


def record_token_usage(module_type: str, model: str, input_tokens: int, output_tokens: int, 
                       total_tokens: int, is_stream: bool = False, provider: str = ''):
    """记录 Token 使用量到数据库"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO token_usage 
            (module, model, input_tokens, output_tokens, total_tokens, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (f"{module_type}:{provider}" if provider else module_type, 
              model, input_tokens, output_tokens, total_tokens, datetime.now()))
        conn.commit()
    except Exception as e:
        print(f"[AI Proxy] 记录 Token 用量失败: {e}")
    finally:
        conn.close()


@ai_proxy_bp.route('/ai/chat', methods=['POST'])
def ai_chat():
    """
    代理 AI 聊天请求（非流式）
    自动根据策略选择 DeepSeek 或 GLM
    """
    client, provider, reason = get_available_client()
    if not client:
        return jsonify({
            "code": 500,
            "msg": "没有可用的 AI 服务"
        }), 500
    
    # 获取前端请求体
    request_data = request.get_json() or {}
    module = request_data.pop('module', 'unknown')
    requested_model = request_data.get("model", "deepseek-chat")
    
    # 转换模型名称
    model = convert_model_name(requested_model, provider)
    
    # 构建请求参数
    kwargs = {
        "model": model,
        "messages": request_data.get("messages", []),
        "temperature": request_data.get("temperature", 0.3),
        "max_tokens": request_data.get("max_tokens", 4096),
        "stream": False
    }
    
    # 可选参数
    if "response_format" in request_data:
        kwargs["response_format"] = request_data["response_format"]
    if "top_p" in request_data:
        kwargs["top_p"] = request_data["top_p"]
    if "frequency_penalty" in request_data:
        kwargs["frequency_penalty"] = request_data["frequency_penalty"]
    if "presence_penalty" in request_data:
        kwargs["presence_penalty"] = request_data["presence_penalty"]
    if "thinking" in request_data:
        kwargs["extra_body"] = {"thinking": request_data["thinking"]}
    
    try:
        # 发送请求
        start_time = time.time()
        completion = client.chat.completions.create(**kwargs)
        
        # 转换为字典格式
        data = completion.model_dump()
        
        # 添加 provider 信息
        data['_provider'] = provider
        data['_switch_reason'] = reason
        
        # 记录 Token 用量
        usage = data.get('usage', {})
        if usage:
            record_token_usage(
                module_type=module,
                model=model,
                input_tokens=usage.get('prompt_tokens', 0),
                output_tokens=usage.get('completion_tokens', 0),
                total_tokens=usage.get('total_tokens', 0),
                is_stream=False,
                provider=provider
            )
        
        # 返回给前端
        return jsonify({
            "code": 0,
            "data": data
        }), 200
        
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
    自动根据策略选择 DeepSeek 或 GLM
    """
    client, provider, reason = get_available_client()
    if not client:
        return jsonify({
            "code": 500,
            "msg": "没有可用的 AI 服务"
        }), 500
    
    # 获取前端请求体
    request_data = request.get_json() or {}
    module = request_data.pop('module', 'unknown')
    requested_model = request_data.get("model", "deepseek-chat")
    
    # 转换模型名称
    model = convert_model_name(requested_model, provider)
    
    # 构建请求参数
    kwargs = {
        "model": model,
        "messages": request_data.get("messages", []),
        "temperature": request_data.get("temperature", 0.3),
        "max_tokens": request_data.get("max_tokens", 4096),
        "stream": True
    }
    
    # 可选参数
    if "top_p" in request_data:
        kwargs["top_p"] = request_data["top_p"]
    if "frequency_penalty" in request_data:
        kwargs["frequency_penalty"] = request_data["frequency_penalty"]
    if "presence_penalty" in request_data:
        kwargs["presence_penalty"] = request_data["presence_penalty"]
    if "thinking" in request_data:
        kwargs["extra_body"] = {"thinking": request_data["thinking"]}
    
    try:
        # 用于统计的变量
        total_input_tokens = 0
        total_output_tokens = 0
        
        def generate():
            nonlocal total_input_tokens, total_output_tokens
            
            # 发送流式请求
            stream = client.chat.completions.create(**kwargs)
            
            # 发送 provider 信息（作为第一个 chunk）
            provider_info = {
                "_provider": provider,
                "_switch_reason": reason,
                "_model": model,
                "choices": [{"delta": {"content": ""}}]
            }
            yield f"data: {json.dumps(provider_info, ensure_ascii=False)}\n\n".encode('utf-8')
            
            for chunk in stream:
                # 转换为字典
                chunk_dict = chunk.model_dump()
                
                # 尝试获取 usage 信息
                usage = chunk_dict.get('usage')
                if usage:
                    total_input_tokens = usage.get('prompt_tokens', 0)
                    total_output_tokens = usage.get('completion_tokens', 0)
                
                # 格式化为 SSE 格式
                data_str = json.dumps(chunk_dict, ensure_ascii=False)
                yield f"data: {data_str}\n\n".encode('utf-8')
            
            # 发送结束标记
            yield b"data: [DONE]\n\n"
            
            # 流结束后记录 Token 用量
            if total_input_tokens > 0 or total_output_tokens > 0:
                record_token_usage(
                    module_type=module,
                    model=model,
                    input_tokens=total_input_tokens,
                    output_tokens=total_output_tokens,
                    total_tokens=total_input_tokens + total_output_tokens,
                    is_stream=True,
                    provider=provider
                )
        
        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no'
            }
        )
        
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
                "description": "通用对话模型 (DeepSeek)"
            },
            {
                "id": "deepseek-reasoner",
                "name": "DeepSeek Reasoner",
                "description": "推理模型，支持 thinking 模式 (DeepSeek)"
            },
            {
                "id": "hunyuan-lite",
                "name": "Hunyuan Lite",
                "description": "轻量快速模型，免费 (Hunyuan)"
            },
            {
                "id": "hunyuan-standard",
                "name": "Hunyuan Standard",
                "description": "标准对话模型 (Hunyuan)"
            },
            {
                "id": "hunyuan-standard-256K",
                "name": "Hunyuan Standard 256K",
                "description": "长上下文模型 (Hunyuan)"
            },
            {
                "id": "hunyuan-pro",
                "name": "Hunyuan Pro",
                "description": "专业版模型 (Hunyuan)"
            }
        ]
    }), 200


@ai_proxy_bp.route('/ai/token-usage', methods=['GET'])
def get_token_usage():
    """
    获取 Token 使用统计
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
        
        # 查询按日期统计
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
    代理查询 DeepSeek 余额
    """
    import requests
    
    config = load_api_config()
    api_key = config.get('api_key', '')
    
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


@ai_proxy_bp.route('/ai/provider', methods=['GET'])
def get_current_provider():
    """获取当前使用的 AI 提供商信息"""
    client, provider, reason = get_available_client()
    
    if not client:
        return jsonify({
            "code": 500,
            "msg": "没有可用的 AI 服务"
        }), 500
    
    return jsonify({
        "code": 0,
        "data": {
            "provider": provider,
            "reason": reason,
            "available_providers": []
        }
    }), 200
