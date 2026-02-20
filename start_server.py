#!/usr/bin/env python3
"""
服务器启动脚本
支持开发模式和生产模式
"""

import os
import sys
import argparse
import subprocess


def start_dev():
    """启动开发服务器（Flask 内置）"""
    print("=" * 60)
    print("启动开发服务器 (Flask)")
    print("=" * 60)
    print("适用场景：开发调试")
    print("并发能力：1-2 人同时")
    print("=" * 60)
    
    from server import app
    app.run(host='0.0.0.0', port=5000, debug=True)


def start_prod():
    """启动生产服务器（Gunicorn + Gevent）"""
    print("=" * 60)
    print("启动生产服务器 (Gunicorn + Gevent)")
    print("=" * 60)
    print("适用场景：生产环境")
    print("并发能力：40+ 人同时")
    print("=" * 60)
    
    # 检查 gunicorn 是否安装
    try:
        import gunicorn
        import gevent
        print(f"✓ Gunicorn {gunicorn.__version__} 已安装")
        print(f"✓ Gevent {gevent.__version__} 已安装")
    except ImportError as e:
        print(f"✗ 缺少依赖: {e}")
        print("请先安装依赖: pip install -r requirements.txt")
        sys.exit(1)
    
    print("\n启动参数:")
    print("  Workers: 8")
    print("  Worker Class: gevent")
    print("  Worker Connections: 1000")
    print("  Timeout: 120s")
    print("=" * 60)
    
    # 使用配置文件启动
    cmd = [
        sys.executable, "-m", "gunicorn",
        "-c", "gunicorn.conf.py",
        "server:app"
    ]
    
    subprocess.run(cmd)


def start_prod_simple():
    """简化版生产服务器（纯 Gunicorn，无 gevent）"""
    print("=" * 60)
    print("启动生产服务器 (Gunicorn Sync)")
    print("=" * 60)
    print("适用场景：生产环境（无 gevent 依赖）")
    print("并发能力：8-16 人同时")
    print("=" * 60)
    
    # 使用同步 worker
    cmd = [
        sys.executable, "-m", "gunicorn",
        "-w", "8",
        "-b", "0.0.0.0:5000",
        "--timeout", "120",
        "--access-logfile", "-",
        "--error-logfile", "-",
        "--log-level", "info",
        "server:app"
    ]
    
    subprocess.run(cmd)


def main():
    parser = argparse.ArgumentParser(description='编译原理教学平台后端服务器')
    parser.add_argument(
        'mode',
        choices=['dev', 'prod', 'prod-simple'],
        default='dev',
        nargs='?',
        help='运行模式: dev=开发, prod=生产(推荐), prod-simple=生产(简化)'
    )
    
    args = parser.parse_args()
    
    if args.mode == 'dev':
        start_dev()
    elif args.mode == 'prod':
        start_prod()
    elif args.mode == 'prod-simple':
        start_prod_simple()


if __name__ == '__main__':
    main()
