# -*- coding: utf-8 -*-
"""
EHR 数据库工具

用于从 SQL Server (EHR 系统) 获取员工列表
"""

from typing import List, Optional
from core.logger import get_logger

logger = get_logger('weiban.ehr_db')


def get_staff_ids_from_ehr(ehr_config: dict) -> List[str]:
    """
    从 EHR 数据库获取员工ID列表
    
    查询指定部门的员工工号列表
    
    Args:
        ehr_config: EHR 数据库配置字典
            - host: 数据库主机
            - port: 端口
            - user: 用户名
            - password: 密码
            - database: 数据库名
    
    Returns:
        员工工号列表
    """
    # 尝试使用 SQLAlchemy（与 demo 一致）
    try:
        import sqlalchemy
        import pandas as pd
        
        # 构建连接字符串（参考 demo）
        # 注意：密码中的特殊字符需要 URL 编码
        from urllib.parse import quote_plus
        password_encoded = quote_plus(ehr_config['password'])
        
        connection_string = (
            f"mssql+pymssql://{ehr_config['user']}:{password_encoded}"
            f"@{ehr_config['host']}:{ehr_config['port']}/{ehr_config['database']}"
            f"?charset=utf8"
        )
        
        logger.debug(f"连接 EHR 数据库: {ehr_config['host']}:{ehr_config['port']}/{ehr_config['database']}")
        
        engine = sqlalchemy.create_engine(
            connection_string,
            connect_args={'timeout': 10},
            pool_pre_ping=True  # 连接前测试连接
        )
        
        # 执行查询（参考 demo 中的 SQL）
        query = """
        SELECT
            name,
            employee_number,
            department_name,
            hiredate,
            job_id,
            departure_time
        FROM ehr.lqxhr.dbo.employee
        WHERE department_name IN (
            '华东销售一组',
            '华东销售二组',
            '华东销售三组',
            '华东销售四组',
            '东北销售一组',
            '华东销售五组',
            '社群组'
        )
        AND job_id NOT IN (
            '电销经理',
            '管培生',
            '培训主管',
            '人事专员',
            '私域运营资深总监',
            '小程序运营'
        )
        """
        
        # 使用 pandas 读取（与 demo 一致）
        df = pd.read_sql_query(query, engine)
        
        # 提取员工工号
        staff_ids = df['employee_number'].dropna().tolist()
        
        engine.dispose()
        
        logger.info(f"从 EHR 数据库获取到 {len(staff_ids)} 个员工ID")
        
        return staff_ids
        
    except ImportError as e:
        # 如果 SQLAlchemy 或 pandas 不可用，尝试直接使用 pymssql
        logger.warning(f"SQLAlchemy/pandas 不可用，尝试使用 pymssql: {e}")
        try:
            import pymssql
            
            # 连接 SQL Server
            # pymssql 的 server 参数可以是 'host' 或 'host:port' 或 'host,port'
            # 但更推荐使用 host 和 port 分开的方式
            conn = pymssql.connect(
                server=ehr_config['host'],
                port=ehr_config['port'],
                user=ehr_config['user'],
                password=ehr_config['password'],
                database=ehr_config['database'],
                charset='UTF-8',
                timeout=10
            )
            
            cursor = conn.cursor()
            
            # 执行查询
            query = """
            SELECT
                name,
                employee_number,
                department_name,
                hiredate,
                job_id,
                departure_time
            FROM ehr.lqxhr.dbo.employee
            WHERE department_name IN (
                '华东销售一组',
                '华东销售二组',
                '华东销售三组',
                '华东销售四组',
                '东北销售一组',
                '华东销售五组',
                '社群组'
            )
            AND job_id NOT IN (
                '电销经理',
                '管培生',
                '培训主管',
                '人事专员',
                '私域运营资深总监',
                '小程序运营'
            )
            """
            
            cursor.execute(query)
            results = cursor.fetchall()
            
            # 提取员工工号（employee_number 在第2列，索引为1）
            staff_ids = [row[1] for row in results if row[1]]
            
            cursor.close()
            conn.close()
            
            logger.info(f"从 EHR 数据库获取到 {len(staff_ids)} 个员工ID")
            
            return staff_ids
            
        except ImportError:
            logger.error("缺少必要的库。请安装: pip install sqlalchemy pandas pymssql")
            raise RuntimeError("缺少必要的库。请安装: pip install sqlalchemy pandas pymssql")
    except Exception as e:
        error_msg = str(e)
        logger.error(f"从 EHR 数据库获取员工ID失败: {error_msg}")
        
        # 提供更友好的错误提示
        if "Unable to connect" in error_msg or "unavailable" in error_msg.lower():
            raise RuntimeError(
                f"无法连接到 EHR 数据库服务器 {ehr_config['host']}:{ehr_config['port']}。"
                f"请检查：\n"
                f"1. 服务器地址和端口是否正确\n"
                f"2. 网络连接是否正常\n"
                f"3. 防火墙是否允许访问\n"
                f"4. SQL Server 服务是否运行"
            )
        else:
            raise RuntimeError(f"从 EHR 数据库获取员工ID失败: {error_msg}")

