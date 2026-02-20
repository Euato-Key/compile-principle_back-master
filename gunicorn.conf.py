"""
Gunicorn 配置文件
支持 40+ 并发用户
"""

import multiprocessing
import os

# 服务器绑定
bind = "0.0.0.0:5000"

# Worker 配置
# 公式：2 * CPU核心数 + 1，但考虑 AI 请求是 I/O 密集型，可以适当增加
# 对于 40 并发，建议 8-12 个 worker
workers = 8

# 使用 gevent worker 支持异步处理
worker_class = "gevent"

# 每个 worker 的并发连接数（gevent 模式下）
worker_connections = 1000

# 超时时间（AI 请求可能需要较长时间）
timeout = 120

# 保持连接时间
keepalive = 5

# 请求队列长度（超过会返回 503）
backlog = 2048

# 最大请求数（防止内存泄漏，超过自动重启 worker）
max_requests = 1000
max_requests_jitter = 50

# 优雅重启超时
graceful_timeout = 30

# 日志配置
accesslog = "-"  # 输出到 stdout
errorlog = "-"   # 输出到 stderr
loglevel = "info"

# 进程名称
proc_name = "compiler_edu_backend"

# 是否以守护进程运行
daemon = False

# PID 文件
pidfile = "gunicorn.pid"

# 预加载应用（节省内存）
# 注意：设置为 True 可能导致 gevent + requests 出现递归深度错误
preload_app = False

# 工作模式配置
def post_fork(server, worker):
    """Worker 启动后执行"""
    server.log.info(f"Worker spawned (pid: {worker.pid})")

def on_starting(server):
    """服务器启动时执行"""
    server.log.info("Gunicorn starting...")

def on_exit(server):
    """服务器退出时执行"""
    server.log.info("Gunicorn exiting...")
