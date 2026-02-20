"""
统计服务层
提供错误统计的业务逻辑处理
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from database import get_db_connection, MODULES, STEPS, ERROR_TYPES


class StatsService:
    """统计服务类"""
    
    @staticmethod
    def record_error(
        record_id: str,
        module: str,
        step: str,
        error_type: str,
        error_count: int,
        record_created_at: str
    ) -> Dict[str, Any]:
        """
        记录错误统计
        
        Args:
            record_id: 答题记录唯一ID
            module: 模块名称 (lr0, slr1, ll1, fa)
            step: 步骤名称 (step2, step3, step4, step5)
            error_type: 错误类型
            error_count: 错误次数
            record_created_at: 答题创建时间 (ISO格式字符串)
        
        Returns:
            操作结果
        """
        # 验证参数
        if module not in MODULES:
            return {"success": False, "msg": f"无效的模块: {module}"}
        
        if step not in STEPS and step != 'step6':  # fa模块有step6
            return {"success": False, "msg": f"无效的步骤: {step}"}
        
        # 验证错误类型
        valid_types = ERROR_TYPES.get(module, {}).get(step, [])
        if error_type not in valid_types:
            return {"success": False, "msg": f"无效的错误类型: {error_type}"}
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 使用INSERT OR REPLACE语法（SQLite的UPSERT）
            cursor.execute('''
                INSERT INTO error_statistics 
                (record_id, module, step, error_type, error_count, record_created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(record_id, module, step, error_type) 
                DO UPDATE SET 
                    error_count = error_count + excluded.error_count,
                    created_at = CURRENT_TIMESTAMP
            ''', (record_id, module, step, error_type, error_count, record_created_at))
            
            conn.commit()
            
            return {
                "success": True,
                "msg": "错误统计记录成功",
                "data": {
                    "record_id": record_id,
                    "module": module,
                    "step": step,
                    "error_type": error_type,
                    "error_count": error_count
                }
            }
        except Exception as e:
            conn.rollback()
            return {"success": False, "msg": f"记录失败: {str(e)}"}
        finally:
            conn.close()
    
    @staticmethod
    def batch_record_errors(errors: List[Dict]) -> Dict[str, Any]:
        """
        批量记录错误统计
        
        Args:
            errors: 错误记录列表，每个记录包含record_id, module, step, error_type, error_count, record_created_at
        
        Returns:
            操作结果
        """
        if not errors:
            return {"success": False, "msg": "错误列表为空"}
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        success_count = 0
        fail_count = 0
        
        try:
            for error in errors:
                try:
                    cursor.execute('''
                        INSERT INTO error_statistics 
                        (record_id, module, step, error_type, error_count, record_created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ON CONFLICT(record_id, module, step, error_type) 
                        DO UPDATE SET 
                            error_count = error_count + excluded.error_count,
                            created_at = CURRENT_TIMESTAMP
                    ''', (
                        error['record_id'],
                        error['module'],
                        error['step'],
                        error['error_type'],
                        error['error_count'],
                        error['record_created_at']
                    ))
                    success_count += 1
                except Exception:
                    fail_count += 1
            
            conn.commit()
            
            return {
                "success": True,
                "msg": f"批量记录完成: 成功{success_count}条, 失败{fail_count}条",
                "data": {
                    "success_count": success_count,
                    "fail_count": fail_count
                }
            }
        except Exception as e:
            conn.rollback()
            return {"success": False, "msg": f"批量记录失败: {str(e)}"}
        finally:
            conn.close()
    
    @staticmethod
    def get_summary_by_module_step(
        module: Optional[str] = None,
        step: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        按模块和步骤获取错误统计摘要
        
        Args:
            module: 模块名称（可选）
            step: 步骤名称（可选）
            start_date: 开始日期 YYYY-MM-DD（可选）
            end_date: 结束日期 YYYY-MM-DD（可选）
        
        Returns:
            统计结果
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 构建查询条件
        conditions = []
        params = []
        
        if module:
            conditions.append("module = ?")
            params.append(module)
        
        if step:
            conditions.append("step = ?")
            params.append(step)
        
        if start_date:
            conditions.append("date(record_created_at) >= ?")
            params.append(start_date)
        
        if end_date:
            conditions.append("date(record_created_at) <= ?")
            params.append(end_date)
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        query = f'''
            SELECT 
                module,
                step,
                SUM(error_count) as total_errors,
                COUNT(DISTINCT record_id) as affected_records
            FROM error_statistics
            {where_clause}
            GROUP BY module, step
            ORDER BY module, step
        '''
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        result = [{
            "module": row["module"],
            "step": row["step"],
            "total_errors": row["total_errors"],
            "affected_records": row["affected_records"]
        } for row in rows]
        
        conn.close()
        
        return {
            "success": True,
            "msg": "查询成功",
            "data": result
        }
    
    @staticmethod
    def get_error_type_distribution(
        module: str,
        step: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取错误类型分布
        
        Args:
            module: 模块名称
            step: 步骤名称（可选）
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）
        
        Returns:
            错误类型分布
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        
        conditions = ["module = ?"]
        params = [module]
        
        if step:
            conditions.append("step = ?")
            params.append(step)
        
        if start_date:
            conditions.append("date(record_created_at) >= ?")
            params.append(start_date)
        
        if end_date:
            conditions.append("date(record_created_at) <= ?")
            params.append(end_date)
        
        where_clause = "WHERE " + " AND ".join(conditions)
        
        query = f'''
            SELECT 
                step,
                error_type,
                SUM(error_count) as total_errors
            FROM error_statistics
            {where_clause}
            GROUP BY step, error_type
            ORDER BY step, total_errors DESC
        '''
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # 计算百分比
        total_errors = sum(row["total_errors"] for row in rows)
        
        result = []
        for row in rows:
            percentage = round(row["total_errors"] * 100 / total_errors, 2) if total_errors > 0 else 0
            result.append({
                "step": row["step"],
                "error_type": row["error_type"],
                "total_errors": row["total_errors"],
                "percentage": percentage
            })
        
        conn.close()
        
        return {
            "success": True,
            "msg": "查询成功",
            "data": {
                "total_errors": total_errors,
                "distribution": result
            }
        }
    
    @staticmethod
    def get_trend(
        module: str,
        step: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        获取错误趋势（按天统计）
        
        Args:
            module: 模块名称
            step: 步骤名称（可选）
            days: 查询天数（默认30天）
        
        Returns:
            趋势数据
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 计算日期范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        conditions = ["module = ?", "date(record_created_at) >= ?", "date(record_created_at) <= ?"]
        params = [module, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')]
        
        if step:
            conditions.append("step = ?")
            params.append(step)
        
        where_clause = "WHERE " + " AND ".join(conditions)
        
        query = f'''
            SELECT 
                datetime(record_created_at) as day,
                SUM(error_count) as daily_errors,
                COUNT(DISTINCT record_id) as daily_records
            FROM error_statistics
            {where_clause}
            GROUP BY date(record_created_at)
            ORDER BY day
        '''
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        result = [{
            "day": row["day"],
            "daily_errors": row["daily_errors"],
            "daily_records": row["daily_records"]
        } for row in rows]
        
        conn.close()
        
        return {
            "success": True,
            "msg": "查询成功",
            "data": {
                "module": module,
                "step": step,
                "days": days,
                "trend": result
            }
        }
    
    @staticmethod
    def get_overall_stats(start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
        """获取整体统计信息
        
        Args:
            start_date: 开始日期 YYYY-MM-DD（可选）
            end_date: 结束日期 YYYY-MM-DD（可选）
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 构建时间筛选条件
        conditions = []
        params = []
        
        if start_date:
            conditions.append("date(record_created_at) >= ?")
            params.append(start_date)
        
        if end_date:
            conditions.append("date(record_created_at) <= ?")
            params.append(end_date)
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        # 总错误数
        query = f'SELECT SUM(error_count) as total FROM error_statistics {where_clause}'
        cursor.execute(query, params)
        row = cursor.fetchone()
        total_errors = row["total"] or 0
        
        # 总记录数（不同的答题记录）
        query = f'SELECT COUNT(DISTINCT record_id) as total FROM error_statistics {where_clause}'
        cursor.execute(query, params)
        row = cursor.fetchone()
        total_records = row["total"] or 0
        
        # 各模块统计
        query = f'''
            SELECT 
                module,
                SUM(error_count) as errors,
                COUNT(DISTINCT record_id) as records
            FROM error_statistics
            {where_clause}
            GROUP BY module
        '''
        cursor.execute(query, params)
        rows = cursor.fetchall()
        module_stats = [{
            "module": row["module"],
            "errors": row["errors"],
            "records": row["records"]
        } for row in rows]
        
        # 今日统计（不受时间范围影响，始终显示今日）
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute('''
            SELECT 
                SUM(error_count) as errors,
                COUNT(DISTINCT record_id) as records
            FROM error_statistics
            WHERE date(record_created_at) = ?
        ''', (today,))
        row = cursor.fetchone()
        today_stats = {
            "errors": row["errors"] or 0,
            "records": row["records"] or 0
        }
        
        conn.close()
        
        return {
            "success": True,
            "msg": "查询成功",
            "data": {
                "total_errors": total_errors,
                "total_records": total_records,
                "module_stats": module_stats,
                "today_stats": today_stats
            }
        }
    
    @staticmethod
    def clear_all_data() -> Dict[str, Any]:
        """清空所有统计数据"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM error_statistics')
            cursor.execute('DELETE FROM daily_summary')
            conn.commit()
            
            return {
                "success": True,
                "msg": "所有统计数据已清空"
            }
        except Exception as e:
            conn.rollback()
            return {
                "success": False,
                "msg": f"清空失败: {str(e)}"
            }
        finally:
            conn.close()
    
    @staticmethod
    def delete_module_data(module: str) -> Dict[str, Any]:
        """删除指定模块的数据"""
        if module not in MODULES:
            return {"success": False, "msg": f"无效的模块: {module}"}
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM error_statistics WHERE module = ?', (module,))
            cursor.execute('DELETE FROM daily_summary WHERE module = ?', (module,))
            conn.commit()
            
            return {
                "success": True,
                "msg": f"模块 {module} 的数据已删除"
            }
        except Exception as e:
            conn.rollback()
            return {
                "success": False,
                "msg": f"删除失败: {str(e)}"
            }
        finally:
            conn.close()

    @staticmethod
    def delete_by_date_range(start_date: str, end_date: str, module: Optional[str] = None) -> Dict[str, Any]:
        """删除指定日期范围的数据
        
        Args:
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD
            module: 模块名称（可选，不传则删除所有模块）
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            conditions = ["date(record_created_at) >= ?", "date(record_created_at) <= ?"]
            params = [start_date, end_date]
            
            if module:
                if module not in MODULES:
                    return {"success": False, "msg": f"无效的模块: {module}"}
                conditions.append("module = ?")
                params.append(module)
            
            where_clause = "WHERE " + " AND ".join(conditions)
            
            # 先查询要删除的记录数
            cursor.execute(f'SELECT COUNT(*) as count FROM error_statistics {where_clause}', params)
            count = cursor.fetchone()["count"]
            
            # 删除数据
            cursor.execute(f'DELETE FROM error_statistics {where_clause}', params)
            cursor.execute(f'DELETE FROM daily_summary {where_clause}', params)
            conn.commit()
            
            module_msg = f"模块 {module} 的" if module else "所有模块的"
            return {
                "success": True,
                "msg": f"已删除 {module_msg} {start_date} 至 {end_date} 的 {count} 条记录"
            }
        except Exception as e:
            conn.rollback()
            return {
                "success": False,
                "msg": f"删除失败: {str(e)}"
            }
        finally:
            conn.close()

    @staticmethod
    def export_data(start_date: Optional[str] = None, end_date: Optional[str] = None, module: Optional[str] = None) -> Dict[str, Any]:
        """导出数据为 SQL 格式
        
        Args:
            start_date: 开始日期 YYYY-MM-DD（可选）
            end_date: 结束日期 YYYY-MM-DD（可选）
            module: 模块名称（可选）
        
        Returns:
            SQL 格式的数据导出
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 构建查询条件
            conditions = []
            params = []
            
            if start_date:
                conditions.append("date(record_created_at) >= ?")
                params.append(start_date)
            
            if end_date:
                conditions.append("date(record_created_at) <= ?")
                params.append(end_date)
            
            if module:
                conditions.append("module = ?")
                params.append(module)
            
            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
            
            # 查询数据
            query = f'''
                SELECT record_id, module, step, error_type, error_count, record_created_at, created_at
                FROM error_statistics
                {where_clause}
                ORDER BY created_at DESC
            '''
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            # 生成 SQL 插入语句
            sql_lines = [
                "-- 编译原理学习平台 - 统计数据备份",
                f"-- 导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"-- 记录数: {len(rows)}",
                "",
                "BEGIN TRANSACTION;",
                "",
                "-- 创建表（如果不存在）",
                """CREATE TABLE IF NOT EXISTS error_statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    record_id TEXT NOT NULL,
                    module TEXT NOT NULL,
                    step TEXT NOT NULL,
                    error_type TEXT NOT NULL,
                    error_count INTEGER NOT NULL DEFAULT 1,
                    record_created_at TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(record_id, module, step, error_type)
                );""",
                "",
                "-- 插入数据",
            ]
            
            for row in rows:
                sql_lines.append(f"""INSERT OR REPLACE INTO error_statistics 
                    (record_id, module, step, error_type, error_count, record_created_at, created_at) 
                    VALUES ('{row['record_id']}', '{row['module']}', '{row['step']}', '{row['error_type']}', 
                    {row['error_count']}, '{row['record_created_at']}', '{row['created_at']}');""")
            
            sql_lines.extend([
                "",
                "COMMIT;",
                ""
            ])
            
            return {
                "success": True,
                "msg": f"成功导出 {len(rows)} 条记录",
                "data": {
                    "count": len(rows),
                    "sql": "\n".join(sql_lines)
                }
            }
        except Exception as e:
            return {
                "success": False,
                "msg": f"导出失败: {str(e)}"
            }
        finally:
            conn.close()

    @staticmethod
    def import_data(sql_content: str) -> Dict[str, Any]:
        """从 SQL 文件恢复数据
        
        Args:
            sql_content: SQL 文件内容
        
        Returns:
            恢复结果
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 解析 INSERT 语句
            import re
            insert_pattern = r"INSERT OR REPLACE INTO error_statistics.*?VALUES \((.*?)\);"
            matches = re.findall(insert_pattern, sql_content, re.DOTALL)
            
            if not matches:
                return {"success": False, "msg": "未找到有效的数据插入语句"}
            
            success_count = 0
            fail_count = 0
            
            for match in matches:
                try:
                    # 执行插入语句
                    cursor.execute(f"INSERT OR REPLACE INTO error_statistics (record_id, module, step, error_type, error_count, record_created_at, created_at) VALUES ({match})")
                    success_count += 1
                except Exception:
                    fail_count += 1
            
            conn.commit()
            
            return {
                "success": True,
                "msg": f"数据恢复完成: 成功 {success_count} 条, 失败 {fail_count} 条",
                "data": {
                    "success_count": success_count,
                    "fail_count": fail_count
                }
            }
        except Exception as e:
            conn.rollback()
            return {
                "success": False,
                "msg": f"恢复失败: {str(e)}"
            }
        finally:
            conn.close()
