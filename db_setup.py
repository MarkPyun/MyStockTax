#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
데이터베이스 테이블 자동 생성 모듈
새로운 데이터 항목이 추가될 때마다 이 파일에 테이블 스키마를 추가하면 됩니다.
"""

import os
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# Supabase PostgreSQL 연결 정보
# 형식: postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres
SUPABASE_DB_URL = os.getenv(
    'SUPABASE_DB_URL',
    'postgresql://postgres.xrdwcnarfdxszqbboylt:your_password@aws-0-ap-northeast-2.pooler.supabase.com:6543/postgres'
)

# 테이블 스키마 정의 (딕셔너리 형태로 관리)
TABLE_SCHEMAS = {
    'stock_price_data': {
        'description': '주가 데이터',
        'sql': """
            CREATE TABLE IF NOT EXISTS stock_price_data (
                id SERIAL PRIMARY KEY,
                stock_code VARCHAR(20) NOT NULL,
                company_name VARCHAR(200),
                year INTEGER NOT NULL,
                quarter INTEGER NOT NULL,
                stock_price DECIMAL(15,2),
                cache_year INTEGER,
                cache_month INTEGER,
                last_updated TIMESTAMP DEFAULT NOW(),
                UNIQUE(stock_code, year, quarter)
            );
        """,
        'indexes': [
            "CREATE INDEX IF NOT EXISTS idx_stock_price_code_year ON stock_price_data(stock_code, year);",
            "CREATE INDEX IF NOT EXISTS idx_stock_price_cache ON stock_price_data(cache_year, cache_month);"
        ]
    },
    
    'stock_revenue_data': {
        'description': '매출 데이터',
        'sql': """
            CREATE TABLE IF NOT EXISTS stock_revenue_data (
                id SERIAL PRIMARY KEY,
                stock_code VARCHAR(20) NOT NULL,
                company_name VARCHAR(200),
                year INTEGER NOT NULL,
                quarter INTEGER NOT NULL,
                revenue BIGINT,
                cache_year INTEGER,
                cache_month INTEGER,
                last_updated TIMESTAMP DEFAULT NOW(),
                UNIQUE(stock_code, year, quarter)
            );
        """,
        'indexes': [
            "CREATE INDEX IF NOT EXISTS idx_stock_revenue_code_year ON stock_revenue_data(stock_code, year);",
            "CREATE INDEX IF NOT EXISTS idx_stock_revenue_cache ON stock_revenue_data(cache_year, cache_month);"
        ]
    },
    
    'stock_operating_income_data': {
        'description': '영업이익 데이터',
        'sql': """
            CREATE TABLE IF NOT EXISTS stock_operating_income_data (
                id SERIAL PRIMARY KEY,
                stock_code VARCHAR(20) NOT NULL,
                company_name VARCHAR(200),
                year INTEGER NOT NULL,
                quarter INTEGER NOT NULL,
                operating_income BIGINT,
                cache_year INTEGER,
                cache_month INTEGER,
                last_updated TIMESTAMP DEFAULT NOW(),
                UNIQUE(stock_code, year, quarter)
            );
        """,
        'indexes': [
            "CREATE INDEX IF NOT EXISTS idx_stock_operating_income_code_year ON stock_operating_income_data(stock_code, year);",
            "CREATE INDEX IF NOT EXISTS idx_stock_operating_income_cache ON stock_operating_income_data(cache_year, cache_month);"
        ]
    },
    
    'stock_net_profit_data': {
        'description': '당기순이익 데이터',
        'sql': """
            CREATE TABLE IF NOT EXISTS stock_net_profit_data (
                id SERIAL PRIMARY KEY,
                stock_code VARCHAR(20) NOT NULL,
                company_name VARCHAR(200),
                year INTEGER NOT NULL,
                quarter INTEGER NOT NULL,
                net_profit BIGINT,
                cache_year INTEGER,
                cache_month INTEGER,
                last_updated TIMESTAMP DEFAULT NOW(),
                UNIQUE(stock_code, year, quarter)
            );
        """,
        'indexes': [
            "CREATE INDEX IF NOT EXISTS idx_stock_net_profit_code_year ON stock_net_profit_data(stock_code, year);",
            "CREATE INDEX IF NOT EXISTS idx_stock_net_profit_cache ON stock_net_profit_data(cache_year, cache_month);"
        ]
    },
    
    'stock_total_debt_data': {
        'description': '총부채 데이터',
        'sql': """
            CREATE TABLE IF NOT EXISTS stock_total_debt_data (
                id SERIAL PRIMARY KEY,
                stock_code VARCHAR(20) NOT NULL,
                company_name VARCHAR(200),
                year INTEGER NOT NULL,
                quarter INTEGER NOT NULL,
                total_debt BIGINT,
                cache_year INTEGER,
                cache_month INTEGER,
                last_updated TIMESTAMP DEFAULT NOW(),
                UNIQUE(stock_code, year, quarter)
            );
        """,
        'indexes': [
            "CREATE INDEX IF NOT EXISTS idx_stock_total_debt_code_year ON stock_total_debt_data(stock_code, year);",
            "CREATE INDEX IF NOT EXISTS idx_stock_total_debt_cache ON stock_total_debt_data(cache_year, cache_month);"
        ]
    },
    
    'stock_current_liabilities_data': {
        'description': '유동부채 데이터',
        'sql': """
            CREATE TABLE IF NOT EXISTS stock_current_liabilities_data (
                id SERIAL PRIMARY KEY,
                stock_code VARCHAR(20) NOT NULL,
                company_name VARCHAR(200),
                year INTEGER NOT NULL,
                quarter INTEGER NOT NULL,
                current_liabilities BIGINT,
                cache_year INTEGER,
                cache_month INTEGER,
                last_updated TIMESTAMP DEFAULT NOW(),
                UNIQUE(stock_code, year, quarter)
            );
        """,
        'indexes': [
            "CREATE INDEX IF NOT EXISTS idx_stock_current_liabilities_code_year ON stock_current_liabilities_data(stock_code, year);",
            "CREATE INDEX IF NOT EXISTS idx_stock_current_liabilities_cache ON stock_current_liabilities_data(cache_year, cache_month);"
        ]
    },
    
    'stock_interest_expense_data': {
        'description': '이자비용 데이터',
        'sql': """
            CREATE TABLE IF NOT EXISTS stock_interest_expense_data (
                id SERIAL PRIMARY KEY,
                stock_code VARCHAR(20) NOT NULL,
                company_name VARCHAR(200),
                year INTEGER NOT NULL,
                quarter INTEGER NOT NULL,
                interest_expense BIGINT,
                cache_year INTEGER,
                cache_month INTEGER,
                last_updated TIMESTAMP DEFAULT NOW(),
                UNIQUE(stock_code, year, quarter)
            );
        """,
        'indexes': [
            "CREATE INDEX IF NOT EXISTS idx_stock_interest_expense_code_year ON stock_interest_expense_data(stock_code, year);",
            "CREATE INDEX IF NOT EXISTS idx_stock_interest_expense_cache ON stock_interest_expense_data(cache_year, cache_month);"
        ]
    },
    
    'stock_cash_data': {
        'description': '현금및현금성자산 데이터',
        'sql': """
            CREATE TABLE IF NOT EXISTS stock_cash_data (
                id SERIAL PRIMARY KEY,
                stock_code VARCHAR(20) NOT NULL,
                company_name VARCHAR(200),
                year INTEGER NOT NULL,
                quarter INTEGER NOT NULL,
                cash_and_equivalents BIGINT,
                cache_year INTEGER,
                cache_month INTEGER,
                last_updated TIMESTAMP DEFAULT NOW(),
                UNIQUE(stock_code, year, quarter)
            );
        """,
        'indexes': [
            "CREATE INDEX IF NOT EXISTS idx_stock_cash_code_year ON stock_cash_data(stock_code, year);",
            "CREATE INDEX IF NOT EXISTS idx_stock_cash_cache ON stock_cash_data(cache_year, cache_month);"
        ]
    },
    
    'economy_treasury_data': {
        'description': '미국 국채금리 데이터 (5년물 vs 3개월물)',
        'sql': """
            CREATE TABLE IF NOT EXISTS economy_treasury_data (
                id SERIAL PRIMARY KEY,
                year INTEGER NOT NULL,
                quarter INTEGER NOT NULL,
                treasury_5y DECIMAL(10,4),
                treasury_3m DECIMAL(10,4),
                cache_year INTEGER,
                cache_month INTEGER,
                last_updated TIMESTAMP DEFAULT NOW(),
                UNIQUE(year, quarter)
            );
        """,
        'indexes': [
            "CREATE INDEX IF NOT EXISTS idx_economy_treasury_year ON economy_treasury_data(year);",
            "CREATE INDEX IF NOT EXISTS idx_economy_treasury_cache ON economy_treasury_data(cache_year, cache_month);"
        ]
    },
    
    'economy_cpi_data': {
        'description': 'CPI (소비자물가지수) 데이터',
        'sql': """
            CREATE TABLE IF NOT EXISTS economy_cpi_data (
                id SERIAL PRIMARY KEY,
                year INTEGER NOT NULL,
                quarter INTEGER NOT NULL,
                cpi_value DECIMAL(10,4),
                cache_year INTEGER,
                cache_month INTEGER,
                last_updated TIMESTAMP DEFAULT NOW(),
                UNIQUE(year, quarter)
            );
        """,
        'indexes': [
            "CREATE INDEX IF NOT EXISTS idx_economy_cpi_year ON economy_cpi_data(year);",
            "CREATE INDEX IF NOT EXISTS idx_economy_cpi_cache ON economy_cpi_data(cache_year, cache_month);"
        ]
    },
    
    'economy_industrial_production_data': {
        'description': '제조업 생산지수 데이터',
        'sql': """
            CREATE TABLE IF NOT EXISTS economy_industrial_production_data (
                id SERIAL PRIMARY KEY,
                year INTEGER NOT NULL,
                quarter INTEGER NOT NULL,
                production_index DECIMAL(10,4),
                cache_year INTEGER,
                cache_month INTEGER,
                last_updated TIMESTAMP DEFAULT NOW(),
                UNIQUE(year, quarter)
            );
        """,
        'indexes': [
            "CREATE INDEX IF NOT EXISTS idx_economy_industrial_production_year ON economy_industrial_production_data(year);",
            "CREATE INDEX IF NOT EXISTS idx_economy_industrial_production_cache ON economy_industrial_production_data(cache_year, cache_month);"
        ]
    },
    
    'economy_unemployment_data': {
        'description': '실업률 데이터',
        'sql': """
            CREATE TABLE IF NOT EXISTS economy_unemployment_data (
                id SERIAL PRIMARY KEY,
                year INTEGER NOT NULL,
                quarter INTEGER NOT NULL,
                unemployment_rate DECIMAL(10,4),
                cache_year INTEGER,
                cache_month INTEGER,
                last_updated TIMESTAMP DEFAULT NOW(),
                UNIQUE(year, quarter)
            );
        """,
        'indexes': [
            "CREATE INDEX IF NOT EXISTS idx_economy_unemployment_year ON economy_unemployment_data(year);",
            "CREATE INDEX IF NOT EXISTS idx_economy_unemployment_cache ON economy_unemployment_data(cache_year, cache_month);"
        ]
    },
    
    'economy_gdp_data': {
        'description': 'GDP (국내총생산) 데이터',
        'sql': """
            CREATE TABLE IF NOT EXISTS economy_gdp_data (
                id SERIAL PRIMARY KEY,
                year INTEGER NOT NULL,
                quarter INTEGER NOT NULL,
                gdp_value DECIMAL(15,4),
                cache_year INTEGER,
                cache_month INTEGER,
                last_updated TIMESTAMP DEFAULT NOW(),
                UNIQUE(year, quarter)
            );
        """,
        'indexes': [
            "CREATE INDEX IF NOT EXISTS idx_economy_gdp_year ON economy_gdp_data(year);",
            "CREATE INDEX IF NOT EXISTS idx_economy_gdp_cache ON economy_gdp_data(cache_year, cache_month);"
        ]
    },
    
    'economy_buffett_data': {
        'description': '버핏지수 (Wilshire 5000) 데이터',
        'sql': """
            CREATE TABLE IF NOT EXISTS economy_buffett_data (
                id SERIAL PRIMARY KEY,
                year INTEGER NOT NULL,
                quarter INTEGER NOT NULL,
                wilshire_5000 DECIMAL(15,4),
                cache_year INTEGER,
                cache_month INTEGER,
                last_updated TIMESTAMP DEFAULT NOW(),
                UNIQUE(year, quarter)
            );
        """,
        'indexes': [
            "CREATE INDEX IF NOT EXISTS idx_economy_buffett_year ON economy_buffett_data(year);",
            "CREATE INDEX IF NOT EXISTS idx_economy_buffett_cache ON economy_buffett_data(cache_year, cache_month);"
        ]
    },
    
    'economy_mortgage_delinquency_data': {
        'description': '모기지 연체율 데이터',
        'sql': """
            CREATE TABLE IF NOT EXISTS economy_mortgage_delinquency_data (
                id SERIAL PRIMARY KEY,
                year INTEGER NOT NULL,
                quarter INTEGER NOT NULL,
                delinquency_rate DECIMAL(10,4),
                cache_year INTEGER,
                cache_month INTEGER,
                last_updated TIMESTAMP DEFAULT NOW(),
                UNIQUE(year, quarter)
            );
        """,
        'indexes': [
            "CREATE INDEX IF NOT EXISTS idx_economy_mortgage_delinquency_year ON economy_mortgage_delinquency_data(year);",
            "CREATE INDEX IF NOT EXISTS idx_economy_mortgage_delinquency_cache ON economy_mortgage_delinquency_data(cache_year, cache_month);"
        ]
    },
}


def get_db_connection():
    """PostgreSQL 데이터베이스 연결 생성"""
    try:
        conn = psycopg2.connect(SUPABASE_DB_URL)
        return conn
    except Exception as e:
        print(f"[ERROR] 데이터베이스 연결 실패: {e}")
        return None


def create_table(conn, table_name, schema_info):
    """단일 테이블 생성"""
    try:
        cursor = conn.cursor()
        
        # 테이블 생성
        print(f"  [INFO] 테이블 생성 중: {table_name} ({schema_info['description']})")
        cursor.execute(schema_info['sql'])
        
        # 인덱스 생성
        if 'indexes' in schema_info:
            for index_sql in schema_info['indexes']:
                cursor.execute(index_sql)
        
        conn.commit()
        cursor.close()
        print(f"  [SUCCESS] 완료: {table_name}")
        return True
        
    except Exception as e:
        print(f"  [ERROR] 오류 ({table_name}): {e}")
        conn.rollback()
        return False


def create_all_tables(db_url=None):
    """모든 테이블 자동 생성"""
    print("\n" + "=" * 80)
    print("[INFO] Supabase 테이블 자동 생성 시작")
    print("=" * 80)
    
    # DB URL이 제공되면 사용
    if db_url:
        global SUPABASE_DB_URL
        SUPABASE_DB_URL = db_url
    
    # 데이터베이스 연결
    conn = get_db_connection()
    if not conn:
        print("\n[WARNING] 데이터베이스 연결에 실패했습니다.")
        print_manual_instructions()
        return False
    
    print(f"\n[SUCCESS] 데이터베이스 연결 성공")
    print(f"[INFO] 생성할 테이블 수: {len(TABLE_SCHEMAS)}개\n")
    
    # 각 테이블 생성
    success_count = 0
    for table_name, schema_info in TABLE_SCHEMAS.items():
        if create_table(conn, table_name, schema_info):
            success_count += 1
    
    conn.close()
    
    print("\n" + "=" * 80)
    print(f"✨ 완료: {success_count}/{len(TABLE_SCHEMAS)}개 테이블 생성 성공")
    print("=" * 80 + "\n")
    
    return success_count == len(TABLE_SCHEMAS)


def check_table_exists(table_name):
    """특정 테이블 존재 여부 확인 (PostgreSQL 직접 연결)"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = %s
            );
        """, (table_name,))
        
        exists = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        
        return exists
        
    except Exception as e:
        print(f"테이블 확인 오류 ({table_name}): {e}")
        if conn:
            conn.close()
        return False


def check_table_exists_via_supabase(supabase_client, table_name):
    """특정 테이블 존재 여부 확인 (Supabase API 사용)"""
    try:
        # 테이블 조회를 시도해서 존재 여부 확인
        result = supabase_client.table(table_name).select('id').limit(1).execute()
        return True
    except Exception as e:
        error_msg = str(e)
        if 'PGRST205' in error_msg or 'not find the table' in error_msg:
            # 테이블이 없는 경우
            return False
        else:
            # 다른 에러 (예: 권한 문제)
            print(f"테이블 확인 오류 ({table_name}): {e}")
            return False


def ensure_table_exists(table_name, supabase_client=None, db_url=None):
    """
    테이블이 없으면 자동으로 생성
    
    Args:
        table_name: 확인할 테이블 이름
        supabase_client: Supabase 클라이언트 (존재 여부 확인용)
        db_url: PostgreSQL 연결 URL (테이블 생성용)
    
    Returns:
        bool: 테이블이 존재하거나 성공적으로 생성되면 True
    """
    # 1. 테이블 존재 여부 확인
    if supabase_client:
        exists = check_table_exists_via_supabase(supabase_client, table_name)
    else:
        exists = check_table_exists(table_name)
    
    if exists:
        return True
    
    # 2. 테이블이 없으면 생성
    print(f"\n[WARNING] 테이블이 없습니다: {table_name}")
    print(f"[INFO] 자동으로 테이블을 생성합니다...")
    
    if table_name not in TABLE_SCHEMAS:
        print(f"[ERROR] 오류: '{table_name}' 스키마를 찾을 수 없습니다.")
        return False
    
    schema_info = TABLE_SCHEMAS[table_name]
    
    # PostgreSQL 직접 연결로 테이블 생성
    if not db_url:
        db_url = os.getenv('SUPABASE_DB_URL')
    
    if not db_url or 'your_password' in db_url.lower():
        print(f"[ERROR] SUPABASE_DB_URL 환경 변수가 설정되지 않았습니다.")
        print(f"   .env 파일에 다음을 추가하세요:")
        print(f"   SUPABASE_DB_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres")
        return False
    
    # 테이블 생성
    try:
        # DB URL 임시 저장
        original_url = globals().get('SUPABASE_DB_URL')
        globals()['SUPABASE_DB_URL'] = db_url
        
        conn = get_db_connection()
        if not conn:
            return False
        
        success = create_table(conn, table_name, schema_info)
        conn.close()
        
        # DB URL 복원
        if original_url:
            globals()['SUPABASE_DB_URL'] = original_url
        
        if success:
            print(f"[SUCCESS] 테이블 생성 완료: {table_name}")
            return True
        else:
            print(f"[ERROR] 테이블 생성 실패: {table_name}")
            return False
            
    except Exception as e:
        print(f"[ERROR] 테이블 생성 오류 ({table_name}): {e}")
        return False


def check_all_tables():
    """모든 필수 테이블 존재 여부 확인"""
    print("\n" + "=" * 80)
    print("[INFO] 테이블 존재 여부 확인")
    print("=" * 80 + "\n")
    
    missing_tables = []
    
    for table_name, schema_info in TABLE_SCHEMAS.items():
        exists = check_table_exists(table_name)
        status = "[OK] 존재" if exists else "[MISSING] 없음"
        print(f"  {status}: {table_name} ({schema_info['description']})")
        
        if not exists:
            missing_tables.append(table_name)
    
    print("\n" + "=" * 80)
    
    if missing_tables:
        print(f"[WARNING] {len(missing_tables)}개 테이블이 누락되었습니다: {', '.join(missing_tables)}")
        print("=" * 80 + "\n")
        return False
    else:
        print("[SUCCESS] 모든 필수 테이블이 존재합니다.")
        print("=" * 80 + "\n")
        return True


def print_manual_instructions():
    """수동 테이블 생성 안내"""
    print("\n" + "=" * 80)
    print("[INFO] 수동 테이블 생성 방법")
    print("=" * 80)
    
    print("\n방법 1: 환경 변수 설정 후 자동 생성")
    print("-" * 80)
    print("1. .env 파일에 다음 내용 추가:")
    print("   SUPABASE_DB_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres")
    print("2. 이 스크립트 실행: python db_setup.py")
    
    print("\n방법 2: Supabase 대시보드에서 직접 실행")
    print("-" * 80)
    print("1. https://xrdwcnarfdxszqbboylt.supabase.co 에 로그인")
    print("2. 왼쪽 메뉴에서 'SQL Editor' 클릭")
    print("3. 'setup_tables.sql' 파일의 내용을 복사해서 실행")
    
    print("\n" + "=" * 80 + "\n")


def export_to_sql_file(filename='setup_tables.sql'):
    """모든 테이블 스키마를 SQL 파일로 내보내기"""
    print(f"\n[INFO] SQL 파일 생성 중: {filename}")
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("-- MyStockTax 데이터베이스 테이블 생성 스크립트\n")
        f.write("-- Supabase SQL Editor에서 이 파일을 실행하세요.\n\n")
        
        for table_name, schema_info in TABLE_SCHEMAS.items():
            f.write(f"-- {schema_info['description']}\n")
            f.write(schema_info['sql'])
            f.write("\n\n")
            
            if 'indexes' in schema_info:
                for index_sql in schema_info['indexes']:
                    f.write(index_sql + "\n")
                f.write("\n")
    
    print(f"[SUCCESS] SQL 파일 생성 완료: {filename}\n")


if __name__ == '__main__':
    """
    스크립트 직접 실행시:
    1. 테이블 존재 여부 확인
    2. 누락된 테이블 자동 생성 시도
    3. 실패시 수동 안내 출력
    """
    
    # Windows 콘솔 인코딩 설정
    import sys
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    print("\n" + "=" * 80)
    print("MyStockTax 데이터베이스 설정 도구")
    print("=" * 80)
    
    # SQL 파일 생성
    export_to_sql_file()
    
    # 테이블 존재 여부 확인
    all_exists = check_all_tables()
    
    if not all_exists:
        print("\n[QUESTION] 누락된 테이블을 자동으로 생성하시겠습니까? (y/n): ", end='')
        response = input().strip().lower()
        
        if response == 'y':
            # 환경 변수에서 DB URL 가져오기
            db_url = os.getenv('SUPABASE_DB_URL')
            if not db_url or 'your_password' in db_url:
                print("\n[WARNING] .env 파일에 SUPABASE_DB_URL을 설정해주세요.")
                print_manual_instructions()
            else:
                create_all_tables(db_url)
        else:
            print_manual_instructions()
    
    print("\n[SUCCESS] 완료\n")

