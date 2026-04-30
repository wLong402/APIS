# -*- coding: utf-8 -*-
"""检查并创建复合唯一索引"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.database import get_db_manager

def check_locks(db):
    """检查数据库锁"""
    print('\n检查数据库进程...')
    try:
        processes = db.fetch_all('SHOW PROCESSLIST')
        for p in processes:
            pid = p.get('Id', '')
            time = p.get('Time', 0)
            state = p.get('State', '')
            info = str(p.get('Info', ''))[:80]
            if time > 5:  # 超过5秒的进程
                print(f'  [LONG] ID={pid}, Time={time}s, State={state}')
                print(f'         SQL: {info}')
    except Exception as e:
        print(f'  检查失败: {e}')

def main():
    db = get_db_manager()
    table_name = 'weiban_external_user'
    
    # 1. 检查当前索引
    sql = f"""
        SELECT INDEX_NAME, COLUMN_NAME, NON_UNIQUE 
        FROM information_schema.statistics 
        WHERE table_schema = DATABASE() 
        AND table_name = '{table_name}'
        ORDER BY INDEX_NAME, SEQ_IN_INDEX
    """
    result = db.fetch_all(sql)
    print('当前索引:')
    if result:
        for row in result:
            print(f'  {row}')
    else:
        print('  无索引')
    
    # 2. 检查是否有重复数据
    dup_sql = f"""
        SELECT `id`, `staff_id`, COUNT(*) as cnt 
        FROM `{table_name}` 
        GROUP BY `id`, `staff_id` 
        HAVING cnt > 1 
        LIMIT 5
    """
    dups = db.fetch_all(dup_sql)
    print(f'\n重复数据: {len(dups)} 组')
    if dups:
        for d in dups:
            print(f'  {d}')
    
    # 3. 清理重复数据
    if dups:
        print('\n清理重复数据...')
        # 先检查是否有锁
        check_locks(db)
        
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                # 设置更长的超时时间
                cursor.execute("SET innodb_lock_wait_timeout = 120")
                cursor.execute(f"""
                    DELETE t1 FROM `{table_name}` t1
                    INNER JOIN `{table_name}` t2 
                    WHERE t1.`id` = t2.`id` 
                    AND t1.`staff_id` = t2.`staff_id` 
                    AND t1.`pk_id` < t2.`pk_id`
                """)
                deleted = cursor.rowcount
                conn.commit()
            print(f'[OK] 已删除 {deleted} 条重复数据')
        except Exception as e:
            print(f'[FAIL] 清理重复数据失败: {e}')
            print('\n提示: 可能有其他进程占用表，请稍后重试或检查数据库连接')
            return
    
    # 4. 创建索引
    index_check = f"""
        SELECT COUNT(*) as cnt FROM information_schema.statistics 
        WHERE table_schema = DATABASE() 
        AND table_name = '{table_name}' 
        AND index_name = 'idx_user_staff'
    """
    idx_result = db.fetch_one(index_check)
    if idx_result and idx_result['cnt'] > 0:
        print('\n复合唯一索引 idx_user_staff 已存在')
    else:
        print('\n创建复合唯一索引...')
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"""
                    ALTER TABLE `{table_name}` 
                    ADD UNIQUE INDEX `idx_user_staff` (`id`, `staff_id`)
                """)
                conn.commit()
            print('[OK] 复合唯一索引 idx_user_staff 创建成功')
        except Exception as e:
            print(f'[FAIL] 创建索引失败: {e}')

if __name__ == '__main__':
    main()

