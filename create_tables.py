#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Supabase 테이블 자동 생성 스크립트
영업이익 테이블을 포함한 모든 필요한 테이블을 생성합니다.
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# Supabase 설정
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("⚠️ SUPABASE_URL 및 SUPABASE_KEY 환경 변수가 필요합니다. .env 파일을 확인하세요.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# SQL 쿼리들
CREATE_TABLE_SQLS = [
    # 1. 주가 데이터 테이블
    """
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
    
    # 2. 매출 데이터 테이블
    """
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
    
    # 3. 영업이익 데이터 테이블
    """
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
    
    # 인덱스 생성
    """
    CREATE INDEX IF NOT EXISTS idx_stock_price_code_year ON stock_price_data(stock_code, year);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_stock_revenue_code_year ON stock_revenue_data(stock_code, year);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_stock_operating_income_code_year ON stock_operating_income_data(stock_code, year);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_stock_price_cache ON stock_price_data(cache_year, cache_month);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_stock_revenue_cache ON stock_revenue_data(cache_year, cache_month);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_stock_operating_income_cache ON stock_operating_income_data(cache_year, cache_month);
    """
]

def create_tables_via_rpc():
    """RPC 함수를 통해 테이블 생성"""
    print("=" * 80)
    print("Supabase 테이블 생성 시작")
    print("=" * 80)
    
    for i, sql in enumerate(CREATE_TABLE_SQLS, 1):
        try:
            print(f"\n[{i}/{len(CREATE_TABLE_SQLS)}] SQL 실행 중...")
            print(f"SQL: {sql[:100]}...")
            
            # Supabase에서 SQL을 실행하려면 RPC 함수가 필요합니다
            # 대신 직접 테이블을 확인하고 존재 여부를 판단합니다
            result = supabase.rpc('exec_sql', {'sql': sql}).execute()
            print(f"✓ 성공")
            
        except Exception as e:
            print(f"✗ 오류: {e}")
            print(f"   주의: Supabase에서 직접 SQL 실행이 제한될 수 있습니다.")
    
    print("\n" + "=" * 80)
    print("테이블 생성 완료")
    print("=" * 80)

def print_manual_instructions():
    """수동 설정 안내"""
    print("\n" + "=" * 80)
    print("⚠️  Supabase Python SDK로 직접 테이블을 생성할 수 없습니다.")
    print("=" * 80)
    print("\n다음 방법 중 하나를 선택하세요:\n")
    
    print("방법 1: Supabase 대시보드에서 직접 실행 (권장)")
    print("-" * 80)
    print("1. https://xrdwcnarfdxszqbboylt.supabase.co 에 로그인")
    print("2. 왼쪽 메뉴에서 'SQL Editor' 클릭")
    print("3. 'setup_tables.sql' 파일의 내용을 복사해서 실행\n")
    
    print("방법 2: 아래 SQL을 직접 복사해서 실행")
    print("-" * 80)
    
    # setup_tables.sql 파일 읽기
    setup_file = 'setup_tables.sql'
    if os.path.exists(setup_file):
        with open(setup_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
            print(sql_content)
    else:
        # 파일이 없으면 직접 SQL 출력
        combined_sql = "\n\n".join(CREATE_TABLE_SQLS)
        print(combined_sql)
    
    print("\n" + "=" * 80)

if __name__ == '__main__':
    print("\n🚀 Supabase 테이블 생성 도구")
    print_manual_instructions()
    
    print("\n\n💡 참고:")
    print("   - Supabase는 보안상의 이유로 클라이언트 SDK에서 DDL 실행을 제한합니다.")
    print("   - 테이블 생성은 Supabase 대시보드의 SQL Editor에서 수행해야 합니다.")
    print("   - 위의 SQL을 복사하여 Supabase SQL Editor에서 실행하세요.\n")


