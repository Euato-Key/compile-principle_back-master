"""
统计相关接口蓝图
提供错误统计的记录、查询和管理功能
"""
from flask import Blueprint, request, jsonify
from services.stats_service import StatsService
from database import MODULES, STEPS, ERROR_TYPES

stats_bp = Blueprint('stats', __name__, url_prefix='/api/stats')


# ==================== 错误记录接口 ====================

@stats_bp.route('/record', methods=['POST'])
def record_error():
    """
    记录单个错误统计
    
    请求体:
    {
        "record_id": "abc123",
        "module": "lr0",
        "step": "step2",
        "error_type": "augmentedFormula",
        "error_count": 3,
        "record_created_at": "2025-02-19T10:00:00Z"
    }
    """
    data = request.get_json()
    
    # 参数校验
    required_fields = ['record_id', 'module', 'step', 'error_type', 'error_count', 'record_created_at']
    for field in required_fields:
        if field not in data:
            return jsonify({
                "code": 400,
                "msg": f"缺少必填字段: {field}"
            }), 400
    
    result = StatsService.record_error(
        record_id=data['record_id'],
        module=data['module'],
        step=data['step'],
        error_type=data['error_type'],
        error_count=data['error_count'],
        record_created_at=data['record_created_at']
    )
    
    if result['success']:
        return jsonify({
            "code": 0,
            "msg": result['msg'],
            "data": result['data']
        }), 200
    else:
        return jsonify({
            "code": 400,
            "msg": result['msg']
        }), 400


@stats_bp.route('/record/batch', methods=['POST'])
def batch_record_errors():
    """
    批量记录错误统计
    
    请求体:
    {
        "errors": [
            {
                "record_id": "abc123",
                "module": "lr0",
                "step": "step2",
                "error_type": "augmentedFormula",
                "error_count": 3,
                "record_created_at": "2025-02-19T10:00:00Z"
            },
            ...
        ]
    }
    """
    data = request.get_json()
    
    if 'errors' not in data or not isinstance(data['errors'], list):
        return jsonify({
            "code": 400,
            "msg": "请求体必须包含errors数组"
        }), 400
    
    result = StatsService.batch_record_errors(data['errors'])
    
    if result['success']:
        return jsonify({
            "code": 0,
            "msg": result['msg'],
            "data": result['data']
        }), 200
    else:
        return jsonify({
            "code": 400,
            "msg": result['msg']
        }), 400


# ==================== 统计查询接口 ====================

@stats_bp.route('/summary', methods=['GET'])
def get_summary():
    """
    获取错误统计摘要
    
    查询参数:
    - module: 模块名称（可选）
    - step: 步骤名称（可选）
    - start_date: 开始日期 YYYY-MM-DD（可选）
    - end_date: 结束日期 YYYY-MM-DD（可选）
    """
    module = request.args.get('module')
    step = request.args.get('step')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # 验证模块
    if module and module not in MODULES:
        return jsonify({
            "code": 400,
            "msg": f"无效的模块: {module}"
        }), 400
    
    result = StatsService.get_summary_by_module_step(
        module=module,
        step=step,
        start_date=start_date,
        end_date=end_date
    )
    
    return jsonify({
        "code": 0,
        "msg": result['msg'],
        "data": result['data']
    }), 200


@stats_bp.route('/distribution', methods=['GET'])
def get_distribution():
    """
    获取错误类型分布
    
    查询参数:
    - module: 模块名称（必填）
    - step: 步骤名称（可选）
    - start_date: 开始日期 YYYY-MM-DD（可选）
    - end_date: 结束日期 YYYY-MM-DD（可选）
    """
    module = request.args.get('module')
    step = request.args.get('step')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # 验证模块
    if not module:
        return jsonify({
            "code": 400,
            "msg": "module参数必填"
        }), 400
    
    if module not in MODULES:
        return jsonify({
            "code": 400,
            "msg": f"无效的模块: {module}"
        }), 400
    
    result = StatsService.get_error_type_distribution(
        module=module,
        step=step,
        start_date=start_date,
        end_date=end_date
    )
    
    return jsonify({
        "code": 0,
        "msg": result['msg'],
        "data": result['data']
    }), 200


@stats_bp.route('/trend', methods=['GET'])
def get_trend():
    """
    获取错误趋势（按天统计）
    
    查询参数:
    - module: 模块名称（必填）
    - step: 步骤名称（可选）
    - days: 查询天数，默认30天（可选）
    """
    module = request.args.get('module')
    step = request.args.get('step')
    days = request.args.get('days', default=30, type=int)
    
    # 验证模块
    if not module:
        return jsonify({
            "code": 400,
            "msg": "module参数必填"
        }), 400
    
    if module not in MODULES:
        return jsonify({
            "code": 400,
            "msg": f"无效的模块: {module}"
        }), 400
    
    result = StatsService.get_trend(
        module=module,
        step=step,
        days=days
    )
    
    return jsonify({
        "code": 0,
        "msg": result['msg'],
        "data": result['data']
    }), 200


@stats_bp.route('/overall', methods=['GET'])
def get_overall():
    """获取整体统计信息
    
    查询参数:
    - start_date: 开始日期 YYYY-MM-DD（可选）
    - end_date: 结束日期 YYYY-MM-DD（可选）
    """
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    result = StatsService.get_overall_stats(
        start_date=start_date,
        end_date=end_date
    )
    
    return jsonify({
        "code": 0,
        "msg": result['msg'],
        "data": result['data']
    }), 200


# ==================== 数据管理接口 ====================

@stats_bp.route('/clear', methods=['POST'])
def clear_data():
    """清空所有统计数据"""
    result = StatsService.clear_all_data()
    
    if result['success']:
        return jsonify({
            "code": 0,
            "msg": result['msg']
        }), 200
    else:
        return jsonify({
            "code": 500,
            "msg": result['msg']
        }), 500


@stats_bp.route('/delete/<module>', methods=['POST'])
def delete_module_data(module):
    """删除指定模块的数据"""
    result = StatsService.delete_module_data(module)
    
    if result['success']:
        return jsonify({
            "code": 0,
            "msg": result['msg']
        }), 200
    else:
        return jsonify({
            "code": 400,
            "msg": result['msg']
        }), 400


@stats_bp.route('/delete/by-date', methods=['POST'])
def delete_by_date_range():
    """删除指定日期范围的数据
    
    请求体:
    {
        "start_date": "2025-01-01",
        "end_date": "2025-02-20",
        "module": "lr0"  // 可选，不传则删除所有模块
    }
    """
    data = request.get_json()
    
    if 'start_date' not in data or 'end_date' not in data:
        return jsonify({
            "code": 400,
            "msg": "缺少必填字段: start_date, end_date"
        }), 400
    
    result = StatsService.delete_by_date_range(
        start_date=data['start_date'],
        end_date=data['end_date'],
        module=data.get('module')
    )
    
    if result['success']:
        return jsonify({
            "code": 0,
            "msg": result['msg']
        }), 200
    else:
        return jsonify({
            "code": 400,
            "msg": result['msg']
        }), 400


@stats_bp.route('/export', methods=['GET'])
def export_data():
    """导出数据为 SQL 格式
    
    查询参数:
    - start_date: 开始日期 YYYY-MM-DD（可选）
    - end_date: 结束日期 YYYY-MM-DD（可选）
    - module: 模块名称（可选）
    """
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    module = request.args.get('module')
    
    # 验证模块
    if module and module not in MODULES:
        return jsonify({
            "code": 400,
            "msg": f"无效的模块: {module}"
        }), 400
    
    result = StatsService.export_data(
        start_date=start_date,
        end_date=end_date,
        module=module
    )
    
    if result['success']:
        return jsonify({
            "code": 0,
            "msg": result['msg'],
            "data": result['data']
        }), 200
    else:
        return jsonify({
            "code": 500,
            "msg": result['msg']
        }), 500


@stats_bp.route('/import', methods=['POST'])
def import_data():
    """从 SQL 文件恢复数据
    
    请求体:
    {
        "sql_content": "SQL文件内容..."
    }
    """
    data = request.get_json()
    
    if 'sql_content' not in data:
        return jsonify({
            "code": 400,
            "msg": "缺少必填字段: sql_content"
        }), 400
    
    result = StatsService.import_data(sql_content=data['sql_content'])
    
    if result['success']:
        return jsonify({
            "code": 0,
            "msg": result['msg'],
            "data": result['data']
        }), 200
    else:
        return jsonify({
            "code": 400,
            "msg": result['msg']
        }), 400


# ==================== 配置查询接口 ====================

@stats_bp.route('/config/modules', methods=['GET'])
def get_modules():
    """获取所有支持的模块列表"""
    return jsonify({
        "code": 0,
        "msg": "查询成功",
        "data": {
            "modules": MODULES,
            "steps": STEPS,
            "error_types": ERROR_TYPES
        }
    }), 200


@stats_bp.route('/config/error-types/<module>', methods=['GET'])
def get_error_types(module):
    """获取指定模块的错误类型配置"""
    if module not in MODULES:
        return jsonify({
            "code": 400,
            "msg": f"无效的模块: {module}"
        }), 400
    
    return jsonify({
        "code": 0,
        "msg": "查询成功",
        "data": {
            "module": module,
            "error_types": ERROR_TYPES.get(module, {})
        }
    }), 200


@stats_bp.route('/debug/db-status', methods=['GET'])
def get_db_status():
    """调试接口：获取数据库状态"""
    from database import get_db_connection
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 总记录数
        cursor.execute('SELECT COUNT(*) as total FROM error_statistics')
        total_records = cursor.fetchone()["total"]
        
        # 最早的记录日期
        cursor.execute('SELECT MIN(date(record_created_at)) as min_date FROM error_statistics')
        min_date = cursor.fetchone()["min_date"]
        
        # 最晚的记录日期
        cursor.execute('SELECT MAX(date(record_created_at)) as max_date FROM error_statistics')
        max_date = cursor.fetchone()["max_date"]
        
        # 各模块记录数
        cursor.execute('''
            SELECT module, COUNT(*) as count 
            FROM error_statistics 
            GROUP BY module
        ''')
        module_counts = [{"module": row["module"], "count": row["count"]} for row in cursor.fetchall()]
        
        # 最近的10条记录
        cursor.execute('''
            SELECT record_id, module, step, error_type, error_count, record_created_at
            FROM error_statistics
            ORDER BY record_created_at DESC
            LIMIT 10
        ''')
        recent_records = [{
            "record_id": row["record_id"],
            "module": row["module"],
            "step": row["step"],
            "error_type": row["error_type"],
            "error_count": row["error_count"],
            "record_created_at": row["record_created_at"]
        } for row in cursor.fetchall()]
        
        conn.close()
        
        result = {
            "total_records": total_records,
            "min_date": min_date,
            "max_date": max_date,
            "module_counts": module_counts,
            "recent_records": recent_records
        }
        
        return jsonify({
            "code": 0,
            "msg": "查询成功",
            "data": result
        }), 200
    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": f"查询失败: {str(e)}"
        }), 500
