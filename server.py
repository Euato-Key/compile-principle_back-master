from flask_cors import CORS
from flask import Flask, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# 导入蓝图
from blueprints.api_key import api_key_bp
from blueprints.fa import fa_bp
from blueprints.ll1 import ll1_bp
from blueprints.lr0 import lr0_bp
from blueprints.slr1 import slr1_bp

app = Flask(__name__)
CORS(app)

# 注册蓝图
app.register_blueprint(api_key_bp)
app.register_blueprint(fa_bp)
app.register_blueprint(ll1_bp)
app.register_blueprint(lr0_bp)
app.register_blueprint(slr1_bp)

# ================= 反爬核心配置 =================
def get_real_ip():
    """
    安全获取经过代理的真实客户端IP
    优先级：X-Forwarded-For -> X-Real-IP -> 默认remote_address
    """
    print("=========================================================",request.headers.get('X-Real-IP', get_remote_address()))
    forwarded_for = request.headers.get('X-Forwarded-For', '').split(',')
    if forwarded_for and len(forwarded_for) > 0:
        # 取第一个非内网IP（根据实际网络结构调整过滤逻辑）
        for ip in forwarded_for:
            ip = ip.strip()
            if not ip.startswith(('10.', '172.16.', '192.168.')):
                return ip
        return forwarded_for[0].strip()
    return request.headers.get('X-Real-IP', get_remote_address())

# 初始化限流器（生产环境建议使用Redis存储）
limiter = Limiter(
    app=app,
    key_func=get_real_ip,  # 基于真实客户端IP
    default_limits=["2000 per day", "500 per hour"],  # 全局默认限制
    storage_uri="memory://",  # 限流计数器的存储后端， 默认未内存存储， 生产环境建议改为redis://
    strategy="fixed-window-elastic-expiry"  # 限流策略： 弹性窗口策略
)

# ================= 路由保护配置 =================
@app.errorhandler(429)
def ratelimit_handler(e):
    """自定义限流响应"""
    return jsonify({
        "code": 429,
        "msg": "请求过于频繁，请稍后再试"
    }), 429

@app.errorhandler(500)
def server_error(error):
    return '服务异常'


# ================= 接口配置 =================
@app.route('/api/test', methods=['GET'])
@limiter.limit("3/minute")
def test():
    return jsonify({
        "code": 0,
        "msg": "test success!"
    }), 200


if __name__ == '__main__':
    print("!!!!!!!!!!!!startup!!!!!!!!!!!!! !!")
    app.run(host='0.0.0.0',debug=True)
