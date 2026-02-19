"""
数据库模块初始化
提供SQLite数据库连接和初始化功能
"""
import os
import sqlite3
from pathlib import Path

# 数据库文件路径
DATABASE_DIR = Path(__file__).parent
DATABASE_PATH = DATABASE_DIR / "stats.db"

# 模块和步骤定义
MODULES = ['lr0', 'slr1', 'll1', 'fa']
STEPS = ['step2', 'step3', 'step4', 'step5']

# 各模块的错误类型定义
ERROR_TYPES = {
    'lr0': {
        'step2': ['augmentedFormula'],
        'step3': ['dfaState', 'gotoTransition'],
        'step4': ['actionTable', 'gotoTable'],
        'step5': ['analysisStep']
    },
    'slr1': {
        'step2': ['augmentedFormula'],
        'step3': ['dfaState', 'gotoTransition'],
        'step4': ['actionTable', 'gotoTable'],
        'step5': ['analysisStep']
    },
    'll1': {
        'step2': ['firstSet', 'followSet'],
        'step3': ['parsingTable'],
        'step4': ['analysisStep']
    },
    'fa': {
        'step2': ['nfaCanvas'],
        'step3': ['conversionTable', 'transitionMatrix'],
        'step4': ['dfaCanvas'],
        'step5': ['pSets', 'minimizedMatrix'],
        'step6': ['minDfaCanvas']
    }
}


def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """初始化数据库，创建表和索引"""
    # 确保数据库目录存在
    DATABASE_DIR.mkdir(parents=True, exist_ok=True)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 创建错误统计主表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS error_statistics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id TEXT NOT NULL,
            module TEXT NOT NULL,
            step TEXT NOT NULL,
            error_type TEXT NOT NULL,
            error_count INTEGER NOT NULL DEFAULT 0,
            record_created_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(record_id, module, step, error_type)
        )
    ''')
    
    # 创建每日汇总表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_summary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            module TEXT NOT NULL,
            step TEXT NOT NULL,
            error_type TEXT NOT NULL,
            total_errors INTEGER NOT NULL DEFAULT 0,
            unique_records INTEGER NOT NULL DEFAULT 0,
            UNIQUE(date, module, step, error_type)
        )
    ''')
    
    # 创建索引
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_stats_module_step 
        ON error_statistics(module, step)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_stats_record_created 
        ON error_statistics(record_created_at)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_stats_module_step_created 
        ON error_statistics(module, step, record_created_at)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_summary_date 
        ON daily_summary(date)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_summary_module_step 
        ON daily_summary(module, step)
    ''')
    
    conn.commit()
    conn.close()
    
    print(f"[Database] 数据库初始化完成: {DATABASE_PATH}")


def reset_database():
    """重置数据库（删除所有数据）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM error_statistics')
    cursor.execute('DELETE FROM daily_summary')
    
    conn.commit()
    conn.close()
    
    print("[Database] 数据库已重置")


def delete_database():
    """删除数据库文件"""
    if DATABASE_PATH.exists():
        DATABASE_PATH.unlink()
        print(f"[Database] 数据库文件已删除: {DATABASE_PATH}")
    else:
        print("[Database] 数据库文件不存在")


# 初始化数据库（导入时自动执行）
init_database()
