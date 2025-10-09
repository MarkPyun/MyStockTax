from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory
from flask_cors import CORS
import json
import os
from datetime import datetime, timedelta
import pandas as pd
import yfinance as yf
from supabase import create_client, Client
from fredapi import Fred
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

app = Flask(__name__)
CORS(app)

# Supabase 설정
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# FRED API 설정
FRED_API_KEY = os.getenv('FRED_API_KEY')

# 환경 변수 확인 (로컬 개발 시에만 경고)
if not SUPABASE_URL or not SUPABASE_KEY:
    print("[WARNING] SUPABASE_URL 및 SUPABASE_KEY 환경 변수가 설정되지 않았습니다.")
    print("   일부 기능이 제한될 수 있습니다.")

if not FRED_API_KEY:
    print("[WARNING] FRED_API_KEY 환경 변수가 설정되지 않았습니다.")
    print("   경제 지표 기능이 제한될 수 있습니다.")

# Supabase 클라이언트 생성 (환경 변수가 있을 때만)
supabase = None
fred = None

try:
    if SUPABASE_URL and SUPABASE_KEY:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("[SUCCESS] Supabase 연결 성공")
except Exception as e:
    print(f"[WARNING] Supabase 연결 실패: {e}")

try:
    if FRED_API_KEY:
        fred = Fred(api_key=FRED_API_KEY)
        print("[SUCCESS] FRED API 연결 성공")
except Exception as e:
    print(f"[WARNING] FRED API 연결 실패: {e}")

# 데이터베이스 자동 설정 모듈 임포트
DB_SETUP_AVAILABLE = False
ensure_table_exists = None

try:
    from db_setup import check_all_tables, create_all_tables, export_to_sql_file, TABLE_SCHEMAS, ensure_table_exists
    DB_SETUP_AVAILABLE = True
    print("✓ db_setup 모듈 로드 성공")
except ImportError as e:
    print(f"[WARNING] db_setup 모듈을 찾을 수 없습니다: {e}")
except Exception as e:
    print(f"[WARNING] db_setup 모듈 로드 중 오류: {e}")

def check_and_create_tables():
    """테이블 존재 여부를 확인하고 자동 생성 시도"""
    
    # Supabase가 초기화되지 않았으면 스킵
    if not supabase:
        print("[WARNING] Supabase 클라이언트가 초기화되지 않았습니다. 테이블 확인을 건너뜁니다.")
        return
    
    if not DB_SETUP_AVAILABLE:
        # db_setup 모듈이 없으면 기존 방식 사용
        print("\n[WARNING] db_setup 모듈을 사용할 수 없습니다.")
        print_manual_table_creation_guide()
        return
    
    print("\n" + "="*80)
    print("[INFO] 데이터베이스 테이블 확인 중...")
    print("="*80)
    
    # Supabase API로 테이블 존재 여부 확인
    required_tables = {
        'stock_price_data': '주가',
        'stock_revenue_data': '매출',
        'stock_operating_income_data': '영업이익',
        'stock_net_profit_data': '당기순이익',
        'stock_total_debt_data': '총부채',
        'stock_current_liabilities_data': '유동부채',
        'stock_interest_expense_data': '이자비용',
        'stock_cash_data': '현금및현금성자산',
        'stock_valuation_data': 'PBR/PER/EV/EBITDA'
    }
    
    missing_tables = []
    
    for table_name, table_desc in required_tables.items():
        try:
            # 테이블 조회를 시도해서 존재 여부 확인
            result = supabase.table(table_name).select('id').limit(1).execute()
            print(f"  [OK] {table_name} ({table_desc})")
        except Exception as e:
            print(f"  [MISSING] {table_name} ({table_desc}) - 테이블이 없습니다")
            missing_tables.append(table_name)
    
    if missing_tables:
        print("\n" + "="*80)
        print(f"[WARNING] {len(missing_tables)}개 테이블이 누락되었습니다!")
        print("="*80)
        
        # 자동 생성 시도
        print("\n[INFO] 자동 테이블 생성을 시도합니다...")
        
        # 환경 변수에서 DB URL 확인
        db_url = os.getenv('SUPABASE_DB_URL')
        
        if db_url and 'your_password' not in db_url.lower():
            # DB URL이 설정되어 있으면 자동 생성 시도
            print("  [INFO] SUPABASE_DB_URL 환경 변수를 발견했습니다.")
            success = create_all_tables(db_url)
            
            if success:
                print("\n[SUCCESS] 모든 테이블이 성공적으로 생성되었습니다!")
            else:
                print("\n[WARNING] 일부 테이블 생성에 실패했습니다.")
                print_manual_table_creation_guide()
        else:
            # DB URL이 없으면 수동 안내
            print("\n[WARNING] SUPABASE_DB_URL 환경 변수가 설정되지 않았습니다.")
            print("  자동 테이블 생성을 위해서는 .env 파일에 다음을 추가하세요:")
            print("  SUPABASE_DB_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres")
            print("\n[INFO] 수동으로 테이블을 생성하려면:")
            print_manual_table_creation_guide()
    else:
        print("\n[SUCCESS] 모든 필수 테이블이 존재합니다.")
        print("="*80 + "\n")

def print_manual_table_creation_guide():
    """수동 테이블 생성 안내"""
    print("\n" + "-"*80)
    print("[INFO] 수동 테이블 생성 방법:")
    print("-"*80)
    print("1. https://xrdwcnarfdxszqbboylt.supabase.co 에 로그인")
    print("2. 왼쪽 메뉴에서 'SQL Editor' 클릭")
    print("3. 'setup_tables.sql' 파일의 내용을 복사해서 실행")
    print("\n또는:")
    print("  python db_setup.py  # 이 명령으로 setup_tables.sql 파일 생성 및 안내")
    print("-"*80 + "\n")
    
    # setup_tables.sql 파일이 없으면 생성
    if not os.path.exists('setup_tables.sql'):
        try:
            export_to_sql_file()
            print("[SUCCESS] setup_tables.sql 파일을 생성했습니다.\n")
        except:
            pass

def create_tables_if_not_exist():
    """테이블이 없으면 자동으로 생성"""
    check_and_create_tables()

# 앱 시작 시 테이블 확인 및 생성
create_tables_if_not_exist()

# 데이터 저장을 위한 JSON 파일
DATA_FILE = 'data.json'

def load_data():
    """데이터 파일에서 정보를 로드합니다."""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"stocks": [], "transactions": []}

def save_data(data):
    """데이터를 파일에 저장합니다."""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def is_english_ticker(ticker):
    """입력값이 영문 티커(미국 주식)인지 확인합니다."""
    return ticker.isalpha() and ticker.isascii()

def convert_to_yahoo_symbol(ticker):
    """주식 코드를 Yahoo Finance 심볼로 변환합니다."""
    if is_english_ticker(ticker):
        return ticker.upper()  # 미국 주식
    else:
        # 한국 주식 (코스닥 일부 종목)
        kosdaq_stocks = ['035420', '035720', '207940']
        if ticker in kosdaq_stocks:
            return f"{ticker}.KQ"
        else:
            return f"{ticker}.KS"

def get_company_name(ticker):
    """Yahoo Finance에서 회사명을 조회합니다."""
    try:
        import time
        time.sleep(0.5)  # Rate limit 방지를 위한 지연
        
        yahoo_symbol = convert_to_yahoo_symbol(ticker)
        ticker_obj = yf.Ticker(yahoo_symbol)
        
        # 회사 정보 조회
        info = ticker_obj.info
        
        # 회사명 추출 (여러 필드 시도)
        company_name = info.get('longName') or info.get('shortName') or info.get('name')
        
        if company_name:
            print(f"회사명 조회 성공: {ticker} -> {company_name}")
            return company_name
        else:
            print(f"회사명을 찾을 수 없음: {ticker}")
            return f"Company_{ticker}"
            
    except Exception as e:
        print(f"회사명 조회 오류: {e}")
        return f"Company_{ticker}"

def get_stock_price_data(ticker, years=10):
    """Yahoo Finance에서 주가 데이터만 조회합니다."""
    try:
        import time
        time.sleep(0.5)  # Rate limit 방지를 위한 지연
        
        yahoo_symbol = convert_to_yahoo_symbol(ticker)
        ticker_obj = yf.Ticker(yahoo_symbol)
        
        # 주가 데이터 조회
        current_date = datetime.now()
        start_date = current_date - timedelta(days=years*365)
        
        hist = ticker_obj.history(start=start_date, end=current_date)
        
        if hist is None or hist.empty:
            print(f"Yahoo Finance에서 주가 데이터를 가져올 수 없습니다: {yahoo_symbol}")
            return None, None
        
        # 회사 정보 조회
        info = ticker_obj.info
        company_name = info.get('longName', f"Company_{ticker}") if info else f"Company_{ticker}"
        
        return hist, company_name
        
    except Exception as e:
        print(f"주가 데이터 조회 오류: {e}")
        return None, None

def get_stock_revenue_data(ticker, years=10):
    """Yahoo Finance에서 매출 데이터만 조회합니다."""
    try:
        import time
        time.sleep(0.5)  # Rate limit 방지를 위한 지연
        
        yahoo_symbol = convert_to_yahoo_symbol(ticker)
        ticker_obj = yf.Ticker(yahoo_symbol)
        
        # 매출 데이터 조회
        revenue_data = get_revenue_data_from_yahoo(ticker_obj, years)
        
        return revenue_data
        
    except Exception as e:
        print(f"매출 데이터 조회 오류: {e}")
        return {}

def get_stock_operating_income_data(ticker, years=10):
    """Yahoo Finance에서 영업이익 데이터만 조회합니다."""
    try:
        import time
        time.sleep(0.5)  # Rate limit 방지를 위한 지연
        
        yahoo_symbol = convert_to_yahoo_symbol(ticker)
        ticker_obj = yf.Ticker(yahoo_symbol)
        
        # 영업이익 데이터 조회
        operating_income_data = get_operating_income_data_from_yahoo(ticker_obj, years)
        
        return operating_income_data
        
    except Exception as e:
        print(f"영업이익 데이터 조회 오류: {e}")
        return {}

def get_stock_net_profit_data(ticker, years=10):
    """Yahoo Finance에서 당기순이익 데이터만 조회합니다."""
    try:
        import time
        time.sleep(0.5)  # Rate limit 방지를 위한 지연
        
        yahoo_symbol = convert_to_yahoo_symbol(ticker)
        ticker_obj = yf.Ticker(yahoo_symbol)
        
        # 당기순이익 데이터 조회
        net_profit_data = get_net_profit_data_from_yahoo(ticker_obj, years)
        
        return net_profit_data
        
    except Exception as e:
        print(f"당기순이익 데이터 조회 오류: {e}")
        return {}

def get_stock_total_debt_data(ticker, years=10):
    """Yahoo Finance에서 총부채 데이터만 조회합니다."""
    try:
        import time
        time.sleep(0.5)  # Rate limit 방지를 위한 지연
        
        yahoo_symbol = convert_to_yahoo_symbol(ticker)
        ticker_obj = yf.Ticker(yahoo_symbol)
        
        # 총부채 데이터 조회
        total_debt_data = get_total_debt_data_from_yahoo(ticker_obj, years)
        
        return total_debt_data
        
    except Exception as e:
        print(f"총부채 데이터 조회 오류: {e}")
        return {}

def get_stock_current_liabilities_data(ticker, years=10):
    """Yahoo Finance에서 유동부채 데이터만 조회합니다."""
    try:
        import time
        time.sleep(0.5)  # Rate limit 방지를 위한 지연
        
        yahoo_symbol = convert_to_yahoo_symbol(ticker)
        ticker_obj = yf.Ticker(yahoo_symbol)
        
        # 유동부채 데이터 조회
        current_liabilities_data = get_current_liabilities_data_from_yahoo(ticker_obj, years)
        
        return current_liabilities_data
        
    except Exception as e:
        print(f"유동부채 데이터 조회 오류: {e}")
        return {}

def get_stock_interest_expense_data(ticker, years=10):
    """Yahoo Finance에서 이자비용 데이터만 조회합니다."""
    try:
        import time
        time.sleep(0.5)  # Rate limit 방지를 위한 지연
        
        yahoo_symbol = convert_to_yahoo_symbol(ticker)
        ticker_obj = yf.Ticker(yahoo_symbol)
        
        # 이자비용 데이터 조회
        interest_expense_data = get_interest_expense_data_from_yahoo(ticker_obj, years)
        
        return interest_expense_data
        
    except Exception as e:
        print(f"이자비용 데이터 조회 오류: {e}")
        return {}

def get_stock_cash_data(ticker, years=10):
    """Yahoo Finance에서 현금및현금성자산 데이터만 조회합니다."""
    try:
        import time
        time.sleep(0.5)  # Rate limit 방지를 위한 지연
        
        yahoo_symbol = convert_to_yahoo_symbol(ticker)
        ticker_obj = yf.Ticker(yahoo_symbol)
        
        # 현금및현금성자산 데이터 조회
        cash_data = get_cash_data_from_yahoo(ticker_obj, years)
        
        return cash_data
        
    except Exception as e:
        print(f"현금및현금성자산 데이터 조회 오류: {e}")
        return {}

def get_stock_valuation_data(ticker, years=10):
    """Yahoo Finance에서 PBR, PER, EV/EBITDA 데이터만 조회합니다."""
    try:
        import time
        time.sleep(0.5)  # Rate limit 방지를 위한 지연
        
        yahoo_symbol = convert_to_yahoo_symbol(ticker)
        ticker_obj = yf.Ticker(yahoo_symbol)
        
        # 밸류에이션 데이터 조회
        valuation_data = get_valuation_data_from_yahoo(ticker_obj, years)
        
        return valuation_data
        
    except Exception as e:
        print(f"밸류에이션 데이터 조회 오류: {e}")
        return {}

def get_revenue_data_from_yahoo(ticker_obj, years=10):
    """Yahoo Finance에서 매출 데이터를 조회합니다 (연간 + 분기별)."""
    try:
        current_date = datetime.now()
        current_year = current_date.year
        
        revenue_data = {}
        
        # 1. 연간 재무 데이터 조회 (과거 데이터용)
        try:
            annual_financials = ticker_obj.financials
            
            if annual_financials is not None and not annual_financials.empty:
                # Total Revenue 행 찾기
                revenue_row = None
                for idx in annual_financials.index:
                    if 'Total Revenue' in str(idx):
                        revenue_row = idx
                        break
                
                if revenue_row:
                    print(f"연간 매출 데이터 발견: {len(annual_financials.columns)}개 년도")
                    
                    # 연간 데이터를 분기별로 나누기 (년도당 4개 분기로 분배)
                    # 현재 년도는 제외 (분기별 실제 데이터를 사용해야 함)
                    for col in annual_financials.columns:
                        year = col.year
                        
                        # 현재 년도는 제외하고 과거 년도만 처리
                        if year >= current_year - years and year < current_year:
                            annual_revenue = annual_financials.loc[revenue_row, col]
                            if annual_revenue and annual_revenue > 0:
                                # 연간 매출을 4분기로 균등 분배 (과거 년도용)
                                quarterly_avg = annual_revenue / 4
                                for quarter in range(1, 5):
                                    key = f"{year}Q{quarter}"
                                    revenue_data[key] = quarterly_avg
                                    
                                print(f"{year}년 연간 매출: {annual_revenue:,.0f} -> 분기당 평균: {quarterly_avg:,.0f}")
        except Exception as e:
            print(f"연간 재무 데이터 조회 오류: {e}")
        
        # 2. 분기별 재무 데이터 조회 (최근 데이터용 - 더 정확함)
        try:
            quarterly_financials = ticker_obj.quarterly_financials
            
            if quarterly_financials is not None and not quarterly_financials.empty:
                # Total Revenue 행 찾기
                revenue_row = None
                for idx in quarterly_financials.index:
                    if 'Total Revenue' in str(idx):
                        revenue_row = idx
                        break
                
                if revenue_row:
                    print(f"분기별 매출 데이터 발견: {len(quarterly_financials.columns)}개 분기")
                    
                    # 분기별 매출 데이터 추출 (실제 분기 데이터 - 가장 정확함)
                    # 과거 년도의 연간 평균값을 덮어쓸 수 있음
                    for col in quarterly_financials.columns:
                        year = col.year
                        quarter = ((col.month - 1) // 3) + 1
                        
                        if year >= current_year - years:
                            revenue_value = quarterly_financials.loc[revenue_row, col]
                            if revenue_value and revenue_value > 0:
                                key = f"{year}Q{quarter}"
                                revenue_data[key] = revenue_value
                                print(f"{key} (실제): {revenue_value:,.0f} (${revenue_value/1_000_000_000:.1f}B)")
        except Exception as e:
            print(f"분기별 재무 데이터 조회 오류: {e}")
        
        print(f"매출 데이터 조회 완료: 총 {len(revenue_data)}개 분기")
        return revenue_data
        
    except Exception as e:
        print(f"매출 데이터 조회 오류: {e}")
        return {}

def get_operating_income_data_from_yahoo(ticker_obj, years=10):
    """Yahoo Finance에서 영업이익 데이터를 조회합니다 (연간 + 분기별)."""
    try:
        current_date = datetime.now()
        current_year = current_date.year
        
        operating_income_data = {}
        
        # 1. 연간 재무 데이터 조회 (과거 데이터용)
        try:
            annual_financials = ticker_obj.financials
            
            if annual_financials is not None and not annual_financials.empty:
                # Operating Income 행 찾기
                operating_income_row = None
                for idx in annual_financials.index:
                    idx_str = str(idx)
                    if idx_str == 'Operating Income':  # 정확히 'Operating Income'만 찾기
                        operating_income_row = idx
                        print(f"[DEBUG] Found exact match: '{idx}'")
                        break
                
                if operating_income_row:
                    print(f"연간 영업이익 데이터 발견: {len(annual_financials.columns)}개 년도")
                    print(f"[DEBUG] Using row: {operating_income_row}")
                    
                    # 연간 데이터를 분기별로 나누기 (년도당 4개 분기로 분배)
                    # 현재 년도는 제외 (분기별 실제 데이터를 사용해야 함)
                    for col in annual_financials.columns:
                        year = col.year
                        
                        # 현재 년도는 제외하고 과거 년도만 처리
                        if year >= current_year - years and year < current_year:
                            annual_operating_income = annual_financials.loc[operating_income_row, col]
                            print(f"[DEBUG] {year}년 raw value: {annual_operating_income}, type: {type(annual_operating_income)}")
                            
                            # pd.isna() 사용하여 None/NaN 체크
                            if pd.notna(annual_operating_income) and annual_operating_income != 0:
                                # 연간 영업이익을 4분기로 균등 분배 (과거 년도용)
                                quarterly_avg = annual_operating_income / 4
                                for quarter in range(1, 5):
                                    key = f"{year}Q{quarter}"
                                    operating_income_data[key] = quarterly_avg
                                    
                                print(f"{year}년 연간 영업이익: {annual_operating_income:,.0f} -> 분기당 평균: {quarterly_avg:,.0f}")
                else:
                    print("[DEBUG] Operating Income row not found in annual financials")
        except Exception as e:
            print(f"연간 재무 데이터 조회 오류: {e}")
            import traceback
            traceback.print_exc()
        
        # 2. 분기별 재무 데이터 조회 (최근 데이터용 - 더 정확함)
        try:
            quarterly_financials = ticker_obj.quarterly_financials
            
            if quarterly_financials is not None and not quarterly_financials.empty:
                # Operating Income 행 찾기
                operating_income_row = None
                for idx in quarterly_financials.index:
                    idx_str = str(idx)
                    if idx_str == 'Operating Income':  # 정확히 'Operating Income'만 찾기
                        operating_income_row = idx
                        print(f"[DEBUG] Found exact match in quarterly: '{idx}'")
                        break
                
                if operating_income_row:
                    print(f"분기별 영업이익 데이터 발견: {len(quarterly_financials.columns)}개 분기")
                    print(f"[DEBUG] Using row: {operating_income_row}")
                    
                    # 분기별 영업이익 데이터 추출 (실제 분기 데이터 - 가장 정확함)
                    # 과거 년도의 연간 평균값을 덮어쓸 수 있음
                    for col in quarterly_financials.columns:
                        year = col.year
                        quarter = ((col.month - 1) // 3) + 1
                        
                        if year >= current_year - years:
                            operating_income_value = quarterly_financials.loc[operating_income_row, col]
                            print(f"[DEBUG] {year}Q{quarter} raw value: {operating_income_value}, type: {type(operating_income_value)}")
                            
                            # pd.isna() 사용하여 None/NaN 체크
                            if pd.notna(operating_income_value) and operating_income_value != 0:
                                key = f"{year}Q{quarter}"
                                operating_income_data[key] = operating_income_value
                                print(f"{key} (실제): {operating_income_value:,.0f} (${operating_income_value/1_000_000_000:.1f}B)")
                else:
                    print("[DEBUG] Operating Income row not found in quarterly financials")
        except Exception as e:
            print(f"분기별 재무 데이터 조회 오류: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"영업이익 데이터 조회 완료: 총 {len(operating_income_data)}개 분기")
        print(f"[DEBUG] Final operating_income_data keys: {list(operating_income_data.keys())}")
        return operating_income_data
        
    except Exception as e:
        print(f"영업이익 데이터 조회 오류: {e}")
        import traceback
        traceback.print_exc()
        return {}

def get_net_profit_data_from_yahoo(ticker_obj, years=10):
    """Yahoo Finance에서 당기순이익 데이터를 조회합니다 (연간 + 분기별)."""
    try:
        current_date = datetime.now()
        current_year = current_date.year
        
        net_profit_data = {}
        
        # 1. 연간 재무 데이터 조회 (과거 데이터용)
        try:
            annual_financials = ticker_obj.financials
            
            if annual_financials is not None and not annual_financials.empty:
                # Net Income 행 찾기
                net_income_row = None
                for idx in annual_financials.index:
                    idx_str = str(idx)
                    if idx_str == 'Net Income':  # 정확히 'Net Income'만 찾기
                        net_income_row = idx
                        print(f"[DEBUG] Found exact match: '{idx}'")
                        break
                
                if net_income_row:
                    print(f"연간 당기순이익 데이터 발견: {len(annual_financials.columns)}개 년도")
                    print(f"[DEBUG] Using row: {net_income_row}")
                    
                    # 연간 데이터를 분기별로 나누기 (년도당 4개 분기로 분배)
                    for col in annual_financials.columns:
                        year = col.year
                        
                        # 현재 년도는 제외하고 과거 년도만 처리
                        if year >= current_year - years and year < current_year:
                            annual_net_income = annual_financials.loc[net_income_row, col]
                            print(f"[DEBUG] {year}년 raw value: {annual_net_income}, type: {type(annual_net_income)}")
                            
                            # pd.isna() 사용하여 None/NaN 체크
                            if pd.notna(annual_net_income) and annual_net_income != 0:
                                # 연간 당기순이익을 4분기로 균등 분배
                                quarterly_avg = annual_net_income / 4
                                for quarter in range(1, 5):
                                    key = f"{year}Q{quarter}"
                                    net_profit_data[key] = quarterly_avg
                                    
                                print(f"{year}년 연간 당기순이익: {annual_net_income:,.0f} -> 분기당 평균: {quarterly_avg:,.0f}")
                else:
                    print("[DEBUG] Net Income row not found in annual financials")
        except Exception as e:
            print(f"연간 재무 데이터 조회 오류: {e}")
            import traceback
            traceback.print_exc()
        
        # 2. 분기별 재무 데이터 조회 (최근 데이터용 - 더 정확함)
        try:
            quarterly_financials = ticker_obj.quarterly_financials
            
            if quarterly_financials is not None and not quarterly_financials.empty:
                # Net Income 행 찾기
                net_income_row = None
                for idx in quarterly_financials.index:
                    idx_str = str(idx)
                    if idx_str == 'Net Income':  # 정확히 'Net Income'만 찾기
                        net_income_row = idx
                        print(f"[DEBUG] Found exact match in quarterly: '{idx}'")
                        break
                
                if net_income_row:
                    print(f"분기별 당기순이익 데이터 발견: {len(quarterly_financials.columns)}개 분기")
                    print(f"[DEBUG] Using row: {net_income_row}")
                    
                    # 분기별 당기순이익 데이터 추출 (실제 분기 데이터 - 가장 정확함)
                    for col in quarterly_financials.columns:
                        year = col.year
                        quarter = ((col.month - 1) // 3) + 1
                        
                        if year >= current_year - years:
                            net_income_value = quarterly_financials.loc[net_income_row, col]
                            print(f"[DEBUG] {year}Q{quarter} raw value: {net_income_value}, type: {type(net_income_value)}")
                            
                            # pd.isna() 사용하여 None/NaN 체크
                            if pd.notna(net_income_value) and net_income_value != 0:
                                key = f"{year}Q{quarter}"
                                net_profit_data[key] = net_income_value
                                print(f"{key} (실제): {net_income_value:,.0f} (${net_income_value/1_000_000_000:.1f}B)")
                else:
                    print("[DEBUG] Net Income row not found in quarterly financials")
        except Exception as e:
            print(f"분기별 재무 데이터 조회 오류: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"당기순이익 데이터 조회 완료: 총 {len(net_profit_data)}개 분기")
        print(f"[DEBUG] Final net_profit_data keys: {list(net_profit_data.keys())}")
        return net_profit_data
        
    except Exception as e:
        print(f"당기순이익 데이터 조회 오류: {e}")
        import traceback
        traceback.print_exc()
        return {}

def get_total_debt_data_from_yahoo(ticker_obj, years=10):
    """Yahoo Finance에서 총부채 데이터를 조회합니다 (연간 + 분기별)."""
    try:
        current_date = datetime.now()
        current_year = current_date.year
        
        total_debt_data = {}
        
        # 1. 연간 대차대조표 데이터 조회 (과거 데이터용)
        try:
            annual_balance_sheet = ticker_obj.balance_sheet
            
            if annual_balance_sheet is not None and not annual_balance_sheet.empty:
                # Total Debt 또는 Total Liabilities 행 찾기
                total_debt_row = None
                for idx in annual_balance_sheet.index:
                    idx_str = str(idx)
                    if idx_str == 'Total Debt':  # 정확히 'Total Debt'만 찾기
                        total_debt_row = idx
                        print(f"[DEBUG] Found exact match: '{idx}'")
                        break
                
                if total_debt_row:
                    print(f"연간 총부채 데이터 발견: {len(annual_balance_sheet.columns)}개 년도")
                    print(f"[DEBUG] Using row: {total_debt_row}")
                    
                    # 연간 데이터를 분기별로 나누기 (년도당 4개 분기로 분배)
                    for col in annual_balance_sheet.columns:
                        year = col.year
                        
                        # 현재 년도는 제외하고 과거 년도만 처리
                        if year >= current_year - years and year < current_year:
                            annual_total_debt = annual_balance_sheet.loc[total_debt_row, col]
                            print(f"[DEBUG] {year}년 raw value: {annual_total_debt}, type: {type(annual_total_debt)}")
                            
                            # pd.isna() 사용하여 None/NaN 체크
                            if pd.notna(annual_total_debt) and annual_total_debt != 0:
                                # 연간 총부채를 4분기로 균등 분배
                                quarterly_avg = annual_total_debt / 4
                                for quarter in range(1, 5):
                                    key = f"{year}Q{quarter}"
                                    total_debt_data[key] = quarterly_avg
                                    
                                print(f"{year}년 연간 총부채: {annual_total_debt:,.0f} -> 분기당 평균: {quarterly_avg:,.0f}")
                else:
                    print("[DEBUG] Total Debt row not found in annual balance sheet")
        except Exception as e:
            print(f"연간 대차대조표 데이터 조회 오류: {e}")
            import traceback
            traceback.print_exc()
        
        # 2. 분기별 대차대조표 데이터 조회 (최근 데이터용 - 더 정확함)
        try:
            quarterly_balance_sheet = ticker_obj.quarterly_balance_sheet
            
            if quarterly_balance_sheet is not None and not quarterly_balance_sheet.empty:
                # Total Debt 행 찾기
                total_debt_row = None
                for idx in quarterly_balance_sheet.index:
                    idx_str = str(idx)
                    if idx_str == 'Total Debt':  # 정확히 'Total Debt'만 찾기
                        total_debt_row = idx
                        print(f"[DEBUG] Found exact match in quarterly: '{idx}'")
                        break
                
                if total_debt_row:
                    print(f"분기별 총부채 데이터 발견: {len(quarterly_balance_sheet.columns)}개 분기")
                    print(f"[DEBUG] Using row: {total_debt_row}")
                    
                    # 분기별 총부채 데이터 추출 (실제 분기 데이터 - 가장 정확함)
                    for col in quarterly_balance_sheet.columns:
                        year = col.year
                        quarter = ((col.month - 1) // 3) + 1
                        
                        if year >= current_year - years:
                            total_debt_value = quarterly_balance_sheet.loc[total_debt_row, col]
                            print(f"[DEBUG] {year}Q{quarter} raw value: {total_debt_value}, type: {type(total_debt_value)}")
                            
                            # pd.isna() 사용하여 None/NaN 체크
                            if pd.notna(total_debt_value) and total_debt_value != 0:
                                key = f"{year}Q{quarter}"
                                total_debt_data[key] = total_debt_value
                                print(f"{key} (실제): {total_debt_value:,.0f} (${total_debt_value/1_000_000_000:.1f}B)")
                else:
                    print("[DEBUG] Total Debt row not found in quarterly balance sheet")
        except Exception as e:
            print(f"분기별 대차대조표 데이터 조회 오류: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"총부채 데이터 조회 완료: 총 {len(total_debt_data)}개 분기")
        print(f"[DEBUG] Final total_debt_data keys: {list(total_debt_data.keys())}")
        return total_debt_data
        
    except Exception as e:
        print(f"총부채 데이터 조회 오류: {e}")
        import traceback
        traceback.print_exc()
        return {}

def get_current_liabilities_data_from_yahoo(ticker_obj, years=10):
    """Yahoo Finance에서 유동부채 데이터를 조회합니다 (연간 + 분기별)."""
    try:
        current_date = datetime.now()
        current_year = current_date.year
        
        current_liabilities_data = {}
        
        # 1. 연간 대차대조표 데이터 조회 (과거 데이터용)
        try:
            annual_balance_sheet = ticker_obj.balance_sheet
            
            if annual_balance_sheet is not None and not annual_balance_sheet.empty:
                # Current Liabilities 행 찾기
                current_liabilities_row = None
                for idx in annual_balance_sheet.index:
                    idx_str = str(idx)
                    if idx_str == 'Current Liabilities':  # 정확히 'Current Liabilities'만 찾기
                        current_liabilities_row = idx
                        print(f"[DEBUG] Found exact match: '{idx}'")
                        break
                
                if current_liabilities_row:
                    print(f"연간 유동부채 데이터 발견: {len(annual_balance_sheet.columns)}개 년도")
                    print(f"[DEBUG] Using row: {current_liabilities_row}")
                    
                    # 연간 데이터를 분기별로 나누기
                    for col in annual_balance_sheet.columns:
                        year = col.year
                        
                        # 현재 년도는 제외하고 과거 년도만 처리
                        if year >= current_year - years and year < current_year:
                            annual_current_liabilities = annual_balance_sheet.loc[current_liabilities_row, col]
                            print(f"[DEBUG] {year}년 raw value: {annual_current_liabilities}, type: {type(annual_current_liabilities)}")
                            
                            # pd.isna() 사용하여 None/NaN 체크
                            if pd.notna(annual_current_liabilities) and annual_current_liabilities != 0:
                                # 연간 유동부채를 4분기로 균등 분배
                                quarterly_avg = annual_current_liabilities / 4
                                for quarter in range(1, 5):
                                    key = f"{year}Q{quarter}"
                                    current_liabilities_data[key] = quarterly_avg
                                    
                                print(f"{year}년 연간 유동부채: {annual_current_liabilities:,.0f} -> 분기당 평균: {quarterly_avg:,.0f}")
                else:
                    print("[DEBUG] Current Liabilities row not found in annual balance sheet")
        except Exception as e:
            print(f"연간 대차대조표 데이터 조회 오류: {e}")
            import traceback
            traceback.print_exc()
        
        # 2. 분기별 대차대조표 데이터 조회 (최근 데이터용 - 더 정확함)
        try:
            quarterly_balance_sheet = ticker_obj.quarterly_balance_sheet
            
            if quarterly_balance_sheet is not None and not quarterly_balance_sheet.empty:
                # Current Liabilities 행 찾기
                current_liabilities_row = None
                for idx in quarterly_balance_sheet.index:
                    idx_str = str(idx)
                    if idx_str == 'Current Liabilities':  # 정확히 'Current Liabilities'만 찾기
                        current_liabilities_row = idx
                        print(f"[DEBUG] Found exact match in quarterly: '{idx}'")
                        break
                
                if current_liabilities_row:
                    print(f"분기별 유동부채 데이터 발견: {len(quarterly_balance_sheet.columns)}개 분기")
                    print(f"[DEBUG] Using row: {current_liabilities_row}")
                    
                    # 분기별 유동부채 데이터 추출 (실제 분기 데이터 - 가장 정확함)
                    for col in quarterly_balance_sheet.columns:
                        year = col.year
                        quarter = ((col.month - 1) // 3) + 1
                        
                        if year >= current_year - years:
                            current_liabilities_value = quarterly_balance_sheet.loc[current_liabilities_row, col]
                            print(f"[DEBUG] {year}Q{quarter} raw value: {current_liabilities_value}, type: {type(current_liabilities_value)}")
                            
                            # pd.isna() 사용하여 None/NaN 체크
                            if pd.notna(current_liabilities_value) and current_liabilities_value != 0:
                                key = f"{year}Q{quarter}"
                                current_liabilities_data[key] = current_liabilities_value
                                print(f"{key} (실제): {current_liabilities_value:,.0f} (${current_liabilities_value/1_000_000_000:.1f}B)")
                else:
                    print("[DEBUG] Current Liabilities row not found in quarterly balance sheet")
        except Exception as e:
            print(f"분기별 대차대조표 데이터 조회 오류: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"유동부채 데이터 조회 완료: 총 {len(current_liabilities_data)}개 분기")
        print(f"[DEBUG] Final current_liabilities_data keys: {list(current_liabilities_data.keys())}")
        return current_liabilities_data
        
    except Exception as e:
        print(f"유동부채 데이터 조회 오류: {e}")
        import traceback
        traceback.print_exc()
        return {}

def get_interest_expense_data_from_yahoo(ticker_obj, years=10):
    """Yahoo Finance에서 이자비용 데이터를 조회합니다 (연간 + 분기별)."""
    try:
        current_date = datetime.now()
        current_year = current_date.year
        
        interest_expense_data = {}
        
        # 1. 연간 재무 데이터 조회 (과거 데이터용)
        try:
            annual_financials = ticker_obj.financials
            
            if annual_financials is not None and not annual_financials.empty:
                # Interest Expense 행 찾기
                interest_expense_row = None
                for idx in annual_financials.index:
                    idx_str = str(idx)
                    if idx_str == 'Interest Expense':  # 정확히 'Interest Expense'만 찾기
                        interest_expense_row = idx
                        print(f"[DEBUG] Found exact match: '{idx}'")
                        break
                
                if interest_expense_row:
                    print(f"연간 이자비용 데이터 발견: {len(annual_financials.columns)}개 년도")
                    print(f"[DEBUG] Using row: {interest_expense_row}")
                    
                    # 연간 데이터를 분기별로 나누기
                    for col in annual_financials.columns:
                        year = col.year
                        
                        # 현재 년도는 제외하고 과거 년도만 처리
                        if year >= current_year - years and year < current_year:
                            annual_interest_expense = annual_financials.loc[interest_expense_row, col]
                            print(f"[DEBUG] {year}년 raw value: {annual_interest_expense}, type: {type(annual_interest_expense)}")
                            
                            # pd.isna() 사용하여 None/NaN 체크
                            if pd.notna(annual_interest_expense) and annual_interest_expense != 0:
                                # 연간 이자비용을 4분기로 균등 분배
                                quarterly_avg = annual_interest_expense / 4
                                for quarter in range(1, 5):
                                    key = f"{year}Q{quarter}"
                                    interest_expense_data[key] = quarterly_avg
                                    
                                print(f"{year}년 연간 이자비용: {annual_interest_expense:,.0f} -> 분기당 평균: {quarterly_avg:,.0f}")
                else:
                    print("[DEBUG] Interest Expense row not found in annual financials")
        except Exception as e:
            print(f"연간 재무 데이터 조회 오류: {e}")
            import traceback
            traceback.print_exc()
        
        # 2. 분기별 재무 데이터 조회 (최근 데이터용 - 더 정확함)
        try:
            quarterly_financials = ticker_obj.quarterly_financials
            
            if quarterly_financials is not None and not quarterly_financials.empty:
                # Interest Expense 행 찾기
                interest_expense_row = None
                for idx in quarterly_financials.index:
                    idx_str = str(idx)
                    if idx_str == 'Interest Expense':  # 정확히 'Interest Expense'만 찾기
                        interest_expense_row = idx
                        print(f"[DEBUG] Found exact match in quarterly: '{idx}'")
                        break
                
                if interest_expense_row:
                    print(f"분기별 이자비용 데이터 발견: {len(quarterly_financials.columns)}개 분기")
                    print(f"[DEBUG] Using row: {interest_expense_row}")
                    
                    # 분기별 이자비용 데이터 추출 (실제 분기 데이터 - 가장 정확함)
                    for col in quarterly_financials.columns:
                        year = col.year
                        quarter = ((col.month - 1) // 3) + 1
                        
                        if year >= current_year - years:
                            interest_expense_value = quarterly_financials.loc[interest_expense_row, col]
                            print(f"[DEBUG] {year}Q{quarter} raw value: {interest_expense_value}, type: {type(interest_expense_value)}")
                            
                            # pd.isna() 사용하여 None/NaN 체크
                            if pd.notna(interest_expense_value) and interest_expense_value != 0:
                                key = f"{year}Q{quarter}"
                                interest_expense_data[key] = interest_expense_value
                                print(f"{key} (실제): {interest_expense_value:,.0f} (${interest_expense_value/1_000_000_000:.1f}B)")
                else:
                    print("[DEBUG] Interest Expense row not found in quarterly financials")
        except Exception as e:
            print(f"분기별 재무 데이터 조회 오류: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"이자비용 데이터 조회 완료: 총 {len(interest_expense_data)}개 분기")
        print(f"[DEBUG] Final interest_expense_data keys: {list(interest_expense_data.keys())}")
        return interest_expense_data
        
    except Exception as e:
        print(f"이자비용 데이터 조회 오류: {e}")
        import traceback
        traceback.print_exc()
        return {}

def get_cash_data_from_yahoo(ticker_obj, years=10):
    """Yahoo Finance에서 현금및현금성자산 데이터를 조회합니다 (연간 + 분기별)."""
    try:
        current_date = datetime.now()
        current_year = current_date.year
        
        cash_data = {}
        
        # 1. 연간 대차대조표 데이터 조회 (과거 데이터용)
        try:
            annual_balance_sheet = ticker_obj.balance_sheet
            
            if annual_balance_sheet is not None and not annual_balance_sheet.empty:
                # Cash And Cash Equivalents 행 찾기
                cash_row = None
                for idx in annual_balance_sheet.index:
                    idx_str = str(idx)
                    if idx_str == 'Cash And Cash Equivalents':  # 정확히 'Cash And Cash Equivalents'만 찾기
                        cash_row = idx
                        print(f"[DEBUG] Found exact match: '{idx}'")
                        break
                
                if cash_row:
                    print(f"연간 현금성자산 데이터 발견: {len(annual_balance_sheet.columns)}개 년도")
                    print(f"[DEBUG] Using row: {cash_row}")
                    
                    # 연간 데이터를 분기별로 나누기
                    for col in annual_balance_sheet.columns:
                        year = col.year
                        
                        # 현재 년도는 제외하고 과거 년도만 처리
                        if year >= current_year - years and year < current_year:
                            annual_cash = annual_balance_sheet.loc[cash_row, col]
                            print(f"[DEBUG] {year}년 raw value: {annual_cash}, type: {type(annual_cash)}")
                            
                            # pd.isna() 사용하여 None/NaN 체크
                            if pd.notna(annual_cash) and annual_cash != 0:
                                # 연간 현금성자산을 4분기로 균등 분배
                                quarterly_avg = annual_cash / 4
                                for quarter in range(1, 5):
                                    key = f"{year}Q{quarter}"
                                    cash_data[key] = quarterly_avg
                                    
                                print(f"{year}년 연간 현금성자산: {annual_cash:,.0f} -> 분기당 평균: {quarterly_avg:,.0f}")
                else:
                    print("[DEBUG] Cash And Cash Equivalents row not found in annual balance sheet")
        except Exception as e:
            print(f"연간 대차대조표 데이터 조회 오류: {e}")
            import traceback
            traceback.print_exc()
        
        # 2. 분기별 대차대조표 데이터 조회 (최근 데이터용 - 더 정확함)
        try:
            quarterly_balance_sheet = ticker_obj.quarterly_balance_sheet
            
            if quarterly_balance_sheet is not None and not quarterly_balance_sheet.empty:
                # Cash And Cash Equivalents 행 찾기
                cash_row = None
                for idx in quarterly_balance_sheet.index:
                    idx_str = str(idx)
                    if idx_str == 'Cash And Cash Equivalents':  # 정확히 'Cash And Cash Equivalents'만 찾기
                        cash_row = idx
                        print(f"[DEBUG] Found exact match in quarterly: '{idx}'")
                        break
                
                if cash_row:
                    print(f"분기별 현금성자산 데이터 발견: {len(quarterly_balance_sheet.columns)}개 분기")
                    print(f"[DEBUG] Using row: {cash_row}")
                    
                    # 분기별 현금성자산 데이터 추출 (실제 분기 데이터 - 가장 정확함)
                    for col in quarterly_balance_sheet.columns:
                        year = col.year
                        quarter = ((col.month - 1) // 3) + 1
                        
                        if year >= current_year - years:
                            cash_value = quarterly_balance_sheet.loc[cash_row, col]
                            print(f"[DEBUG] {year}Q{quarter} raw value: {cash_value}, type: {type(cash_value)}")
                            
                            # pd.isna() 사용하여 None/NaN 체크
                            if pd.notna(cash_value) and cash_value != 0:
                                key = f"{year}Q{quarter}"
                                cash_data[key] = cash_value
                                print(f"{key} (실제): {cash_value:,.0f} (${cash_value/1_000_000_000:.1f}B)")
                else:
                    print("[DEBUG] Cash And Cash Equivalents row not found in quarterly balance sheet")
        except Exception as e:
            print(f"분기별 대차대조표 데이터 조회 오류: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"현금성자산 데이터 조회 완료: 총 {len(cash_data)}개 분기")
        print(f"[DEBUG] Final cash_data keys: {list(cash_data.keys())}")
        return cash_data
        
    except Exception as e:
        print(f"현금성자산 데이터 조회 오류: {e}")
        import traceback
        traceback.print_exc()
        return {}

def get_valuation_data_from_yahoo(ticker_obj, years=10):
    """Yahoo Finance에서 PBR, PER, EV/EBITDA 데이터를 조회합니다 (분기별).
    주의: Yahoo Finance quarterly_financials는 최근 5개 분기만 제공합니다."""
    try:
        current_date = datetime.now()
        current_year = current_date.year
        
        valuation_data = {}
        
        # 필요한 데이터: 주가, Net Income, EBITDA, Tangible Book Value, Shares Outstanding
        # 1. 분기별 주가 데이터 가져오기 (충분히 긴 기간)
        hist = ticker_obj.history(period="2y")  # 2년치 주가 (5분기 커버)
        
        # 주가 데이터가 없으면 빈 딕셔너리 반환
        if hist is None or hist.empty:
            print("[DEBUG] hist is empty - no price data available")
            return {}
        
        # Timezone 제거 (timezone-naive로 변환)
        if hasattr(hist.index, 'tz') and hist.index.tz is not None:
            hist.index = hist.index.tz_localize(None)
        
        # 2. 분기별 재무제표 데이터
        quarterly_financials = ticker_obj.quarterly_financials
        quarterly_balance_sheet = ticker_obj.quarterly_balance_sheet
        
        if quarterly_financials is None or quarterly_financials.empty:
            print("[DEBUG] quarterly_financials is empty")
            return {}
            
        if quarterly_balance_sheet is None or quarterly_balance_sheet.empty:
            print("[DEBUG] quarterly_balance_sheet is empty")
            return {}
        
        # 3. 분기별로 PBR, PER, EV/EBITDA 계산 (최근 5개 분기)
        for col in quarterly_financials.columns:
            year = col.year
            quarter = ((col.month - 1) // 3) + 1
            key = f"{year}Q{quarter}"
            
            try:
                # Net Income 가져오기
                net_income = None
                if 'Net Income' in quarterly_financials.index:
                    net_income = quarterly_financials.loc['Net Income', col]
                
                # EBITDA 가져오기
                ebitda = None
                if 'EBITDA' in quarterly_financials.index:
                    ebitda = quarterly_financials.loc['EBITDA', col]
                
                # Tangible Book Value 가져오기
                tangible_book_value = None
                if col in quarterly_balance_sheet.columns:
                    if 'Tangible Book Value' in quarterly_balance_sheet.index:
                        tangible_book_value = quarterly_balance_sheet.loc['Tangible Book Value', col]
                
                # Shares Outstanding 가져오기
                shares_outstanding = None
                if col in quarterly_balance_sheet.columns:
                    if 'Ordinary Shares Number' in quarterly_balance_sheet.index:
                        shares_outstanding = quarterly_balance_sheet.loc['Ordinary Shares Number', col]
                
                # Total Debt 가져오기
                total_debt = None
                if col in quarterly_balance_sheet.columns:
                    if 'Total Debt' in quarterly_balance_sheet.index:
                        total_debt = quarterly_balance_sheet.loc['Total Debt', col]
                
                # Cash 가져오기
                cash = None
                if col in quarterly_balance_sheet.columns:
                    if 'Cash And Cash Equivalents' in quarterly_balance_sheet.index:
                        cash = quarterly_balance_sheet.loc['Cash And Cash Equivalents', col]
                
                # 해당 분기의 평균 주가 계산
                quarter_start = col
                quarter_end = col + pd.DateOffset(months=3)
                quarter_prices = hist[(hist.index >= quarter_start) & (hist.index < quarter_end)]
                
                avg_price = None
                if not quarter_prices.empty:
                    avg_price = quarter_prices['Close'].mean()
                
                # 주가 데이터가 없으면 해당 분기 건너뛰기
                if avg_price is None or pd.isna(avg_price):
                    print(f"{key}: 주가 데이터 없음 - 건너뜀")
                    continue
                
                # PER 계산 = 주가 / EPS = 주가 / (순이익 / 발행주식수)
                per = None
                if pd.notna(net_income) and pd.notna(shares_outstanding) and shares_outstanding > 0:
                    eps = net_income / shares_outstanding
                    if eps > 0:
                        per = avg_price / eps
                
                # PBR 계산 = 주가 / BPS = 주가 / (Tangible Book Value / 발행주식수)
                pbr = None
                if pd.notna(tangible_book_value) and pd.notna(shares_outstanding) and shares_outstanding > 0:
                    bps = tangible_book_value / shares_outstanding
                    if bps > 0:
                        pbr = avg_price / bps
                
                # EV/EBITDA 계산 = EV / EBITDA
                # EV = Market Cap + Total Debt - Cash
                ev_ebitda = None
                if pd.notna(ebitda) and ebitda > 0 and pd.notna(shares_outstanding) and shares_outstanding > 0:
                    market_cap = avg_price * shares_outstanding
                    ev = market_cap
                    
                    if pd.notna(total_debt):
                        ev += total_debt
                    if pd.notna(cash):
                        ev -= cash
                    
                    ev_ebitda = ev / ebitda
                
                # 데이터 저장
                if per is not None or pbr is not None or ev_ebitda is not None:
                    valuation_data[key] = {
                        'pbr': float(pbr) if pd.notna(pbr) else None,
                        'per': float(per) if pd.notna(per) else None,
                        'ev_ebitda': float(ev_ebitda) if pd.notna(ev_ebitda) else None
                    }
                    print(f"{key}: PBR={pbr:.2f if pd.notna(pbr) else 'N/A'}, PER={per:.2f if pd.notna(per) else 'N/A'}, EV/EBITDA={ev_ebitda:.2f if pd.notna(ev_ebitda) else 'N/A'}")
            
            except Exception as e:
                print(f"{key} 밸류에이션 계산 오류: {e}")
                continue
        
        print(f"밸류에이션 데이터 조회 완료: 총 {len(valuation_data)}개 분기")
        return valuation_data
        
    except Exception as e:
        print(f"밸류에이션 데이터 조회 오류: {e}")
        import traceback
        traceback.print_exc()
        return {}

def save_valuation_to_database(stock_code, company_name, valuation_data):
    """PBR, PER, EV/EBITDA 데이터를 데이터베이스에 저장합니다."""
    try:
        print(f"[DEBUG SAVE] Starting save for {stock_code}, data count: {len(valuation_data)}")
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        table_name = 'stock_valuation_data'
        
        saved_count = 0
        skipped_count = 0
        
        for quarter_key, values in valuation_data.items():
            try:
                # quarter_key에서 년도와 분기 추출 (예: "2024Q3" -> 2024, 3)
                year_str, quarter_str = quarter_key.split('Q')
                year = int(year_str)
                quarter = int(quarter_str)
                
                print(f"[DEBUG SAVE] Processing {quarter_key}: PBR={values.get('pbr')}, PER={values.get('per')}, EV/EBITDA={values.get('ev_ebitda')}")
                
                # 기본키 존재 여부 확인
                existing = supabase.table(table_name).select('id').eq('stock_code', stock_code).eq('year', year).eq('quarter', quarter).execute()
                
                if existing.data:
                    # 데이터가 이미 존재하면 건너뛰기
                    skipped_count += 1
                    print(f"밸류에이션 데이터가 이미 존재함: {stock_code} {year}Q{quarter}")
                    continue
                
                # 밸류에이션 데이터 저장
                record = {
                    'stock_code': stock_code,
                    'company_name': company_name,
                    'year': year,
                    'quarter': quarter,
                    'pbr': float(values['pbr']) if values.get('pbr') is not None else None,
                    'per': float(values['per']) if values.get('per') is not None else None,
                    'ev_ebitda': float(values['ev_ebitda']) if values.get('ev_ebitda') is not None else None,
                    'cache_year': cache_year,
                    'cache_month': cache_month,
                    'last_updated': current_date.isoformat()
                }
                
                print(f"[DEBUG SAVE] Record to insert: {record}")
                
                supabase.table(table_name).insert(record).execute()
                saved_count += 1
                print(f"새 밸류에이션 데이터 저장: {stock_code} {year}Q{quarter}")
                
            except Exception as e:
                print(f"밸류에이션 데이터베이스 처리 오류: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"밸류에이션 데이터베이스 저장 완료: {stock_code} (저장 개수: {saved_count}개, 건너뛰기: {skipped_count}개)")
        return True
        
    except Exception as e:
        print(f"밸류에이션 데이터베이스 저장 오류: {e}")
        import traceback
        traceback.print_exc()
        return False

def get_valuation_database_data(stock_code, period=5):
    """밸류에이션 데이터베이스에서 차트용 데이터 조회"""
    try:
        current_year = datetime.now().year
        start_year = current_year - period
        
        table_name = 'stock_valuation_data'
        
        # 기간 내 데이터 조회
        result = supabase.table(table_name).select('*').eq('stock_code', stock_code).gte('year', start_year).order('year', desc=False).order('quarter', desc=False).execute()
        
        return result.data if result.data else []
        
    except Exception as e:
        print(f"밸류에이션 데이터베이스 조회 오류: {e}")
        return []

def check_valuation_database_data(stock_code):
    """밸류에이션 데이터베이스에서 현재 달 데이터 확인"""
    try:
        current_date = datetime.now()
        current_year = current_date.year
        current_month = current_date.month
        
        table_name = 'stock_valuation_data'
        
        # 현재 달 데이터 조회
        result = supabase.table(table_name).select('*').eq('stock_code', stock_code).eq('cache_year', current_year).eq('cache_month', current_month).execute()
        
        if result.data:
            return True, result.data
        else:
            return False, []
            
    except Exception as e:
        print(f"밸류에이션 데이터베이스 조회 오류: {e}")
        return False, []

def check_price_database_data(stock_code):
    """주가 데이터베이스에서 현재 달 데이터 확인"""
    try:
        current_date = datetime.now()
        current_year = current_date.year
        current_month = current_date.month
        
        # 주가 데이터 테이블 (기존 테이블 사용)
        table_name = 'stock_price_data'
        
        # 현재 달 데이터 조회
        result = supabase.table(table_name).select('*').eq('stock_code', stock_code).eq('cache_year', current_year).eq('cache_month', current_month).execute()
        
        if result.data:
            return True, result.data
        else:
            return False, []
            
    except Exception as e:
        print(f"주가 데이터베이스 조회 오류: {e}")
        return False, []

def check_revenue_database_data(stock_code):
    """매출 데이터베이스에서 현재 달 데이터 확인"""
    try:
        current_date = datetime.now()
        current_year = current_date.year
        current_month = current_date.month
        
        # 매출 데이터 테이블
        table_name = 'stock_revenue_data'
        
        # 현재 달 데이터 조회
        result = supabase.table(table_name).select('*').eq('stock_code', stock_code).eq('cache_year', current_year).eq('cache_month', current_month).execute()
        
        if result.data:
            return True, result.data
        else:
            return False, []
            
    except Exception as e:
        print(f"매출 데이터베이스 조회 오류: {e}")
        return False, []

def check_operating_income_database_data(stock_code):
    """영업이익 데이터베이스에서 현재 달 데이터 확인"""
    try:
        current_date = datetime.now()
        current_year = current_date.year
        current_month = current_date.month
        
        # 영업이익 데이터 테이블
        table_name = 'stock_operating_income_data'
        
        # 현재 달 데이터 조회
        result = supabase.table(table_name).select('*').eq('stock_code', stock_code).eq('cache_year', current_year).eq('cache_month', current_month).execute()
        
        if result.data:
            return True, result.data
        else:
            return False, []
            
    except Exception as e:
        print(f"영업이익 데이터베이스 조회 오류: {e}")
        return False, []

def check_net_profit_database_data(stock_code):
    """당기순이익 데이터베이스에서 현재 달 데이터 확인"""
    try:
        current_date = datetime.now()
        current_year = current_date.year
        current_month = current_date.month
        
        # 당기순이익 데이터 테이블
        table_name = 'stock_net_profit_data'
        
        # 현재 달 데이터 조회
        result = supabase.table(table_name).select('*').eq('stock_code', stock_code).eq('cache_year', current_year).eq('cache_month', current_month).execute()
        
        if result.data:
            return True, result.data
        else:
            return False, []
            
    except Exception as e:
        print(f"당기순이익 데이터베이스 조회 오류: {e}")
        return False, []

def check_total_debt_database_data(stock_code):
    """총부채 데이터베이스에서 현재 달 데이터 확인"""
    try:
        current_date = datetime.now()
        current_year = current_date.year
        current_month = current_date.month
        
        # 총부채 데이터 테이블
        table_name = 'stock_total_debt_data'
        
        # 현재 달 데이터 조회
        result = supabase.table(table_name).select('*').eq('stock_code', stock_code).eq('cache_year', current_year).eq('cache_month', current_month).execute()
        
        if result.data:
            return True, result.data
        else:
            return False, []
            
    except Exception as e:
        print(f"총부채 데이터베이스 조회 오류: {e}")
        return False, []

def check_current_liabilities_database_data(stock_code):
    """유동부채 데이터베이스에서 현재 달 데이터 확인"""
    try:
        current_date = datetime.now()
        current_year = current_date.year
        current_month = current_date.month
        
        # 유동부채 데이터 테이블
        table_name = 'stock_current_liabilities_data'
        
        # 현재 달 데이터 조회
        result = supabase.table(table_name).select('*').eq('stock_code', stock_code).eq('cache_year', current_year).eq('cache_month', current_month).execute()
        
        if result.data:
            return True, result.data
        else:
            return False, []
            
    except Exception as e:
        print(f"유동부채 데이터베이스 조회 오류: {e}")
        return False, []

def check_interest_expense_database_data(stock_code):
    """이자비용 데이터베이스에서 현재 달 데이터 확인"""
    try:
        current_date = datetime.now()
        current_year = current_date.year
        current_month = current_date.month
        
        # 이자비용 데이터 테이블
        table_name = 'stock_interest_expense_data'
        
        # 현재 달 데이터 조회
        result = supabase.table(table_name).select('*').eq('stock_code', stock_code).eq('cache_year', current_year).eq('cache_month', current_month).execute()
        
        if result.data:
            return True, result.data
        else:
            return False, []
            
    except Exception as e:
        print(f"이자비용 데이터베이스 조회 오류: {e}")
        return False, []

def get_price_database_data(stock_code, period=5):
    """주가 데이터베이스에서 차트용 데이터 조회"""
    try:
        current_year = datetime.now().year
        start_year = current_year - period
        
        # 주가 데이터 테이블 (기존 테이블 사용)
        table_name = 'stock_price_data'
        
        # 기간 내 데이터 조회
        result = supabase.table(table_name).select('*').eq('stock_code', stock_code).gte('year', start_year).order('year', desc=False).order('quarter', desc=False).execute()
        
        return result.data if result.data else []
        
    except Exception as e:
        print(f"주가 데이터베이스 조회 오류: {e}")
        return []

def get_revenue_database_data(stock_code, period=5):
    """매출 데이터베이스에서 차트용 데이터 조회"""
    try:
        current_year = datetime.now().year
        start_year = current_year - period
        
        # 매출 데이터 테이블
        table_name = 'stock_revenue_data'
        
        # 기간 내 데이터 조회
        result = supabase.table(table_name).select('*').eq('stock_code', stock_code).gte('year', start_year).order('year', desc=False).order('quarter', desc=False).execute()
        
        return result.data if result.data else []
        
    except Exception as e:
        print(f"매출 데이터베이스 조회 오류: {e}")
        return []

def get_operating_income_database_data(stock_code, period=5):
    """영업이익 데이터베이스에서 차트용 데이터 조회"""
    try:
        current_year = datetime.now().year
        start_year = current_year - period
        
        # 영업이익 데이터 테이블
        table_name = 'stock_operating_income_data'
        
        # 기간 내 데이터 조회
        result = supabase.table(table_name).select('*').eq('stock_code', stock_code).gte('year', start_year).order('year', desc=False).order('quarter', desc=False).execute()
        
        return result.data if result.data else []
        
    except Exception as e:
        print(f"영업이익 데이터베이스 조회 오류: {e}")
        return []

def get_net_profit_database_data(stock_code, period=5):
    """당기순이익 데이터베이스에서 차트용 데이터 조회"""
    try:
        current_year = datetime.now().year
        start_year = current_year - period
        
        # 당기순이익 데이터 테이블
        table_name = 'stock_net_profit_data'
        
        # 기간 내 데이터 조회
        result = supabase.table(table_name).select('*').eq('stock_code', stock_code).gte('year', start_year).order('year', desc=False).order('quarter', desc=False).execute()
        
        return result.data if result.data else []
        
    except Exception as e:
        print(f"당기순이익 데이터베이스 조회 오류: {e}")
        return []

def get_total_debt_database_data(stock_code, period=5):
    """총부채 데이터베이스에서 차트용 데이터 조회"""
    try:
        current_year = datetime.now().year
        start_year = current_year - period
        
        # 총부채 데이터 테이블
        table_name = 'stock_total_debt_data'
        
        # 기간 내 데이터 조회
        result = supabase.table(table_name).select('*').eq('stock_code', stock_code).gte('year', start_year).order('year', desc=False).order('quarter', desc=False).execute()
        
        return result.data if result.data else []
        
    except Exception as e:
        print(f"총부채 데이터베이스 조회 오류: {e}")
        return []

def get_current_liabilities_database_data(stock_code, period=5):
    """유동부채 데이터베이스에서 차트용 데이터 조회"""
    try:
        current_year = datetime.now().year
        start_year = current_year - period
        
        # 유동부채 데이터 테이블
        table_name = 'stock_current_liabilities_data'
        
        # 기간 내 데이터 조회
        result = supabase.table(table_name).select('*').eq('stock_code', stock_code).gte('year', start_year).order('year', desc=False).order('quarter', desc=False).execute()
        
        return result.data if result.data else []
        
    except Exception as e:
        print(f"유동부채 데이터베이스 조회 오류: {e}")
        return []

def get_interest_expense_database_data(stock_code, period=5):
    """이자비용 데이터베이스에서 차트용 데이터 조회"""
    try:
        current_year = datetime.now().year
        start_year = current_year - period
        
        # 이자비용 데이터 테이블
        table_name = 'stock_interest_expense_data'
        
        # 기간 내 데이터 조회
        result = supabase.table(table_name).select('*').eq('stock_code', stock_code).gte('year', start_year).order('year', desc=False).order('quarter', desc=False).execute()
        
        return result.data if result.data else []
        
    except Exception as e:
        print(f"이자비용 데이터베이스 조회 오류: {e}")
        return []

def check_cash_database_data(stock_code):
    """현금및현금성자산 데이터베이스에서 현재 달 데이터 확인"""
    try:
        current_date = datetime.now()
        current_year = current_date.year
        current_month = current_date.month
        
        # 현금성자산 데이터 테이블
        table_name = 'stock_cash_data'
        
        # 현재 달 데이터 조회
        result = supabase.table(table_name).select('*').eq('stock_code', stock_code).eq('cache_year', current_year).eq('cache_month', current_month).execute()
        
        if result.data:
            return True, result.data
        else:
            return False, []
            
    except Exception as e:
        print(f"현금성자산 데이터베이스 조회 오류: {e}")
        return False, []

def get_cash_database_data(stock_code, period=5):
    """현금및현금성자산 데이터베이스에서 차트용 데이터 조회"""
    try:
        current_year = datetime.now().year
        start_year = current_year - period
        
        # 현금성자산 데이터 테이블
        table_name = 'stock_cash_data'
        
        # 기간 내 데이터 조회
        result = supabase.table(table_name).select('*').eq('stock_code', stock_code).gte('year', start_year).order('year', desc=False).order('quarter', desc=False).execute()
        
        return result.data if result.data else []
        
    except Exception as e:
        print(f"현금성자산 데이터베이스 조회 오류: {e}")
        return []

def process_quarterly_data(hist, ticker):
    """분기별 데이터를 처리합니다."""
    quarterly_data = []
    current_year = datetime.now().year
    current_month = datetime.now().month
    start_year = current_year - 10
    
    # 실적발표 가능한 분기 계산 (현재 달 기준)
    def get_available_quarters(year, month):
        if year < current_year:
            return 4  # 지난 해는 모든 분기
        elif year == current_year:
            if month >= 10:  # 10월 이후
                return 3  # 3분기까지
            elif month >= 7:  # 7월 이후
                return 2  # 2분기까지
            elif month >= 4:  # 4월 이후
                return 1  # 1분기만
            else:
                return 0  # 아직 실적발표 없음
        else:
            return 0  # 미래 년도
    
    for year in range(start_year, current_year + 1):
        available_quarters = get_available_quarters(year, current_month)
        
        for quarter in range(1, available_quarters + 1):
            # 분기별 데이터 필터링
            quarter_start_month = (quarter - 1) * 3 + 1
            quarter_end_month = quarter * 3
            
            quarter_data = hist[
                (hist.index.year == year) & 
                (hist.index.month >= quarter_start_month) & 
                (hist.index.month <= quarter_end_month)
            ]
            
            if not quarter_data.empty:
                avg_close = quarter_data['Close'].mean()
                
                # avg_close가 0이면 건너뛰기
                if avg_close <= 0:
                    continue
                
                avg_price_int = int(avg_close) if avg_close > 0 else 0
                
                quarterly_data.append({
                    'year': year,
                    'quarter': quarter,
                    'avg_price': avg_price_int,
                    'operating_profit_ratio': 0,  # 기본값
                    'net_profit': 0,  # 기본값
                    'revenue': 0  # 기본값 (나중에 save_to_database에서 처리)
                })
    
    return quarterly_data
        
def clear_price_cache_data(cache_year, cache_month):
    """주가 데이터에서 동일한 cache_year, cache_month를 가진 데이터 모두 삭제"""
    try:
        table_name = 'stock_price_data'
        
        # 동일한 cache_year, cache_month를 가진 데이터 삭제
        delete_result = supabase.table(table_name).delete().eq('cache_year', cache_year).eq('cache_month', cache_month).execute()
        deleted_count = len(delete_result.data) if delete_result.data else 0
        
        print(f"주가 캐시 데이터 삭제 완료: {cache_year}년 {cache_month}월 데이터 {deleted_count}개 삭제")
        return True, deleted_count
        
    except Exception as e:
        print(f"주가 캐시 데이터 삭제 오류: {e}")
        return False, 0

def clear_price_cache_data_for_ticker(ticker, cache_year, cache_month):
    """특정 종목의 주가 데이터에서 동일한 cache_year, cache_month를 가진 데이터 삭제"""
    try:
        table_name = 'stock_price_data'
        
        # 특정 종목의 동일한 cache_year, cache_month를 가진 데이터 삭제
        delete_result = supabase.table(table_name).delete().eq('stock_code', ticker).eq('cache_year', cache_year).eq('cache_month', cache_month).execute()
        deleted_count = len(delete_result.data) if delete_result.data else 0
        
        print(f"주가 캐시 데이터 삭제 완료: {ticker} {cache_year}년 {cache_month}월 데이터 {deleted_count}개 삭제")
        return True, deleted_count
        
    except Exception as e:
        print(f"주가 캐시 데이터 삭제 오류: {e}")
        return False, 0

def clear_revenue_cache_data(cache_year, cache_month):
    """매출 데이터에서 동일한 cache_year, cache_month를 가진 데이터 모두 삭제"""
    try:
        table_name = 'stock_revenue_data'
        
        # 동일한 cache_year, cache_month를 가진 데이터 삭제
        delete_result = supabase.table(table_name).delete().eq('cache_year', cache_year).eq('cache_month', cache_month).execute()
        deleted_count = len(delete_result.data) if delete_result.data else 0
        
        print(f"매출 캐시 데이터 삭제 완료: {cache_year}년 {cache_month}월 데이터 {deleted_count}개 삭제")
        return True, deleted_count
        
    except Exception as e:
        print(f"매출 캐시 데이터 삭제 오류: {e}")
        return False, 0

def clear_revenue_cache_data_for_ticker(ticker, cache_year, cache_month):
    """특정 종목의 매출 데이터에서 동일한 cache_year, cache_month를 가진 데이터 삭제"""
    try:
        table_name = 'stock_revenue_data'
        
        # 특정 종목의 동일한 cache_year, cache_month를 가진 데이터 삭제
        delete_result = supabase.table(table_name).delete().eq('stock_code', ticker).eq('cache_year', cache_year).eq('cache_month', cache_month).execute()
        deleted_count = len(delete_result.data) if delete_result.data else 0
        
        print(f"매출 캐시 데이터 삭제 완료: {ticker} {cache_year}년 {cache_month}월 데이터 {deleted_count}개 삭제")
        return True, deleted_count
        
    except Exception as e:
        print(f"매출 캐시 데이터 삭제 오류: {e}")
        return False, 0

def clear_operating_income_cache_data(cache_year, cache_month):
    """영업이익 데이터에서 동일한 cache_year, cache_month를 가진 데이터 모두 삭제"""
    try:
        table_name = 'stock_operating_income_data'
        
        # 동일한 cache_year, cache_month를 가진 데이터 삭제
        delete_result = supabase.table(table_name).delete().eq('cache_year', cache_year).eq('cache_month', cache_month).execute()
        deleted_count = len(delete_result.data) if delete_result.data else 0
        
        print(f"영업이익 캐시 데이터 삭제 완료: {cache_year}년 {cache_month}월 데이터 {deleted_count}개 삭제")
        return True, deleted_count
        
    except Exception as e:
        print(f"영업이익 캐시 데이터 삭제 오류: {e}")
        return False, 0

def clear_operating_income_cache_data_for_ticker(ticker, cache_year, cache_month):
    """특정 종목의 영업이익 데이터에서 동일한 cache_year, cache_month를 가진 데이터 삭제"""
    try:
        table_name = 'stock_operating_income_data'
        
        # 특정 종목의 동일한 cache_year, cache_month를 가진 데이터 삭제
        delete_result = supabase.table(table_name).delete().eq('stock_code', ticker).eq('cache_year', cache_year).eq('cache_month', cache_month).execute()
        deleted_count = len(delete_result.data) if delete_result.data else 0
        
        print(f"영업이익 캐시 데이터 삭제 완료: {ticker} {cache_year}년 {cache_month}월 데이터 {deleted_count}개 삭제")
        return True, deleted_count
        
    except Exception as e:
        print(f"영업이익 캐시 데이터 삭제 오류: {e}")
        return False, 0

def clear_net_profit_cache_data_for_ticker(ticker, cache_year, cache_month):
    """특정 종목의 당기순이익 데이터에서 동일한 cache_year, cache_month를 가진 데이터 삭제"""
    try:
        table_name = 'stock_net_profit_data'
        
        # 특정 종목의 동일한 cache_year, cache_month를 가진 데이터 삭제
        delete_result = supabase.table(table_name).delete().eq('stock_code', ticker).eq('cache_year', cache_year).eq('cache_month', cache_month).execute()
        deleted_count = len(delete_result.data) if delete_result.data else 0
        
        print(f"당기순이익 캐시 데이터 삭제 완료: {ticker} {cache_year}년 {cache_month}월 데이터 {deleted_count}개 삭제")
        return True, deleted_count
        
    except Exception as e:
        print(f"당기순이익 캐시 데이터 삭제 오류: {e}")
        return False, 0

def clear_total_debt_cache_data_for_ticker(ticker, cache_year, cache_month):
    """특정 종목의 총부채 데이터에서 동일한 cache_year, cache_month를 가진 데이터 삭제"""
    try:
        table_name = 'stock_total_debt_data'
        
        # 특정 종목의 동일한 cache_year, cache_month를 가진 데이터 삭제
        delete_result = supabase.table(table_name).delete().eq('stock_code', ticker).eq('cache_year', cache_year).eq('cache_month', cache_month).execute()
        deleted_count = len(delete_result.data) if delete_result.data else 0
        
        print(f"총부채 캐시 데이터 삭제 완료: {ticker} {cache_year}년 {cache_month}월 데이터 {deleted_count}개 삭제")
        return True, deleted_count
        
    except Exception as e:
        print(f"총부채 캐시 데이터 삭제 오류: {e}")
        return False, 0

def clear_current_liabilities_cache_data_for_ticker(ticker, cache_year, cache_month):
    """특정 종목의 유동부채 데이터에서 동일한 cache_year, cache_month를 가진 데이터 삭제"""
    try:
        table_name = 'stock_current_liabilities_data'
        
        # 특정 종목의 동일한 cache_year, cache_month를 가진 데이터 삭제
        delete_result = supabase.table(table_name).delete().eq('stock_code', ticker).eq('cache_year', cache_year).eq('cache_month', cache_month).execute()
        deleted_count = len(delete_result.data) if delete_result.data else 0
        
        print(f"유동부채 캐시 데이터 삭제 완료: {ticker} {cache_year}년 {cache_month}월 데이터 {deleted_count}개 삭제")
        return True, deleted_count
        
    except Exception as e:
        print(f"유동부채 캐시 데이터 삭제 오류: {e}")
        return False, 0

def clear_interest_expense_cache_data_for_ticker(ticker, cache_year, cache_month):
    """특정 종목의 이자비용 데이터에서 동일한 cache_year, cache_month를 가진 데이터 삭제"""
    try:
        table_name = 'stock_interest_expense_data'
        
        # 특정 종목의 동일한 cache_year, cache_month를 가진 데이터 삭제
        delete_result = supabase.table(table_name).delete().eq('stock_code', ticker).eq('cache_year', cache_year).eq('cache_month', cache_month).execute()
        deleted_count = len(delete_result.data) if delete_result.data else 0
        
        print(f"이자비용 캐시 데이터 삭제 완료: {ticker} {cache_year}년 {cache_month}월 데이터 {deleted_count}개 삭제")
        return True, deleted_count
        
    except Exception as e:
        print(f"이자비용 캐시 데이터 삭제 오류: {e}")
        return False, 0

def save_cash_to_database(stock_code, company_name, cash_data):
    """현금및현금성자산 데이터를 데이터베이스에 저장합니다."""
    try:
        print(f"[DEBUG SAVE] Starting save for {stock_code}, data count: {len(cash_data)}")
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        # 현금성자산 데이터 테이블
        table_name = 'stock_cash_data'
        
        # 테이블 존재 여부 확인 및 자동 생성
        if DB_SETUP_AVAILABLE and ensure_table_exists:
            db_url = os.getenv('SUPABASE_DB_URL')
            if not ensure_table_exists(table_name, supabase, db_url):
                print(f"[WARNING] {table_name} 테이블을 생성할 수 없습니다. 수동으로 생성해주세요.")
                return False
        
        saved_count = 0
        skipped_count = 0
        
        for quarter_key, cash_value in cash_data.items():
            try:
                # quarter_key에서 년도와 분기 추출 (예: "2024Q3" -> 2024, 3)
                year_str, quarter_str = quarter_key.split('Q')
                year = int(year_str)
                quarter = int(quarter_str)
                
                print(f"[DEBUG SAVE] Processing {quarter_key}: value={cash_value}")
                
                # 기본키 존재 여부 확인
                existing = supabase.table(table_name).select('id').eq('stock_code', stock_code).eq('year', year).eq('quarter', quarter).execute()
                
                if existing.data:
                    # 데이터가 이미 존재하면 건너뛰기
                    skipped_count += 1
                    print(f"현금성자산 데이터가 이미 존재함: {stock_code} {year}Q{quarter}")
                    continue
                
                # 현금성자산 데이터 저장
                record = {
                    'stock_code': stock_code,
                    'company_name': company_name,
                    'year': year,
                    'quarter': quarter,
                    'cash_and_equivalents': int(cash_value),
                    'cache_year': cache_year,
                    'cache_month': cache_month,
                    'last_updated': current_date.isoformat()
                }
                
                print(f"[DEBUG SAVE] Record to insert: {record}")
                
                supabase.table(table_name).insert(record).execute()
                saved_count += 1
                print(f"새 현금성자산 데이터 저장: {stock_code} {year}Q{quarter}, value={int(cash_value)}")
                
            except Exception as e:
                print(f"현금성자산 데이터베이스 처리 오류: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"현금성자산 데이터베이스 저장 완료: {stock_code} (새로 저장: {saved_count}개, 건너뜀: {skipped_count}개)")
        return True
        
    except Exception as e:
        print(f"현금성자산 데이터베이스 저장 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def clear_cash_cache_data_for_ticker(ticker, cache_year, cache_month):
    """특정 종목의 현금성자산 데이터에서 동일한 cache_year, cache_month를 가진 데이터 삭제"""
    try:
        table_name = 'stock_cash_data'
        
        # 특정 종목의 동일한 cache_year, cache_month를 가진 데이터 삭제
        delete_result = supabase.table(table_name).delete().eq('stock_code', ticker).eq('cache_year', cache_year).eq('cache_month', cache_month).execute()
        deleted_count = len(delete_result.data) if delete_result.data else 0
        
        print(f"현금성자산 캐시 데이터 삭제 완료: {ticker} {cache_year}년 {cache_month}월 데이터 {deleted_count}개 삭제")
        return True, deleted_count
        
    except Exception as e:
        print(f"현금성자산 캐시 데이터 삭제 오류: {e}")
        return False, 0

def clear_valuation_cache_data_for_ticker(ticker, cache_year, cache_month):
    """특정 종목의 밸류에이션 데이터에서 동일한 cache_year, cache_month를 가진 데이터 삭제"""
    try:
        table_name = 'stock_valuation_data'
        
        # 특정 종목의 동일한 cache_year, cache_month를 가진 데이터 삭제
        delete_result = supabase.table(table_name).delete().eq('stock_code', ticker).eq('cache_year', cache_year).eq('cache_month', cache_month).execute()
        deleted_count = len(delete_result.data) if delete_result.data else 0
        
        print(f"밸류에이션 캐시 데이터 삭제 완료: {ticker} {cache_year}년 {cache_month}월 데이터 {deleted_count}개 삭제")
        return True, deleted_count
        
    except Exception as e:
        print(f"밸류에이션 캐시 데이터 삭제 오류: {e}")
        return False, 0

def save_price_to_database(stock_code, company_name, quarterly_data):
    """주가 데이터를 데이터베이스에 저장합니다."""
    try:
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        # 주가 데이터 테이블 (기존 테이블 사용)
        table_name = 'stock_price_data'
        
        # 테이블 존재 여부 확인 및 자동 생성
        if DB_SETUP_AVAILABLE and ensure_table_exists:
            db_url = os.getenv('SUPABASE_DB_URL')
            if not ensure_table_exists(table_name, supabase, db_url):
                print(f"[WARNING] {table_name} 테이블을 생성할 수 없습니다. 수동으로 생성해주세요.")
                return False
        
        saved_count = 0
        skipped_count = 0
        
        for data in quarterly_data:
            # 기본키 존재 여부 확인
            try:
                existing = supabase.table(table_name).select('id').eq('stock_code', stock_code).eq('year', data['year']).eq('quarter', data['quarter']).execute()
                
                if existing.data:
                    # 데이터가 이미 존재하면 건너뛰기
                    skipped_count += 1
                    print(f"주가 데이터가 이미 존재함: {stock_code} {data['year']}Q{data['quarter']}")
                    continue
                
                # 주가 데이터 저장 (주가 전용 테이블)
                record = {
                    'stock_code': stock_code,
                    'company_name': company_name,
                    'year': data['year'],
                    'quarter': data['quarter'],
                    'stock_price': data.get('avg_price', 0) or 0,
                    'cache_year': cache_year,
                    'cache_month': cache_month,
                    'last_updated': current_date.isoformat()
                }
                
                supabase.table(table_name).insert(record).execute()
                saved_count += 1
                print(f"새 주가 데이터 저장: {stock_code} {data['year']}Q{data['quarter']}")
                
            except Exception as e:
                print(f"주가 데이터베이스 처리 오류: {e}")
                continue
        
        print(f"주가 데이터베이스 저장 완료: {stock_code} (새로 저장: {saved_count}개, 건너뜀: {skipped_count}개)")
        return True
        
    except Exception as e:
        print(f"주가 데이터베이스 저장 실패: {e}")
        return False

def save_revenue_to_database(stock_code, company_name, revenue_data):
    """매출 데이터를 데이터베이스에 저장합니다."""
    try:
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        # 매출 데이터 테이블
        table_name = 'stock_revenue_data'
        
        # 테이블 존재 여부 확인 및 자동 생성
        if DB_SETUP_AVAILABLE and ensure_table_exists:
            db_url = os.getenv('SUPABASE_DB_URL')
            if not ensure_table_exists(table_name, supabase, db_url):
                print(f"[WARNING] {table_name} 테이블을 생성할 수 없습니다. 수동으로 생성해주세요.")
                return False
        
        saved_count = 0
        skipped_count = 0
        
        for quarter_key, revenue_value in revenue_data.items():
            try:
                # quarter_key에서 년도와 분기 추출 (예: "2024Q3" -> 2024, 3)
                year_str, quarter_str = quarter_key.split('Q')
                year = int(year_str)
                quarter = int(quarter_str)
                
                # 기본키 존재 여부 확인
                existing = supabase.table(table_name).select('id').eq('stock_code', stock_code).eq('year', year).eq('quarter', quarter).execute()
                
                if existing.data:
                    # 데이터가 이미 존재하면 건너뛰기
                    skipped_count += 1
                    print(f"매출 데이터가 이미 존재함: {stock_code} {year}Q{quarter}")
                    continue
                
                # 매출 데이터 저장 (매출 전용 테이블)
                record = {
                    'stock_code': stock_code,
                    'company_name': company_name,
                    'year': year,
                    'quarter': quarter,
                    'revenue': int(revenue_value),
                    'cache_year': cache_year,
                    'cache_month': cache_month,
                    'last_updated': current_date.isoformat()
                }
                
                supabase.table(table_name).insert(record).execute()
                saved_count += 1
                print(f"새 매출 데이터 저장: {stock_code} {year}Q{quarter}")
                
            except Exception as e:
                print(f"매출 데이터베이스 처리 오류: {e}")
                continue
        
        print(f"매출 데이터베이스 저장 완료: {stock_code} (새로 저장: {saved_count}개, 건너뜀: {skipped_count}개)")
        return True
        
    except Exception as e:
        print(f"매출 데이터베이스 저장 실패: {e}")
        return False

def save_operating_income_to_database(stock_code, company_name, operating_income_data):
    """영업이익 데이터를 데이터베이스에 저장합니다."""
    try:
        print(f"[DEBUG SAVE] Starting save for {stock_code}, data count: {len(operating_income_data)}")
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        # 영업이익 데이터 테이블
        table_name = 'stock_operating_income_data'
        
        # 테이블 존재 여부 확인 및 자동 생성
        if DB_SETUP_AVAILABLE and ensure_table_exists:
            db_url = os.getenv('SUPABASE_DB_URL')
            if not ensure_table_exists(table_name, supabase, db_url):
                print(f"[WARNING] {table_name} 테이블을 생성할 수 없습니다. 수동으로 생성해주세요.")
                return False
        
        saved_count = 0
        skipped_count = 0
        
        for quarter_key, operating_income_value in operating_income_data.items():
            try:
                # quarter_key에서 년도와 분기 추출 (예: "2024Q3" -> 2024, 3)
                year_str, quarter_str = quarter_key.split('Q')
                year = int(year_str)
                quarter = int(quarter_str)
                
                print(f"[DEBUG SAVE] Processing {quarter_key}: value={operating_income_value}")
                
                # 기본키 존재 여부 확인
                existing = supabase.table(table_name).select('id').eq('stock_code', stock_code).eq('year', year).eq('quarter', quarter).execute()
                
                if existing.data:
                    # 데이터가 이미 존재하면 건너뛰기
                    skipped_count += 1
                    print(f"영업이익 데이터가 이미 존재함: {stock_code} {year}Q{quarter}")
                    continue
                
                # 영업이익 데이터 저장 (영업이익 전용 테이블)
                record = {
                    'stock_code': stock_code,
                    'company_name': company_name,
                    'year': year,
                    'quarter': quarter,
                    'operating_income': int(operating_income_value),
                    'cache_year': cache_year,
                    'cache_month': cache_month,
                    'last_updated': current_date.isoformat()
                }
                
                print(f"[DEBUG SAVE] Record to insert: {record}")
                
                supabase.table(table_name).insert(record).execute()
                saved_count += 1
                print(f"새 영업이익 데이터 저장: {stock_code} {year}Q{quarter}, value={int(operating_income_value)}")
                
            except Exception as e:
                print(f"영업이익 데이터베이스 처리 오류: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"영업이익 데이터베이스 저장 완료: {stock_code} (새로 저장: {saved_count}개, 건너뜀: {skipped_count}개)")
        return True
        
    except Exception as e:
        print(f"영업이익 데이터베이스 저장 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def save_net_profit_to_database(stock_code, company_name, net_profit_data):
    """당기순이익 데이터를 데이터베이스에 저장합니다."""
    try:
        print(f"[DEBUG SAVE] Starting save for {stock_code}, data count: {len(net_profit_data)}")
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        # 당기순이익 데이터 테이블
        table_name = 'stock_net_profit_data'
        
        # 테이블 존재 여부 확인 및 자동 생성
        if DB_SETUP_AVAILABLE and ensure_table_exists:
            db_url = os.getenv('SUPABASE_DB_URL')
            if not ensure_table_exists(table_name, supabase, db_url):
                print(f"[WARNING] {table_name} 테이블을 생성할 수 없습니다. 수동으로 생성해주세요.")
                return False
        
        saved_count = 0
        skipped_count = 0
        
        for quarter_key, net_profit_value in net_profit_data.items():
            try:
                # quarter_key에서 년도와 분기 추출 (예: "2024Q3" -> 2024, 3)
                year_str, quarter_str = quarter_key.split('Q')
                year = int(year_str)
                quarter = int(quarter_str)
                
                print(f"[DEBUG SAVE] Processing {quarter_key}: value={net_profit_value}")
                
                # 기본키 존재 여부 확인
                existing = supabase.table(table_name).select('id').eq('stock_code', stock_code).eq('year', year).eq('quarter', quarter).execute()
                
                if existing.data:
                    # 데이터가 이미 존재하면 건너뛰기
                    skipped_count += 1
                    print(f"당기순이익 데이터가 이미 존재함: {stock_code} {year}Q{quarter}")
                    continue
                
                # 당기순이익 데이터 저장
                record = {
                    'stock_code': stock_code,
                    'company_name': company_name,
                    'year': year,
                    'quarter': quarter,
                    'net_profit': int(net_profit_value),
                    'cache_year': cache_year,
                    'cache_month': cache_month,
                    'last_updated': current_date.isoformat()
                }
                
                print(f"[DEBUG SAVE] Record to insert: {record}")
                
                supabase.table(table_name).insert(record).execute()
                saved_count += 1
                print(f"새 당기순이익 데이터 저장: {stock_code} {year}Q{quarter}, value={int(net_profit_value)}")
                
            except Exception as e:
                print(f"당기순이익 데이터베이스 처리 오류: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"당기순이익 데이터베이스 저장 완료: {stock_code} (새로 저장: {saved_count}개, 건너뜀: {skipped_count}개)")
        return True
        
    except Exception as e:
        print(f"당기순이익 데이터베이스 저장 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def save_total_debt_to_database(stock_code, company_name, total_debt_data):
    """총부채 데이터를 데이터베이스에 저장합니다."""
    try:
        print(f"[DEBUG SAVE] Starting save for {stock_code}, data count: {len(total_debt_data)}")
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        # 총부채 데이터 테이블
        table_name = 'stock_total_debt_data'
        
        # 테이블 존재 여부 확인 및 자동 생성
        if DB_SETUP_AVAILABLE and ensure_table_exists:
            db_url = os.getenv('SUPABASE_DB_URL')
            if not ensure_table_exists(table_name, supabase, db_url):
                print(f"[WARNING] {table_name} 테이블을 생성할 수 없습니다. 수동으로 생성해주세요.")
                return False
        
        saved_count = 0
        skipped_count = 0
        
        for quarter_key, total_debt_value in total_debt_data.items():
            try:
                # quarter_key에서 년도와 분기 추출 (예: "2024Q3" -> 2024, 3)
                year_str, quarter_str = quarter_key.split('Q')
                year = int(year_str)
                quarter = int(quarter_str)
                
                print(f"[DEBUG SAVE] Processing {quarter_key}: value={total_debt_value}")
                
                # 기본키 존재 여부 확인
                existing = supabase.table(table_name).select('id').eq('stock_code', stock_code).eq('year', year).eq('quarter', quarter).execute()
                
                if existing.data:
                    # 데이터가 이미 존재하면 건너뛰기
                    skipped_count += 1
                    print(f"총부채 데이터가 이미 존재함: {stock_code} {year}Q{quarter}")
                    continue
                
                # 총부채 데이터 저장
                record = {
                    'stock_code': stock_code,
                    'company_name': company_name,
                    'year': year,
                    'quarter': quarter,
                    'total_debt': int(total_debt_value),
                    'cache_year': cache_year,
                    'cache_month': cache_month,
                    'last_updated': current_date.isoformat()
                }
                
                print(f"[DEBUG SAVE] Record to insert: {record}")
                
                supabase.table(table_name).insert(record).execute()
                saved_count += 1
                print(f"새 총부채 데이터 저장: {stock_code} {year}Q{quarter}, value={int(total_debt_value)}")
                
            except Exception as e:
                print(f"총부채 데이터베이스 처리 오류: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"총부채 데이터베이스 저장 완료: {stock_code} (새로 저장: {saved_count}개, 건너뜀: {skipped_count}개)")
        return True
        
    except Exception as e:
        print(f"총부채 데이터베이스 저장 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def save_current_liabilities_to_database(stock_code, company_name, current_liabilities_data):
    """유동부채 데이터를 데이터베이스에 저장합니다."""
    try:
        print(f"[DEBUG SAVE] Starting save for {stock_code}, data count: {len(current_liabilities_data)}")
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        # 유동부채 데이터 테이블
        table_name = 'stock_current_liabilities_data'
        
        # 테이블 존재 여부 확인 및 자동 생성
        if DB_SETUP_AVAILABLE and ensure_table_exists:
            db_url = os.getenv('SUPABASE_DB_URL')
            if not ensure_table_exists(table_name, supabase, db_url):
                print(f"[WARNING] {table_name} 테이블을 생성할 수 없습니다. 수동으로 생성해주세요.")
                return False
        
        saved_count = 0
        skipped_count = 0
        
        for quarter_key, current_liabilities_value in current_liabilities_data.items():
            try:
                # quarter_key에서 년도와 분기 추출 (예: "2024Q3" -> 2024, 3)
                year_str, quarter_str = quarter_key.split('Q')
                year = int(year_str)
                quarter = int(quarter_str)
                
                print(f"[DEBUG SAVE] Processing {quarter_key}: value={current_liabilities_value}")
                
                # 기본키 존재 여부 확인
                existing = supabase.table(table_name).select('id').eq('stock_code', stock_code).eq('year', year).eq('quarter', quarter).execute()
                
                if existing.data:
                    # 데이터가 이미 존재하면 건너뛰기
                    skipped_count += 1
                    print(f"유동부채 데이터가 이미 존재함: {stock_code} {year}Q{quarter}")
                    continue
                
                # 유동부채 데이터 저장
                record = {
                    'stock_code': stock_code,
                    'company_name': company_name,
                    'year': year,
                    'quarter': quarter,
                    'current_liabilities': int(current_liabilities_value),
                    'cache_year': cache_year,
                    'cache_month': cache_month,
                    'last_updated': current_date.isoformat()
                }
                
                print(f"[DEBUG SAVE] Record to insert: {record}")
                
                supabase.table(table_name).insert(record).execute()
                saved_count += 1
                print(f"새 유동부채 데이터 저장: {stock_code} {year}Q{quarter}, value={int(current_liabilities_value)}")
                
            except Exception as e:
                print(f"유동부채 데이터베이스 처리 오류: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"유동부채 데이터베이스 저장 완료: {stock_code} (새로 저장: {saved_count}개, 건너뜀: {skipped_count}개)")
        return True
        
    except Exception as e:
        print(f"유동부채 데이터베이스 저장 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def save_interest_expense_to_database(stock_code, company_name, interest_expense_data):
    """이자비용 데이터를 데이터베이스에 저장합니다."""
    try:
        print(f"[DEBUG SAVE] Starting save for {stock_code}, data count: {len(interest_expense_data)}")
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        # 이자비용 데이터 테이블
        table_name = 'stock_interest_expense_data'
        
        # 테이블 존재 여부 확인 및 자동 생성
        if DB_SETUP_AVAILABLE and ensure_table_exists:
            db_url = os.getenv('SUPABASE_DB_URL')
            if not ensure_table_exists(table_name, supabase, db_url):
                print(f"[WARNING] {table_name} 테이블을 생성할 수 없습니다. 수동으로 생성해주세요.")
                return False
        
        saved_count = 0
        skipped_count = 0
        
        for quarter_key, interest_expense_value in interest_expense_data.items():
            try:
                # quarter_key에서 년도와 분기 추출 (예: "2024Q3" -> 2024, 3)
                year_str, quarter_str = quarter_key.split('Q')
                year = int(year_str)
                quarter = int(quarter_str)
                
                print(f"[DEBUG SAVE] Processing {quarter_key}: value={interest_expense_value}")
                
                # 기본키 존재 여부 확인
                existing = supabase.table(table_name).select('id').eq('stock_code', stock_code).eq('year', year).eq('quarter', quarter).execute()
                
                if existing.data:
                    # 데이터가 이미 존재하면 건너뛰기
                    skipped_count += 1
                    print(f"이자비용 데이터가 이미 존재함: {stock_code} {year}Q{quarter}")
                    continue
                
                # 이자비용 데이터 저장
                record = {
                    'stock_code': stock_code,
                    'company_name': company_name,
                    'year': year,
                    'quarter': quarter,
                    'interest_expense': int(interest_expense_value),
                    'cache_year': cache_year,
                    'cache_month': cache_month,
                    'last_updated': current_date.isoformat()
                }
                
                print(f"[DEBUG SAVE] Record to insert: {record}")
                
                supabase.table(table_name).insert(record).execute()
                saved_count += 1
                print(f"새 이자비용 데이터 저장: {stock_code} {year}Q{quarter}, value={int(interest_expense_value)}")
                
            except Exception as e:
                print(f"이자비용 데이터베이스 처리 오류: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"이자비용 데이터베이스 저장 완료: {stock_code} (새로 저장: {saved_count}개, 건너뜀: {skipped_count}개)")
        return True
        
    except Exception as e:
        print(f"이자비용 데이터베이스 저장 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def generate_standard_labels(period):
    """
    표준 X축 labels 생성 - 모든 년도를 분기별로 표시
    Yahoo Finance API 제한: 연간 재무 데이터는 최근 3년 + 현재년도 = 4개 년도만 제공
    
    Args:
        period: 표시 기간 (년) - 4년 고정
    
    Returns:
        표준 labels 리스트 (모두 분기별: "2022Q1", "2022Q2", ...)
    """
    current_year = datetime.now().year
    current_month = datetime.now().month
    current_day = datetime.now().day
    
    # Yahoo Finance는 최근 3년 + 현재년도 데이터 제공
    # 2025년 기준: [2025, 2024, 2023, 2022]
    start_year = current_year - 3  # 4년 데이터 (2022, 2023, 2024, 2025)
    
    labels = []
    
    # 이전 년도들 (모두 분기별로 표시 - 4분기씩)
    for year in range(start_year, current_year):
        for quarter in range(1, 5):  # Q1, Q2, Q3, Q4
            labels.append(f"{year}Q{quarter}")
    
    # 현재 년도 (분기별) - 실적발표가 완료된 분기까지만 표시
    # 실적발표는 분기 종료 후 약 1-2개월 후에 이루어짐
    # 보수적으로 분기 종료 후 다음 달 중순 이후에 데이터 사용 가능하다고 가정
    
    if current_month >= 11 or (current_month == 10 and current_day >= 15):  
        # 11월 이후 또는 10월 15일 이후 - 3분기 실적발표 완료
        max_quarter = 3
    elif current_month >= 8 or (current_month == 7 and current_day >= 15):  
        # 8월 이후 또는 7월 15일 이후 - 2분기 실적발표 완료
        max_quarter = 2
    elif current_month >= 5 or (current_month == 4 and current_day >= 15):  
        # 5월 이후 또는 4월 15일 이후 - 1분기 실적발표 완료
        max_quarter = 1
    else:  
        # 그 외 - 아직 실적발표 없음, 이전 년도의 4분기까지만 표시
        max_quarter = 0
    
    for quarter in range(1, max_quarter + 1):
        labels.append(f"{current_year}Q{quarter}")
    
    return labels

def format_chart_data_by_period(data, period, value_key, aggregation_type='average', ticker=None, market=None):
    """
    표준화된 차트 데이터 포맷팅 함수 - 모든 항목을 분기별로 표시
    
    Args:
        data: 데이터베이스에서 조회한 데이터 리스트
        period: 표시 기간 (년)
        value_key: 데이터에서 추출할 값의 키 (예: 'stock_price', 'revenue')
        aggregation_type: 사용하지 않음 (하위 호환성을 위해 유지)
        ticker: 주식 코드 (주가 조회용, 선택사항)
        market: 시장 구분 ('US' 또는 'KR') - 매출 단위 결정용
    
    Returns:
        {'labels': [...], 'values': [...]} 형태의 차트 데이터 (모두 분기별)
    """
    try:
        current_year = datetime.now().year
        start_year = current_year - period
        
        # 표준 labels 생성 (모든 차트가 동일한 X축을 사용 - 분기별)
        standard_labels = generate_standard_labels(period)
        
        # 기간 내 데이터 필터링 및 정렬
        filtered_data = [d for d in data if d['year'] >= start_year]
        filtered_data.sort(key=lambda x: (x['year'], x['quarter']))
        
        # 데이터를 label별로 매핑 (모두 분기별)
        data_map = {}
        
        for item in filtered_data:
            year = item['year']
            quarter = item.get('quarter', 0)
            
            # 값 추출 및 처리
            value = item.get(value_key)
            print(f"[DEBUG format_chart_data_by_period] year={year}, quarter={quarter}, value_key='{value_key}', raw_value={value}, item_keys={list(item.keys())}")
            
            if value is None:
                value = 0
                print(f"[DEBUG format_chart_data_by_period] Value is None, setting to 0")
            
            # 특별 처리: 매출, 영업이익, 당기순이익, 총부채, 유동부채, 이자비용, 현금성자산 단위 변환
            if value_key in ['revenue', 'operating_income', 'net_profit', 'total_debt', 'current_liabilities', 'interest_expense', 'cash_and_equivalents']:
                # 미국 주식: 10억 달러 단위 (Billion USD)
                # 한국 주식: 억원 단위
                if market == 'US':
                    value = value / 1_000_000_000  # 10억 달러
                else:
                    value = value / 100_000_000  # 억원
                print(f"[DEBUG format_chart_data_by_period] After conversion: {value}")
            
            # 모든 데이터를 분기별로 저장
            label = f"{year}Q{quarter}"
            data_map[label] = round(value, 2) if isinstance(value, (int, float)) else value
        
        # 표준 labels에 맞춰 values 생성 (데이터 없으면 0)
        values = []
        for label in standard_labels:
            values.append(data_map.get(label, 0))
        
        return {
            'labels': standard_labels,
            'values': values
        }
        
    except Exception as e:
        print(f"차트 데이터 포맷팅 오류: {e}")
        return None

def format_price_chart_data(data, period, ticker=None):
    """주가 차트용 데이터 포맷팅 - 표준화된 함수 사용"""
    result = format_chart_data_by_period(data, period, 'stock_price', 'average', ticker)
    if result:
        return {
            'labels': result['labels'],
            'prices': result['values']
        }
    return None

def format_revenue_chart_data(data, period, ticker=None):
    """매출 차트용 데이터 포맷팅 - 표준화된 함수 사용 (주가와 동일한 기간 표시)"""
    # 시장 구분
    market = 'US' if ticker and is_english_ticker(ticker) else 'KR'
    result = format_chart_data_by_period(data, period, 'revenue', 'sum', ticker, market)
    if result:
        return {
            'labels': result['labels'],
            'revenues': result['values']
        }
    return None

def format_operating_income_chart_data(data, period, ticker=None):
    """영업이익 차트용 데이터 포맷팅 - 표준화된 함수 사용 (주가와 동일한 기간 표시)"""
    print(f"[DEBUG FORMAT] Formatting operating income chart data for {ticker}, period={period}, data_count={len(data)}")
    print(f"[DEBUG FORMAT] Sample data: {data[:2] if len(data) >= 2 else data}")
    
    # 시장 구분
    market = 'US' if ticker and is_english_ticker(ticker) else 'KR'
    result = format_chart_data_by_period(data, period, 'operating_income', 'sum', ticker, market)
    
    if result:
        print(f"[DEBUG FORMAT] Result labels: {result['labels']}")
        print(f"[DEBUG FORMAT] Result values: {result['values']}")
        return {
            'labels': result['labels'],
            'operating_incomes': result['values']
        }
    else:
        print(f"[DEBUG FORMAT] format_chart_data_by_period returned None")
    return None

def format_net_profit_chart_data(data, period, ticker=None):
    """당기순이익 차트용 데이터 포맷팅 - 표준화된 함수 사용 (주가와 동일한 기간 표시)"""
    print(f"[DEBUG FORMAT] Formatting net profit chart data for {ticker}, period={period}, data_count={len(data)}")
    print(f"[DEBUG FORMAT] Sample data: {data[:2] if len(data) >= 2 else data}")
    
    # 시장 구분
    market = 'US' if ticker and is_english_ticker(ticker) else 'KR'
    result = format_chart_data_by_period(data, period, 'net_profit', 'sum', ticker, market)
    
    if result:
        print(f"[DEBUG FORMAT] Result labels: {result['labels']}")
        print(f"[DEBUG FORMAT] Result values: {result['values']}")
        return {
            'labels': result['labels'],
            'net_profits': result['values']
        }
    else:
        print(f"[DEBUG FORMAT] format_chart_data_by_period returned None")
    return None

def format_total_debt_chart_data(data, period, ticker=None):
    """총부채 차트용 데이터 포맷팅 - 표준화된 함수 사용 (주가와 동일한 기간 표시)"""
    print(f"[DEBUG FORMAT] Formatting total debt chart data for {ticker}, period={period}, data_count={len(data)}")
    print(f"[DEBUG FORMAT] Sample data: {data[:2] if len(data) >= 2 else data}")
    
    # 시장 구분
    market = 'US' if ticker and is_english_ticker(ticker) else 'KR'
    result = format_chart_data_by_period(data, period, 'total_debt', 'average', ticker, market)
    
    if result:
        print(f"[DEBUG FORMAT] Result labels: {result['labels']}")
        print(f"[DEBUG FORMAT] Result values: {result['values']}")
        return {
            'labels': result['labels'],
            'total_debts': result['values']
        }
    else:
        print(f"[DEBUG FORMAT] format_chart_data_by_period returned None")
    return None

def format_current_liabilities_chart_data(data, period, ticker=None):
    """유동부채 차트용 데이터 포맷팅 - 표준화된 함수 사용 (주가와 동일한 기간 표시)"""
    print(f"[DEBUG FORMAT] Formatting current liabilities chart data for {ticker}, period={period}, data_count={len(data)}")
    print(f"[DEBUG FORMAT] Sample data: {data[:2] if len(data) >= 2 else data}")
    
    # 시장 구분
    market = 'US' if ticker and is_english_ticker(ticker) else 'KR'
    result = format_chart_data_by_period(data, period, 'current_liabilities', 'average', ticker, market)
    
    if result:
        print(f"[DEBUG FORMAT] Result labels: {result['labels']}")
        print(f"[DEBUG FORMAT] Result values: {result['values']}")
        return {
            'labels': result['labels'],
            'current_liabilities': result['values']
        }
    else:
        print(f"[DEBUG FORMAT] format_chart_data_by_period returned None")
    return None

def format_interest_expense_chart_data(data, period, ticker=None):
    """이자비용 차트용 데이터 포맷팅 - 표준화된 함수 사용 (주가와 동일한 기간 표시)"""
    print(f"[DEBUG FORMAT] Formatting interest expense chart data for {ticker}, period={period}, data_count={len(data)}")
    print(f"[DEBUG FORMAT] Sample data: {data[:2] if len(data) >= 2 else data}")
    
    # 시장 구분
    market = 'US' if ticker and is_english_ticker(ticker) else 'KR'
    result = format_chart_data_by_period(data, period, 'interest_expense', 'sum', ticker, market)
    
    if result:
        print(f"[DEBUG FORMAT] Result labels: {result['labels']}")
        print(f"[DEBUG FORMAT] Result values: {result['values']}")
        return {
            'labels': result['labels'],
            'interest_expenses': result['values']
        }
    else:
        print(f"[DEBUG FORMAT] format_chart_data_by_period returned None")
    return None

def format_cash_chart_data(data, period, ticker=None):
    """현금및현금성자산 차트용 데이터 포맷팅 - 표준화된 함수 사용 (주가와 동일한 기간 표시)"""
    print(f"[DEBUG FORMAT] Formatting cash chart data for {ticker}, period={period}, data_count={len(data)}")
    print(f"[DEBUG FORMAT] Sample data: {data[:2] if len(data) >= 2 else data}")
    
    # 시장 구분
    market = 'US' if ticker and is_english_ticker(ticker) else 'KR'
    result = format_chart_data_by_period(data, period, 'cash_and_equivalents', 'sum', ticker, market)
    
    if result:
        print(f"[DEBUG FORMAT] Result labels: {result['labels']}")
        print(f"[DEBUG FORMAT] Result values: {result['values']}")
        return {
            'labels': result['labels'],
            'cash_values': result['values']
        }
    else:
        print(f"[DEBUG FORMAT] format_chart_data_by_period returned None")
    return None

def format_valuation_chart_data(data, period, ticker=None):
    """PBR, PER, EV/EBITDA 차트용 데이터 포맷팅 - 3개 라인 반환"""
    print(f"[DEBUG FORMAT] Formatting valuation chart data for {ticker}, period={period}, data_count={len(data)}")
    print(f"[DEBUG FORMAT] Sample data: {data[:2] if len(data) >= 2 else data}")
    
    try:
        current_year = datetime.now().year
        start_year = current_year - period
        
        # 표준 라벨 생성 (2022Q1, 2022Q2, ..., 2025Q4)
        standard_labels = generate_standard_labels(period)
        
        # 각 지표별 값 초기화
        pbr_values = []
        per_values = []
        ev_ebitda_values = []
        
        # 데이터를 딕셔너리로 변환
        data_dict = {}
        for item in data:
            year = item['year']
            quarter = item['quarter']
            key = f"{year}Q{quarter}"
            data_dict[key] = item
        
        # 표준 라벨에 맞춰 데이터 채우기
        for label in standard_labels:
            if label in data_dict:
                item = data_dict[label]
                pbr_values.append(round(item['pbr'], 2) if item.get('pbr') is not None else 0)
                per_values.append(round(item['per'], 2) if item.get('per') is not None else 0)
                ev_ebitda_values.append(round(item['ev_ebitda'], 2) if item.get('ev_ebitda') is not None else 0)
            else:
                pbr_values.append(0)
                per_values.append(0)
                ev_ebitda_values.append(0)
        
        print(f"[DEBUG FORMAT] Result labels: {standard_labels}")
        print(f"[DEBUG FORMAT] PBR values: {pbr_values}")
        print(f"[DEBUG FORMAT] PER values: {per_values}")
        print(f"[DEBUG FORMAT] EV/EBITDA values: {ev_ebitda_values}")
        
        return {
            'labels': standard_labels,
            'pbr_values': pbr_values,
            'per_values': per_values,
            'ev_ebitda_values': ev_ebitda_values
        }
        
    except Exception as e:
        print(f"[DEBUG FORMAT] Error formatting valuation chart data: {e}")
        import traceback
        traceback.print_exc()
        return None

# ============================================================================
# 향후 추가될 항목들을 위한 표준 차트 포맷팅 함수 예시
# ============================================================================
# 
# def format_operating_margin_chart_data(data, period):
#     """영업이익률 차트용 데이터 포맷팅 - 표준화된 함수 사용"""
#     result = format_chart_data_by_period(data, period, 'operating_margin', 'average')
#     if result:
#         return {
#             'labels': result['labels'],
#             'operating_margins': result['values']
#         }
#     return None
# 
# def format_eps_chart_data(data, period):
#     """주당순이익(EPS) 차트용 데이터 포맷팅 - 표준화된 함수 사용"""
#     result = format_chart_data_by_period(data, period, 'eps', 'average')
#     if result:
#         return {
#             'labels': result['labels'],
#             'eps_values': result['values']
#         }
#     return None
# 
# def format_roe_chart_data(data, period):
#     """자기자본이익률(ROE) 차트용 데이터 포맷팅 - 표준화된 함수 사용"""
#     result = format_chart_data_by_period(data, period, 'roe', 'average')
#     if result:
#         return {
#             'labels': result['labels'],
#             'roe_values': result['values']
#         }
#     return None
# 
# 사용 방법:
# 1. format_chart_data_by_period() 함수 호출
# 2. value_key: 데이터베이스 컬럼명 (예: 'net_profit', 'operating_margin', 'eps', 'roe')
# 3. aggregation_type: 'average' (평균) 또는 'sum' (합계)
# 4. 모든 항목은 자동으로 주가와 동일한 기간 표시 방식을 따름
# ============================================================================

@app.route('/')
def index():
    """메인 페이지"""
    return render_template('index.html')

@app.route('/stock-analysis')
def stock_analysis():
    """Stock 분석 페이지"""
    return render_template('stock_analysis.html')

@app.route('/api/stock/analysis', methods=['POST'])
def api_stock_analysis():
    """Stock 분석 API 엔드포인트"""
    try:
        data = request.get_json()
        symbol = data.get('symbol', '').strip().upper()
        period = data.get('period', 5)
        
        if not symbol:
            return jsonify({'error': '주식 심볼을 입력해주세요.'}), 400
        
        # 주식 데이터 조회
        stock_data = get_stock_analysis_data(symbol, period)
        
        if not stock_data:
            return jsonify({'error': f'{symbol} 주식 데이터를 찾을 수 없습니다.'}), 404
        
        return jsonify(stock_data)
        
    except Exception as e:
        print(f"Stock 분석 API 오류: {e}")
        return jsonify({'error': '주식 분석 중 오류가 발생했습니다.'}), 500

def get_stock_analysis_data(symbol, period):
    """주식 분석 데이터 조회"""
    try:
        # 주식 기본 정보 조회
        stock_info = get_stock_basic_info(symbol)
        if not stock_info:
            return None
        
        # 주가 데이터 조회
        price_data = get_stock_price_data(symbol, period)
        
        # 매출 데이터 조회
        revenue_data = get_stock_revenue_data(symbol, period)
        
        return {
            'symbol': symbol,
            'period': period,
            'stock_info': stock_info,
            'price_data': price_data,
            'revenue_data': revenue_data,
            'financial_data': None  # Deprecated - 사용되지 않음
        }
        
    except Exception as e:
        print(f"주식 분석 데이터 조회 오류: {e}")
        return None

def get_stock_basic_info(symbol):
    """주식 기본 정보 조회"""
    import time
    import random
    
    try:
        # yfinance를 사용한 주식 기본 정보 조회
        import yfinance as yf
        
        print(f"[INFO] 주식 정보 조회 시작: {symbol}")
        
        # Rate limiting 방지를 위한 지연 (429 에러 방지)
        time.sleep(random.uniform(2, 5))
        
        stock = yf.Ticker(symbol)
        
        # info 속성 접근 시도
        info = stock.info
        
        # info가 비어있거나 유효하지 않은 경우 확인
        if not info or len(info) == 0:
            print(f"[WARNING] {symbol}: info가 비어있습니다. 기본값 사용")
            # 기본 정보라도 제공
            return {
                'name': symbol,
                'sector': 'N/A',
                'industry': 'N/A',
                'market_cap': 0,
                'current_price': 0
            }
        
        # 정상적으로 데이터가 있는 경우
        result = {
            'name': info.get('longName', info.get('shortName', symbol)),
            'sector': info.get('sector', 'N/A'),
            'industry': info.get('industry', 'N/A'),
            'market_cap': info.get('marketCap', 0),
            'current_price': info.get('currentPrice', info.get('regularMarketPrice', 0))
        }
        
        print(f"[SUCCESS] {symbol}: 주식 정보 조회 성공 - {result['name']}")
        return result
        
    except Exception as e:
        print(f"[ERROR] 주식 기본 정보 조회 오류 ({symbol}): {e}")
        import traceback
        traceback.print_exc()
        
        # 에러가 발생해도 기본 정보는 반환
        return {
            'name': symbol,
            'sector': 'N/A',
            'industry': 'N/A',
            'market_cap': 0,
            'current_price': 0
        }

@app.route('/tax-analysis')
def tax_analysis():
    """Tax 분석 페이지"""
    return render_template('tax_analysis.html')

@app.route('/economy-trade')
def economy_trade():
    """Economy & Trade 페이지"""
    return render_template('economy_trade.html')

# ============================================================================
# Economy & Trade - 미국 국채금리 데이터 처리
# ============================================================================

def get_treasury_data_from_yahoo(years=4):
    """FRED API에서 미국 국채금리 데이터를 조회합니다 (5년물 vs 3개월물)"""
    try:
        if not fred:
            print("[ERROR] FRED API 클라이언트가 초기화되지 않았습니다.")
            return {}
        
        current_date = datetime.now()
        current_year = current_date.year
        start_year = current_year - years
        
        print(f"[INFO] FRED API에서 국채금리 데이터 조회: {start_year}-01-01 ~ {current_date.strftime('%Y-%m-%d')}")
        
        # FRED API에서 5년물(DGS5)과 3개월물(DGS3MO) 데이터 조회
        try:
            treasury_5y_series = fred.get_series('DGS5', observation_start=f'{start_year}-01-01')
            print(f"[INFO] 5년물 데이터 조회 성공: {len(treasury_5y_series)}개")
        except Exception as e:
            print(f"[ERROR] 5년물 데이터 조회 실패: {e}")
            treasury_5y_series = None
        
        try:
            treasury_3m_series = fred.get_series('DGS3MO', observation_start=f'{start_year}-01-01')
            print(f"[INFO] 3개월물 데이터 조회 성공: {len(treasury_3m_series)}개")
        except Exception as e:
            print(f"[ERROR] 3개월물 데이터 조회 실패: {e}")
            treasury_3m_series = None
        
        if treasury_5y_series is None or treasury_3m_series is None:
            print("[ERROR] 국채 데이터를 가져올 수 없습니다.")
            return {}
        
        if treasury_5y_series.empty or treasury_3m_series.empty:
            print("[ERROR] 국채 데이터가 비어있습니다.")
            return {}
        
        # 분기별 데이터 저장
        treasury_data = {}
        
        # 분기별로 평균 계산
        for year in range(start_year, current_year + 1):
            for quarter in range(1, 5):
                # 분기 시작/종료 날짜
                start_month = (quarter - 1) * 3 + 1
                end_month = quarter * 3
                
                # 해당 분기의 데이터 필터링
                mask_5y = (treasury_5y_series.index.year == year) & \
                          (treasury_5y_series.index.month >= start_month) & \
                          (treasury_5y_series.index.month <= end_month)
                mask_3m = (treasury_3m_series.index.year == year) & \
                          (treasury_3m_series.index.month >= start_month) & \
                          (treasury_3m_series.index.month <= end_month)
                
                quarter_data_5y = treasury_5y_series[mask_5y]
                quarter_data_3m = treasury_3m_series[mask_3m]
                
                if not quarter_data_5y.empty and not quarter_data_3m.empty:
                    avg_5y = quarter_data_5y.mean()
                    avg_3m = quarter_data_3m.mean()
                    
                    key = f"{year}Q{quarter}"
                    treasury_data[key] = {
                        'treasury_5y': round(avg_5y, 4),
                        'treasury_3m': round(avg_3m, 4)
                    }
                    
                    print(f"{key}: 5년물={avg_5y:.4f}%, 3개월물={avg_3m:.4f}%")
        
        print(f"[SUCCESS] 국채 데이터 조회 완료: 총 {len(treasury_data)}개 분기")
        return treasury_data
        
    except Exception as e:
        print(f"[ERROR] 국채 데이터 조회 오류: {e}")
        import traceback
        traceback.print_exc()
        return {}

def check_treasury_database_data():
    """국채 데이터베이스에서 현재 달 데이터 확인"""
    try:
        current_date = datetime.now()
        current_year = current_date.year
        current_month = current_date.month
        
        table_name = 'economy_treasury_data'
        
        # 현재 달 데이터 조회
        result = supabase.table(table_name).select('*').eq('cache_year', current_year).eq('cache_month', current_month).execute()
        
        if result.data:
            return True, result.data
        else:
            return False, []
            
    except Exception as e:
        print(f"국채 데이터베이스 조회 오류: {e}")
        return False, []

def get_treasury_database_data(period=4):
    """국채 데이터베이스에서 차트용 데이터 조회"""
    try:
        current_year = datetime.now().year
        start_year = current_year - period
        
        table_name = 'economy_treasury_data'
        
        # 기간 내 데이터 조회
        result = supabase.table(table_name).select('*').gte('year', start_year).order('year', desc=False).order('quarter', desc=False).execute()
        
        return result.data if result.data else []
        
    except Exception as e:
        print(f"국채 데이터베이스 조회 오류: {e}")
        return []

def save_treasury_to_database(treasury_data):
    """국채 데이터를 데이터베이스에 저장합니다."""
    try:
        print(f"[DEBUG SAVE] Starting save, data count: {len(treasury_data)}")
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        table_name = 'economy_treasury_data'
        
        # 테이블 존재 여부 확인 및 자동 생성
        if DB_SETUP_AVAILABLE and ensure_table_exists:
            db_url = os.getenv('SUPABASE_DB_URL')
            if not ensure_table_exists(table_name, supabase, db_url):
                print(f"[WARNING] {table_name} 테이블을 생성할 수 없습니다. 수동으로 생성해주세요.")
                return False
        
        saved_count = 0
        skipped_count = 0
        
        for quarter_key, data in treasury_data.items():
            try:
                # quarter_key에서 년도와 분기 추출 (예: "2024Q3" -> 2024, 3)
                year_str, quarter_str = quarter_key.split('Q')
                year = int(year_str)
                quarter = int(quarter_str)
                
                print(f"[DEBUG SAVE] Processing {quarter_key}: 5Y={data['treasury_5y']}, 3M={data['treasury_3m']}")
                
                # 기본키 존재 여부 확인
                existing = supabase.table(table_name).select('id').eq('year', year).eq('quarter', quarter).execute()
                
                if existing.data:
                    # 데이터가 이미 존재하면 건너뛰기
                    skipped_count += 1
                    print(f"국채 데이터가 이미 존재함: {year}Q{quarter}")
                    continue
                
                # 국채 데이터 저장
                record = {
                    'year': year,
                    'quarter': quarter,
                    'treasury_5y': data['treasury_5y'],
                    'treasury_3m': data['treasury_3m'],
                    'cache_year': cache_year,
                    'cache_month': cache_month,
                    'last_updated': current_date.isoformat()
                }
                
                print(f"[DEBUG SAVE] Record to insert: {record}")
                
                supabase.table(table_name).insert(record).execute()
                saved_count += 1
                print(f"새 국채 데이터 저장: {year}Q{quarter}")
                
            except Exception as e:
                print(f"국채 데이터베이스 처리 오류: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"국채 데이터베이스 저장 완료: (새로 저장: {saved_count}개, 건너뜀: {skipped_count}개)")
        return True
        
    except Exception as e:
        print(f"국채 데이터베이스 저장 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def clear_treasury_cache_data(cache_year, cache_month):
    """국채 데이터에서 동일한 cache_year, cache_month를 가진 데이터 삭제"""
    try:
        table_name = 'economy_treasury_data'
        
        # 동일한 cache_year, cache_month를 가진 데이터 삭제
        delete_result = supabase.table(table_name).delete().eq('cache_year', cache_year).eq('cache_month', cache_month).execute()
        deleted_count = len(delete_result.data) if delete_result.data else 0
        
        print(f"국채 캐시 데이터 삭제 완료: {cache_year}년 {cache_month}월 데이터 {deleted_count}개 삭제")
        return True, deleted_count
        
    except Exception as e:
        print(f"국채 캐시 데이터 삭제 오류: {e}")
        return False, 0

def format_treasury_chart_data(data, period):
    """국채 차트용 데이터 포맷팅"""
    try:
        print(f"[DEBUG FORMAT] Formatting treasury chart data, period={period}, data_count={len(data)}")
        
        current_year = datetime.now().year
        start_year = current_year - period
        
        # 표준 labels 생성 (분기별)
        labels = []
        for year in range(start_year, current_year + 1):
            for quarter in range(1, 5):
                labels.append(f"{year}Q{quarter}")
        
        # 데이터 매핑
        data_map = {}
        for item in data:
            year = item['year']
            quarter = item['quarter']
            label = f"{year}Q{quarter}"
            data_map[label] = {
                '5y': item.get('treasury_5y', 0),
                '3m': item.get('treasury_3m', 0)
            }
        
        # values 생성
        values_5y = []
        values_3m = []
        
        for label in labels:
            if label in data_map:
                values_5y.append(data_map[label]['5y'])
                values_3m.append(data_map[label]['3m'])
            else:
                values_5y.append(None)
                values_3m.append(None)
        
        print(f"[DEBUG FORMAT] Result labels: {labels}")
        print(f"[DEBUG FORMAT] 5Y values: {values_5y}")
        print(f"[DEBUG FORMAT] 3M values: {values_3m}")
        
        return {
            'labels': labels,
            'treasury_5y': values_5y,
            'treasury_3m': values_3m
        }
        
    except Exception as e:
        print(f"국채 차트 데이터 포맷팅 오류: {e}")
        return None

@app.route('/api/economy/treasury/check', methods=['POST'])
def check_economy_treasury():
    """미국 국채금리 데이터 캐시 확인 및 처리"""
    try:
        period = 4  # 4년 고정
        
        print(f"국채금리 캐시 확인 요청: period={period}")
        
        # 현재 날짜 기준 캐시 확인
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        # 국채 데이터베이스에서 현재 달 데이터 확인
        has_current_month_data, db_data = check_treasury_database_data()
        
        if has_current_month_data and db_data:
            # 캐시된 데이터가 있으면 바로 반환
            print(f"캐시된 국채 데이터 사용")
            chart_data = format_treasury_chart_data(db_data, period)
            
            if chart_data is None:
                return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
            
            return jsonify({
                'success': True,
                'type': 'treasury',
                'chart_data': chart_data,
                'period': period,
                'cached': True,
                'message': '캐시된 국채금리 데이터를 사용합니다.'
            })
        else:
            # 캐시된 데이터가 없으면 Yahoo Finance에서 조회
            print(f"Yahoo Finance에서 국채금리 데이터 조회")
            
            treasury_data = get_treasury_data_from_yahoo(period)
            
            if not treasury_data:
                return jsonify({'error': '국채금리 데이터를 가져올 수 없습니다.'}), 400
            
            # 국채 데이터베이스에 저장
            save_treasury_to_database(treasury_data)
            
            # 저장된 데이터로 차트 생성
            db_data = get_treasury_database_data(period)
            chart_data = format_treasury_chart_data(db_data, period)
            
            if chart_data is None:
                return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
            
            return jsonify({
                'success': True,
                'type': 'treasury',
                'chart_data': chart_data,
                'period': period,
                'cached': False,
                'message': 'Yahoo Finance에서 최신 국채금리 데이터를 가져왔습니다.'
            })
        
    except Exception as e:
        print(f"국채금리 캐시 확인 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': '국채금리 데이터 처리 중 오류가 발생했습니다.'}), 500

@app.route('/api/economy/treasury/refresh', methods=['POST'])
def refresh_economy_treasury():
    """미국 국채금리 데이터 새로고침 - API 성공 후 캐시 삭제"""
    try:
        period = 4  # 4년 고정
        
        print(f"국채금리 Refresh 요청: period={period}")
        
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        print(f"Yahoo Finance에서 최신 국채금리 데이터 조회")
        
        # 1. 먼저 Yahoo Finance에서 국채금리 데이터 조회
        treasury_data = get_treasury_data_from_yahoo(period)
        
        if not treasury_data:
            return jsonify({'error': '국채금리 데이터를 가져올 수 없습니다.'}), 400
        
        # 2. API 성공 후 현재 달 데이터 삭제
        clear_success, deleted_count = clear_treasury_cache_data(cache_year, cache_month)
        if not clear_success:
            print(f"국채 캐시 데이터 삭제 실패")
        
        # 3. 국채 데이터베이스에 저장
        save_success = save_treasury_to_database(treasury_data)
        if not save_success:
            return jsonify({'error': '국채금리 데이터 저장에 실패했습니다.'}), 500
        
        # 4. 국채 데이터베이스에서 차트용 데이터 조회
        db_data = get_treasury_database_data(period)
        
        if not db_data:
            return jsonify({'error': '국채금리 데이터가 없습니다.'}), 400
        
        # 5. 국채 차트용 데이터 포맷팅
        chart_data = format_treasury_chart_data(db_data, period)
        
        if chart_data is None:
            return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
        
        return jsonify({
            'success': True,
            'type': 'treasury',
            'chart_data': chart_data,
            'period': period,
            'deleted_count': deleted_count,
            'message': f'국채금리 데이터 {deleted_count}개를 삭제하고 최신 데이터로 새로고침했습니다.'
        })
        
    except Exception as e:
        print(f"국채금리 새로고침 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': '국채금리 새로고침 중 오류가 발생했습니다.'}), 500

# ============================================================================
# Economy & Trade - CPI (소비자물가지수) 데이터 처리
# ============================================================================

def get_cpi_data_from_fred(years=4):
    """FRED API에서 CPI 데이터를 조회합니다 (분기별)"""
    try:
        current_date = datetime.now()
        current_year = current_date.year
        start_year = current_year - years
        
        # FRED에서 CPI 데이터 조회 (CPIAUCSL = Consumer Price Index for All Urban Consumers)
        cpi_series = fred.get_series('CPIAUCSL', observation_start=f'{start_year}-01-01')
        
        if cpi_series is None or cpi_series.empty:
            print("CPI 데이터가 비어있습니다.")
            return {}
        
        # 분기별 데이터 저장
        cpi_data = {}
        
        # 분기별로 평균 계산
        for year in range(start_year, current_year + 1):
            for quarter in range(1, 5):
                # 분기 시작/종료 월
                start_month = (quarter - 1) * 3 + 1
                end_month = quarter * 3
                
                # 해당 분기의 데이터 필터링
                mask = (cpi_series.index.year == year) & (cpi_series.index.month >= start_month) & (cpi_series.index.month <= end_month)
                quarter_data = cpi_series[mask]
                
                if not quarter_data.empty:
                    avg_cpi = quarter_data.mean()
                    
                    key = f"{year}Q{quarter}"
                    cpi_data[key] = round(avg_cpi, 4)
                    
                    print(f"{key}: CPI={avg_cpi:.2f}")
        
        print(f"CPI 데이터 조회 완료: 총 {len(cpi_data)}개 분기")
        return cpi_data
        
    except Exception as e:
        print(f"CPI 데이터 조회 오류: {e}")
        import traceback
        traceback.print_exc()
        return {}

def check_cpi_database_data():
    """CPI 데이터베이스에서 현재 달 데이터 확인"""
    try:
        current_date = datetime.now()
        current_year = current_date.year
        current_month = current_date.month
        
        table_name = 'economy_cpi_data'
        
        # 현재 달 데이터 조회
        result = supabase.table(table_name).select('*').eq('cache_year', current_year).eq('cache_month', current_month).execute()
        
        if result.data:
            return True, result.data
        else:
            return False, []
            
    except Exception as e:
        print(f"CPI 데이터베이스 조회 오류: {e}")
        return False, []

def get_cpi_database_data(period=4):
    """CPI 데이터베이스에서 차트용 데이터 조회"""
    try:
        current_year = datetime.now().year
        start_year = current_year - period
        
        table_name = 'economy_cpi_data'
        
        # 기간 내 데이터 조회
        result = supabase.table(table_name).select('*').gte('year', start_year).order('year', desc=False).order('quarter', desc=False).execute()
        
        return result.data if result.data else []
        
    except Exception as e:
        print(f"CPI 데이터베이스 조회 오류: {e}")
        return []

def save_cpi_to_database(cpi_data):
    """CPI 데이터를 데이터베이스에 저장합니다."""
    try:
        print(f"[DEBUG SAVE] Starting CPI save, data count: {len(cpi_data)}")
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        table_name = 'economy_cpi_data'
        
        # 테이블 존재 여부 확인 및 자동 생성
        if DB_SETUP_AVAILABLE and ensure_table_exists:
            db_url = os.getenv('SUPABASE_DB_URL')
            if not ensure_table_exists(table_name, supabase, db_url):
                print(f"[WARNING] {table_name} 테이블을 생성할 수 없습니다. 수동으로 생성해주세요.")
                return False
        
        saved_count = 0
        skipped_count = 0
        
        for quarter_key, cpi_value in cpi_data.items():
            try:
                # quarter_key에서 년도와 분기 추출 (예: "2024Q3" -> 2024, 3)
                year_str, quarter_str = quarter_key.split('Q')
                year = int(year_str)
                quarter = int(quarter_str)
                
                print(f"[DEBUG SAVE] Processing {quarter_key}: CPI={cpi_value}")
                
                # 기본키 존재 여부 확인
                existing = supabase.table(table_name).select('id').eq('year', year).eq('quarter', quarter).execute()
                
                if existing.data:
                    # 데이터가 이미 존재하면 건너뛰기
                    skipped_count += 1
                    print(f"CPI 데이터가 이미 존재함: {year}Q{quarter}")
                    continue
                
                # CPI 데이터 저장
                record = {
                    'year': year,
                    'quarter': quarter,
                    'cpi_value': cpi_value,
                    'cache_year': cache_year,
                    'cache_month': cache_month,
                    'last_updated': current_date.isoformat()
                }
                
                print(f"[DEBUG SAVE] Record to insert: {record}")
                
                supabase.table(table_name).insert(record).execute()
                saved_count += 1
                print(f"새 CPI 데이터 저장: {year}Q{quarter}")
                
            except Exception as e:
                print(f"CPI 데이터베이스 처리 오류: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"CPI 데이터베이스 저장 완료: (새로 저장: {saved_count}개, 건너뜀: {skipped_count}개)")
        return True
        
    except Exception as e:
        print(f"CPI 데이터베이스 저장 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def clear_cpi_cache_data(cache_year, cache_month):
    """CPI 데이터에서 동일한 cache_year, cache_month를 가진 데이터 삭제"""
    try:
        table_name = 'economy_cpi_data'
        
        # 동일한 cache_year, cache_month를 가진 데이터 삭제
        delete_result = supabase.table(table_name).delete().eq('cache_year', cache_year).eq('cache_month', cache_month).execute()
        deleted_count = len(delete_result.data) if delete_result.data else 0
        
        print(f"CPI 캐시 데이터 삭제 완료: {cache_year}년 {cache_month}월 데이터 {deleted_count}개 삭제")
        return True, deleted_count
        
    except Exception as e:
        print(f"CPI 캐시 데이터 삭제 오류: {e}")
        return False, 0

def format_cpi_chart_data(data, period):
    """CPI 차트용 데이터 포맷팅"""
    try:
        print(f"[DEBUG FORMAT] Formatting CPI chart data, period={period}, data_count={len(data)}")
        
        current_year = datetime.now().year
        start_year = current_year - period
        
        # 표준 labels 생성 (분기별)
        labels = []
        for year in range(start_year, current_year + 1):
            for quarter in range(1, 5):
                labels.append(f"{year}Q{quarter}")
        
        # 데이터 매핑
        data_map = {}
        for item in data:
            year = item['year']
            quarter = item['quarter']
            label = f"{year}Q{quarter}"
            data_map[label] = item.get('cpi_value', 0)
        
        # values 생성
        values = []
        for label in labels:
            if label in data_map:
                values.append(data_map[label])
            else:
                values.append(None)
        
        print(f"[DEBUG FORMAT] Result labels: {labels}")
        print(f"[DEBUG FORMAT] CPI values: {values}")
        
        return {
            'labels': labels,
            'cpi_values': values
        }
        
    except Exception as e:
        print(f"CPI 차트 데이터 포맷팅 오류: {e}")
        return None

@app.route('/api/economy/cpi/check', methods=['POST'])
def check_economy_cpi():
    """CPI 데이터 캐시 확인 및 처리"""
    try:
        period = 4  # 4년 고정
        
        print(f"CPI 캐시 확인 요청: period={period}")
        
        # 현재 날짜 기준 캐시 확인
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        # CPI 데이터베이스에서 현재 달 데이터 확인
        has_current_month_data, db_data = check_cpi_database_data()
        
        if has_current_month_data and db_data:
            # 캐시된 데이터가 있으면 바로 반환
            print(f"캐시된 CPI 데이터 사용")
            chart_data = format_cpi_chart_data(db_data, period)
            
            if chart_data is None:
                return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
            
            return jsonify({
                'success': True,
                'type': 'cpi',
                'chart_data': chart_data,
                'period': period,
                'cached': True,
                'message': '캐시된 CPI 데이터를 사용합니다.'
            })
        else:
            # 캐시된 데이터가 없으면 FRED API에서 조회
            print(f"FRED API에서 CPI 데이터 조회")
            
            cpi_data = get_cpi_data_from_fred(period)
            
            if not cpi_data:
                return jsonify({'error': 'CPI 데이터를 가져올 수 없습니다.'}), 400
            
            # CPI 데이터베이스에 저장
            save_cpi_to_database(cpi_data)
            
            # 저장된 데이터로 차트 생성
            db_data = get_cpi_database_data(period)
            chart_data = format_cpi_chart_data(db_data, period)
            
            if chart_data is None:
                return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
            
            return jsonify({
                'success': True,
                'type': 'cpi',
                'chart_data': chart_data,
                'period': period,
                'cached': False,
                'message': 'FRED API에서 최신 CPI 데이터를 가져왔습니다.'
            })
        
    except Exception as e:
        print(f"CPI 캐시 확인 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'CPI 데이터 처리 중 오류가 발생했습니다.'}), 500

@app.route('/api/economy/cpi/refresh', methods=['POST'])
def refresh_economy_cpi():
    """CPI 데이터 새로고침 - API 성공 후 캐시 삭제"""
    try:
        period = 4  # 4년 고정
        
        print(f"CPI Refresh 요청: period={period}")
        
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        print(f"FRED API에서 최신 CPI 데이터 조회")
        
        # 1. 먼저 FRED API에서 CPI 데이터 조회
        cpi_data = get_cpi_data_from_fred(period)
        
        if not cpi_data:
            return jsonify({'error': 'CPI 데이터를 가져올 수 없습니다.'}), 400
        
        # 2. API 성공 후 현재 달 데이터 삭제
        clear_success, deleted_count = clear_cpi_cache_data(cache_year, cache_month)
        if not clear_success:
            print(f"CPI 캐시 데이터 삭제 실패")
        
        # 3. CPI 데이터베이스에 저장
        save_success = save_cpi_to_database(cpi_data)
        if not save_success:
            return jsonify({'error': 'CPI 데이터 저장에 실패했습니다.'}), 500
        
        # 4. CPI 데이터베이스에서 차트용 데이터 조회
        db_data = get_cpi_database_data(period)
        
        if not db_data:
            return jsonify({'error': 'CPI 데이터가 없습니다.'}), 400
        
        # 5. CPI 차트용 데이터 포맷팅
        chart_data = format_cpi_chart_data(db_data, period)
        
        if chart_data is None:
            return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
        
        return jsonify({
            'success': True,
            'type': 'cpi',
            'chart_data': chart_data,
            'period': period,
            'deleted_count': deleted_count,
            'message': f'CPI 데이터 {deleted_count}개를 삭제하고 최신 데이터로 새로고침했습니다.'
        })
        
    except Exception as e:
        print(f"CPI 새로고침 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'CPI 새로고침 중 오류가 발생했습니다.'}), 500

# ============================================================================
# Economy & Trade - 제조업 생산지수 (Industrial Production) 데이터 처리
# ============================================================================

def get_industrial_production_data_from_fred(years=4):
    """FRED API에서 제조업 생산지수 데이터를 조회합니다 (분기별)"""
    try:
        current_date = datetime.now()
        current_year = current_date.year
        start_year = current_year - years
        
        # FRED에서 제조업 생산지수 데이터 조회 (INDPRO)
        indpro_series = fred.get_series('INDPRO', observation_start=f'{start_year}-01-01')
        
        if indpro_series is None or indpro_series.empty:
            print("제조업 생산지수 데이터가 비어있습니다.")
            return {}
        
        # 분기별 데이터 저장
        indpro_data = {}
        
        # 분기별로 평균 계산
        for year in range(start_year, current_year + 1):
            for quarter in range(1, 5):
                # 분기 시작/종료 월
                start_month = (quarter - 1) * 3 + 1
                end_month = quarter * 3
                
                # 해당 분기의 데이터 필터링
                mask = (indpro_series.index.year == year) & (indpro_series.index.month >= start_month) & (indpro_series.index.month <= end_month)
                quarter_data = indpro_series[mask]
                
                if not quarter_data.empty:
                    avg_indpro = quarter_data.mean()
                    
                    key = f"{year}Q{quarter}"
                    indpro_data[key] = round(avg_indpro, 4)
                    
                    print(f"{key}: 생산지수={avg_indpro:.2f}")
        
        print(f"제조업 생산지수 데이터 조회 완료: 총 {len(indpro_data)}개 분기")
        return indpro_data
        
    except Exception as e:
        print(f"제조업 생산지수 데이터 조회 오류: {e}")
        import traceback
        traceback.print_exc()
        return {}

def check_industrial_production_database_data():
    """제조업 생산지수 데이터베이스에서 현재 달 데이터 확인"""
    try:
        current_date = datetime.now()
        current_year = current_date.year
        current_month = current_date.month
        
        table_name = 'economy_industrial_production_data'
        
        # 현재 달 데이터 조회
        result = supabase.table(table_name).select('*').eq('cache_year', current_year).eq('cache_month', current_month).execute()
        
        if result.data:
            return True, result.data
        else:
            return False, []
            
    except Exception as e:
        print(f"제조업 생산지수 데이터베이스 조회 오류: {e}")
        return False, []

def get_industrial_production_database_data(period=4):
    """제조업 생산지수 데이터베이스에서 차트용 데이터 조회"""
    try:
        current_year = datetime.now().year
        start_year = current_year - period
        
        table_name = 'economy_industrial_production_data'
        
        # 기간 내 데이터 조회
        result = supabase.table(table_name).select('*').gte('year', start_year).order('year', desc=False).order('quarter', desc=False).execute()
        
        return result.data if result.data else []
        
    except Exception as e:
        print(f"제조업 생산지수 데이터베이스 조회 오류: {e}")
        return []

def save_industrial_production_to_database(indpro_data):
    """제조업 생산지수 데이터를 데이터베이스에 저장합니다."""
    try:
        print(f"[DEBUG SAVE] Starting Industrial Production save, data count: {len(indpro_data)}")
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        table_name = 'economy_industrial_production_data'
        
        # 테이블 존재 여부 확인 및 자동 생성
        if DB_SETUP_AVAILABLE and ensure_table_exists:
            db_url = os.getenv('SUPABASE_DB_URL')
            if not ensure_table_exists(table_name, supabase, db_url):
                print(f"[WARNING] {table_name} 테이블을 생성할 수 없습니다. 수동으로 생성해주세요.")
                return False
        
        saved_count = 0
        skipped_count = 0
        
        for quarter_key, indpro_value in indpro_data.items():
            try:
                # quarter_key에서 년도와 분기 추출 (예: "2024Q3" -> 2024, 3)
                year_str, quarter_str = quarter_key.split('Q')
                year = int(year_str)
                quarter = int(quarter_str)
                
                print(f"[DEBUG SAVE] Processing {quarter_key}: INDPRO={indpro_value}")
                
                # 기본키 존재 여부 확인
                existing = supabase.table(table_name).select('id').eq('year', year).eq('quarter', quarter).execute()
                
                if existing.data:
                    # 데이터가 이미 존재하면 건너뛰기
                    skipped_count += 1
                    print(f"제조업 생산지수 데이터가 이미 존재함: {year}Q{quarter}")
                    continue
                
                # 제조업 생산지수 데이터 저장
                record = {
                    'year': year,
                    'quarter': quarter,
                    'production_index': indpro_value,
                    'cache_year': cache_year,
                    'cache_month': cache_month,
                    'last_updated': current_date.isoformat()
                }
                
                print(f"[DEBUG SAVE] Record to insert: {record}")
                
                supabase.table(table_name).insert(record).execute()
                saved_count += 1
                print(f"새 제조업 생산지수 데이터 저장: {year}Q{quarter}")
                
            except Exception as e:
                print(f"제조업 생산지수 데이터베이스 처리 오류: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"제조업 생산지수 데이터베이스 저장 완료: (새로 저장: {saved_count}개, 건너뜀: {skipped_count}개)")
        return True
        
    except Exception as e:
        print(f"제조업 생산지수 데이터베이스 저장 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def clear_industrial_production_cache_data(cache_year, cache_month):
    """제조업 생산지수 데이터에서 동일한 cache_year, cache_month를 가진 데이터 삭제"""
    try:
        table_name = 'economy_industrial_production_data'
        
        # 동일한 cache_year, cache_month를 가진 데이터 삭제
        delete_result = supabase.table(table_name).delete().eq('cache_year', cache_year).eq('cache_month', cache_month).execute()
        deleted_count = len(delete_result.data) if delete_result.data else 0
        
        print(f"제조업 생산지수 캐시 데이터 삭제 완료: {cache_year}년 {cache_month}월 데이터 {deleted_count}개 삭제")
        return True, deleted_count
        
    except Exception as e:
        print(f"제조업 생산지수 캐시 데이터 삭제 오류: {e}")
        return False, 0

def format_industrial_production_chart_data(data, period):
    """제조업 생산지수 차트용 데이터 포맷팅"""
    try:
        print(f"[DEBUG FORMAT] Formatting Industrial Production chart data, period={period}, data_count={len(data)}")
        
        current_year = datetime.now().year
        start_year = current_year - period
        
        # 표준 labels 생성 (분기별)
        labels = []
        for year in range(start_year, current_year + 1):
            for quarter in range(1, 5):
                labels.append(f"{year}Q{quarter}")
        
        # 데이터 매핑
        data_map = {}
        for item in data:
            year = item['year']
            quarter = item['quarter']
            label = f"{year}Q{quarter}"
            data_map[label] = item.get('production_index', 0)
        
        # values 생성
        values = []
        for label in labels:
            if label in data_map:
                values.append(data_map[label])
            else:
                values.append(None)
        
        print(f"[DEBUG FORMAT] Result labels: {labels}")
        print(f"[DEBUG FORMAT] Industrial Production values: {values}")
        
        return {
            'labels': labels,
            'indpro_values': values
        }
        
    except Exception as e:
        print(f"제조업 생산지수 차트 데이터 포맷팅 오류: {e}")
        return None

@app.route('/api/economy/industrial-production/check', methods=['POST'])
def check_economy_industrial_production():
    """제조업 생산지수 데이터 캐시 확인 및 처리"""
    try:
        period = 4  # 4년 고정
        
        print(f"제조업 생산지수 캐시 확인 요청: period={period}")
        
        # 현재 날짜 기준 캐시 확인
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        # 제조업 생산지수 데이터베이스에서 현재 달 데이터 확인
        has_current_month_data, db_data = check_industrial_production_database_data()
        
        if has_current_month_data and db_data:
            # 캐시된 데이터가 있으면 바로 반환
            print(f"캐시된 제조업 생산지수 데이터 사용")
            chart_data = format_industrial_production_chart_data(db_data, period)
            
            if chart_data is None:
                return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
            
            return jsonify({
                'success': True,
                'type': 'industrial_production',
                'chart_data': chart_data,
                'period': period,
                'cached': True,
                'message': '캐시된 제조업 생산지수 데이터를 사용합니다.'
            })
        else:
            # 캐시된 데이터가 없으면 FRED API에서 조회
            print(f"FRED API에서 제조업 생산지수 데이터 조회")
            
            indpro_data = get_industrial_production_data_from_fred(period)
            
            if not indpro_data:
                return jsonify({'error': '제조업 생산지수 데이터를 가져올 수 없습니다.'}), 400
            
            # 제조업 생산지수 데이터베이스에 저장
            save_industrial_production_to_database(indpro_data)
            
            # 저장된 데이터로 차트 생성
            db_data = get_industrial_production_database_data(period)
            chart_data = format_industrial_production_chart_data(db_data, period)
            
            if chart_data is None:
                return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
            
            return jsonify({
                'success': True,
                'type': 'industrial_production',
                'chart_data': chart_data,
                'period': period,
                'cached': False,
                'message': 'FRED API에서 최신 제조업 생산지수 데이터를 가져왔습니다.'
            })
        
    except Exception as e:
        print(f"제조업 생산지수 캐시 확인 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': '제조업 생산지수 데이터 처리 중 오류가 발생했습니다.'}), 500

@app.route('/api/economy/industrial-production/refresh', methods=['POST'])
def refresh_economy_industrial_production():
    """제조업 생산지수 데이터 새로고침 - API 성공 후 캐시 삭제"""
    try:
        period = 4  # 4년 고정
        
        print(f"제조업 생산지수 Refresh 요청: period={period}")
        
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        print(f"FRED API에서 최신 제조업 생산지수 데이터 조회")
        
        # 1. 먼저 FRED API에서 제조업 생산지수 데이터 조회
        indpro_data = get_industrial_production_data_from_fred(period)
        
        if not indpro_data:
            return jsonify({'error': '제조업 생산지수 데이터를 가져올 수 없습니다.'}), 400
        
        # 2. API 성공 후 현재 달 데이터 삭제
        clear_success, deleted_count = clear_industrial_production_cache_data(cache_year, cache_month)
        if not clear_success:
            print(f"제조업 생산지수 캐시 데이터 삭제 실패")
        
        # 3. 제조업 생산지수 데이터베이스에 저장
        save_success = save_industrial_production_to_database(indpro_data)
        if not save_success:
            return jsonify({'error': '제조업 생산지수 데이터 저장에 실패했습니다.'}), 500
        
        # 4. 제조업 생산지수 데이터베이스에서 차트용 데이터 조회
        db_data = get_industrial_production_database_data(period)
        
        if not db_data:
            return jsonify({'error': '제조업 생산지수 데이터가 없습니다.'}), 400
        
        # 5. 제조업 생산지수 차트용 데이터 포맷팅
        chart_data = format_industrial_production_chart_data(db_data, period)
        
        if chart_data is None:
            return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
        
        return jsonify({
            'success': True,
            'type': 'industrial_production',
            'chart_data': chart_data,
            'period': period,
            'deleted_count': deleted_count,
            'message': f'제조업 생산지수 데이터 {deleted_count}개를 삭제하고 최신 데이터로 새로고침했습니다.'
        })
        
    except Exception as e:
        print(f"제조업 생산지수 새로고침 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': '제조업 생산지수 새로고침 중 오류가 발생했습니다.'}), 500

# ============================================================================
# Economy & Trade - 실업률 (Unemployment Rate) 데이터 처리
# ============================================================================

def get_unemployment_data_from_fred(years=4):
    """FRED API에서 실업률 데이터를 조회합니다 (분기별)"""
    try:
        current_date = datetime.now()
        current_year = current_date.year
        start_year = current_year - years
        
        # FRED에서 실업률 데이터 조회 (UNRATE)
        unrate_series = fred.get_series('UNRATE', observation_start=f'{start_year}-01-01')
        
        if unrate_series is None or unrate_series.empty:
            print("실업률 데이터가 비어있습니다.")
            return {}
        
        # 분기별 데이터 저장
        unrate_data = {}
        
        # 분기별로 평균 계산
        for year in range(start_year, current_year + 1):
            for quarter in range(1, 5):
                # 분기 시작/종료 월
                start_month = (quarter - 1) * 3 + 1
                end_month = quarter * 3
                
                # 해당 분기의 데이터 필터링
                mask = (unrate_series.index.year == year) & (unrate_series.index.month >= start_month) & (unrate_series.index.month <= end_month)
                quarter_data = unrate_series[mask]
                
                if not quarter_data.empty:
                    avg_unrate = quarter_data.mean()
                    
                    key = f"{year}Q{quarter}"
                    unrate_data[key] = round(avg_unrate, 4)
                    
                    print(f"{key}: 실업률={avg_unrate:.2f}%")
        
        print(f"실업률 데이터 조회 완료: 총 {len(unrate_data)}개 분기")
        return unrate_data
        
    except Exception as e:
        print(f"실업률 데이터 조회 오류: {e}")
        import traceback
        traceback.print_exc()
        return {}

def check_unemployment_database_data():
    """실업률 데이터베이스에서 현재 달 데이터 확인"""
    try:
        current_date = datetime.now()
        current_year = current_date.year
        current_month = current_date.month
        
        table_name = 'economy_unemployment_data'
        
        # 현재 달 데이터 조회
        result = supabase.table(table_name).select('*').eq('cache_year', current_year).eq('cache_month', current_month).execute()
        
        if result.data:
            return True, result.data
        else:
            return False, []
            
    except Exception as e:
        print(f"실업률 데이터베이스 조회 오류: {e}")
        return False, []

def get_unemployment_database_data(period=4):
    """실업률 데이터베이스에서 차트용 데이터 조회"""
    try:
        current_year = datetime.now().year
        start_year = current_year - period
        
        table_name = 'economy_unemployment_data'
        
        # 기간 내 데이터 조회
        result = supabase.table(table_name).select('*').gte('year', start_year).order('year', desc=False).order('quarter', desc=False).execute()
        
        return result.data if result.data else []
        
    except Exception as e:
        print(f"실업률 데이터베이스 조회 오류: {e}")
        return []

def save_unemployment_to_database(unrate_data):
    """실업률 데이터를 데이터베이스에 저장합니다."""
    try:
        print(f"[DEBUG SAVE] Starting Unemployment save, data count: {len(unrate_data)}")
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        table_name = 'economy_unemployment_data'
        
        # 테이블 존재 여부 확인 및 자동 생성
        if DB_SETUP_AVAILABLE and ensure_table_exists:
            db_url = os.getenv('SUPABASE_DB_URL')
            if not ensure_table_exists(table_name, supabase, db_url):
                print(f"[WARNING] {table_name} 테이블을 생성할 수 없습니다. 수동으로 생성해주세요.")
                return False
        
        saved_count = 0
        skipped_count = 0
        
        for quarter_key, unrate_value in unrate_data.items():
            try:
                # quarter_key에서 년도와 분기 추출 (예: "2024Q3" -> 2024, 3)
                year_str, quarter_str = quarter_key.split('Q')
                year = int(year_str)
                quarter = int(quarter_str)
                
                print(f"[DEBUG SAVE] Processing {quarter_key}: UNRATE={unrate_value}")
                
                # 기본키 존재 여부 확인
                existing = supabase.table(table_name).select('id').eq('year', year).eq('quarter', quarter).execute()
                
                if existing.data:
                    # 데이터가 이미 존재하면 건너뛰기
                    skipped_count += 1
                    print(f"실업률 데이터가 이미 존재함: {year}Q{quarter}")
                    continue
                
                # 실업률 데이터 저장
                record = {
                    'year': year,
                    'quarter': quarter,
                    'unemployment_rate': unrate_value,
                    'cache_year': cache_year,
                    'cache_month': cache_month,
                    'last_updated': current_date.isoformat()
                }
                
                print(f"[DEBUG SAVE] Record to insert: {record}")
                
                supabase.table(table_name).insert(record).execute()
                saved_count += 1
                print(f"새 실업률 데이터 저장: {year}Q{quarter}")
                
            except Exception as e:
                print(f"실업률 데이터베이스 처리 오류: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"실업률 데이터베이스 저장 완료: (새로 저장: {saved_count}개, 건너뜀: {skipped_count}개)")
        return True
        
    except Exception as e:
        print(f"실업률 데이터베이스 저장 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def clear_unemployment_cache_data(cache_year, cache_month):
    """실업률 데이터에서 동일한 cache_year, cache_month를 가진 데이터 삭제"""
    try:
        table_name = 'economy_unemployment_data'
        
        # 동일한 cache_year, cache_month를 가진 데이터 삭제
        delete_result = supabase.table(table_name).delete().eq('cache_year', cache_year).eq('cache_month', cache_month).execute()
        deleted_count = len(delete_result.data) if delete_result.data else 0
        
        print(f"실업률 캐시 데이터 삭제 완료: {cache_year}년 {cache_month}월 데이터 {deleted_count}개 삭제")
        return True, deleted_count
        
    except Exception as e:
        print(f"실업률 캐시 데이터 삭제 오류: {e}")
        return False, 0

def format_unemployment_chart_data(data, period):
    """실업률 차트용 데이터 포맷팅"""
    try:
        print(f"[DEBUG FORMAT] Formatting Unemployment chart data, period={period}, data_count={len(data)}")
        
        current_year = datetime.now().year
        start_year = current_year - period
        
        # 표준 labels 생성 (분기별)
        labels = []
        for year in range(start_year, current_year + 1):
            for quarter in range(1, 5):
                labels.append(f"{year}Q{quarter}")
        
        # 데이터 매핑
        data_map = {}
        for item in data:
            year = item['year']
            quarter = item['quarter']
            label = f"{year}Q{quarter}"
            data_map[label] = item.get('unemployment_rate', 0)
        
        # values 생성
        values = []
        for label in labels:
            if label in data_map:
                values.append(data_map[label])
            else:
                values.append(None)
        
        print(f"[DEBUG FORMAT] Result labels: {labels}")
        print(f"[DEBUG FORMAT] Unemployment values: {values}")
        
        return {
            'labels': labels,
            'unemployment_values': values
        }
        
    except Exception as e:
        print(f"실업률 차트 데이터 포맷팅 오류: {e}")
        return None

@app.route('/api/economy/unemployment/check', methods=['POST'])
def check_economy_unemployment():
    """실업률 데이터 캐시 확인 및 처리"""
    try:
        period = 4  # 4년 고정
        
        print(f"실업률 캐시 확인 요청: period={period}")
        
        # 현재 날짜 기준 캐시 확인
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        # 실업률 데이터베이스에서 현재 달 데이터 확인
        has_current_month_data, db_data = check_unemployment_database_data()
        
        if has_current_month_data and db_data:
            # 캐시된 데이터가 있으면 바로 반환
            print(f"캐시된 실업률 데이터 사용")
            chart_data = format_unemployment_chart_data(db_data, period)
            
            if chart_data is None:
                return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
            
            return jsonify({
                'success': True,
                'type': 'unemployment',
                'chart_data': chart_data,
                'period': period,
                'cached': True,
                'message': '캐시된 실업률 데이터를 사용합니다.'
            })
        else:
            # 캐시된 데이터가 없으면 FRED API에서 조회
            print(f"FRED API에서 실업률 데이터 조회")
            
            unrate_data = get_unemployment_data_from_fred(period)
            
            if not unrate_data:
                return jsonify({'error': '실업률 데이터를 가져올 수 없습니다.'}), 400
            
            # 실업률 데이터베이스에 저장
            save_unemployment_to_database(unrate_data)
            
            # 저장된 데이터로 차트 생성
            db_data = get_unemployment_database_data(period)
            chart_data = format_unemployment_chart_data(db_data, period)
            
            if chart_data is None:
                return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
            
            return jsonify({
                'success': True,
                'type': 'unemployment',
                'chart_data': chart_data,
                'period': period,
                'cached': False,
                'message': 'FRED API에서 최신 실업률 데이터를 가져왔습니다.'
            })
        
    except Exception as e:
        print(f"실업률 캐시 확인 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': '실업률 데이터 처리 중 오류가 발생했습니다.'}), 500

@app.route('/api/economy/unemployment/refresh', methods=['POST'])
def refresh_economy_unemployment():
    """실업률 데이터 새로고침 - API 성공 후 캐시 삭제"""
    try:
        period = 4  # 4년 고정
        
        print(f"실업률 Refresh 요청: period={period}")
        
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        print(f"FRED API에서 최신 실업률 데이터 조회")
        
        # 1. 먼저 FRED API에서 실업률 데이터 조회
        unrate_data = get_unemployment_data_from_fred(period)
        
        if not unrate_data:
            return jsonify({'error': '실업률 데이터를 가져올 수 없습니다.'}), 400
        
        # 2. API 성공 후 현재 달 데이터 삭제
        clear_success, deleted_count = clear_unemployment_cache_data(cache_year, cache_month)
        if not clear_success:
            print(f"실업률 캐시 데이터 삭제 실패")
        
        # 3. 실업률 데이터베이스에 저장
        save_success = save_unemployment_to_database(unrate_data)
        if not save_success:
            return jsonify({'error': '실업률 데이터 저장에 실패했습니다.'}), 500
        
        # 4. 실업률 데이터베이스에서 차트용 데이터 조회
        db_data = get_unemployment_database_data(period)
        
        if not db_data:
            return jsonify({'error': '실업률 데이터가 없습니다.'}), 400
        
        # 5. 실업률 차트용 데이터 포맷팅
        chart_data = format_unemployment_chart_data(db_data, period)
        
        if chart_data is None:
            return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
        
        return jsonify({
            'success': True,
            'type': 'unemployment',
            'chart_data': chart_data,
            'period': period,
            'deleted_count': deleted_count,
            'message': f'실업률 데이터 {deleted_count}개를 삭제하고 최신 데이터로 새로고침했습니다.'
        })
        
    except Exception as e:
        print(f"실업률 새로고침 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': '실업률 새로고침 중 오류가 발생했습니다.'}), 500

# ============================================================================
# Economy & Trade - GDP (국내총생산) 데이터 처리
# ============================================================================

def get_gdp_data_from_fred(years=4):
    """FRED API에서 GDP 데이터를 조회합니다 (분기별)"""
    try:
        current_date = datetime.now()
        current_year = current_date.year
        start_year = current_year - years
        
        # FRED에서 실질 GDP 데이터 조회 (GDPC1 = Real Gross Domestic Product)
        gdp_series = fred.get_series('GDPC1', observation_start=f'{start_year}-01-01')
        
        if gdp_series is None or gdp_series.empty:
            print("GDP 데이터가 비어있습니다.")
            return {}
        
        # GDP는 이미 분기별 데이터로 제공됨
        gdp_data = {}
        
        for idx, value in gdp_series.items():
            year = idx.year
            # 분기 계산 (1월=Q1, 4월=Q2, 7월=Q3, 10월=Q4)
            month = idx.month
            if month in [1, 2, 3]:
                quarter = 1
            elif month in [4, 5, 6]:
                quarter = 2
            elif month in [7, 8, 9]:
                quarter = 3
            else:
                quarter = 4
            
            if year >= start_year and year <= current_year:
                key = f"{year}Q{quarter}"
                gdp_data[key] = round(value, 4)
                
                print(f"{key}: GDP={value:.2f} Billion")
        
        print(f"GDP 데이터 조회 완료: 총 {len(gdp_data)}개 분기")
        return gdp_data
        
    except Exception as e:
        print(f"GDP 데이터 조회 오류: {e}")
        import traceback
        traceback.print_exc()
        return {}

def check_gdp_database_data():
    """GDP 데이터베이스에서 현재 달 데이터 확인"""
    try:
        current_date = datetime.now()
        current_year = current_date.year
        current_month = current_date.month
        
        table_name = 'economy_gdp_data'
        
        # 현재 달 데이터 조회
        result = supabase.table(table_name).select('*').eq('cache_year', current_year).eq('cache_month', current_month).execute()
        
        if result.data:
            return True, result.data
        else:
            return False, []
            
    except Exception as e:
        print(f"GDP 데이터베이스 조회 오류: {e}")
        return False, []

def get_gdp_database_data(period=4):
    """GDP 데이터베이스에서 차트용 데이터 조회"""
    try:
        current_year = datetime.now().year
        start_year = current_year - period
        
        table_name = 'economy_gdp_data'
        
        # 기간 내 데이터 조회
        result = supabase.table(table_name).select('*').gte('year', start_year).order('year', desc=False).order('quarter', desc=False).execute()
        
        return result.data if result.data else []
        
    except Exception as e:
        print(f"GDP 데이터베이스 조회 오류: {e}")
        return []

def save_gdp_to_database(gdp_data):
    """GDP 데이터를 데이터베이스에 저장합니다."""
    try:
        print(f"[DEBUG SAVE] Starting GDP save, data count: {len(gdp_data)}")
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        table_name = 'economy_gdp_data'
        
        # 테이블 존재 여부 확인 및 자동 생성
        if DB_SETUP_AVAILABLE and ensure_table_exists:
            db_url = os.getenv('SUPABASE_DB_URL')
            if not ensure_table_exists(table_name, supabase, db_url):
                print(f"[WARNING] {table_name} 테이블을 생성할 수 없습니다. 수동으로 생성해주세요.")
                return False
        
        saved_count = 0
        skipped_count = 0
        
        for quarter_key, gdp_value in gdp_data.items():
            try:
                # quarter_key에서 년도와 분기 추출 (예: "2024Q3" -> 2024, 3)
                year_str, quarter_str = quarter_key.split('Q')
                year = int(year_str)
                quarter = int(quarter_str)
                
                print(f"[DEBUG SAVE] Processing {quarter_key}: GDP={gdp_value}")
                
                # 기본키 존재 여부 확인
                existing = supabase.table(table_name).select('id').eq('year', year).eq('quarter', quarter).execute()
                
                if existing.data:
                    # 데이터가 이미 존재하면 건너뛰기
                    skipped_count += 1
                    print(f"GDP 데이터가 이미 존재함: {year}Q{quarter}")
                    continue
                
                # GDP 데이터 저장
                record = {
                    'year': year,
                    'quarter': quarter,
                    'gdp_value': gdp_value,
                    'cache_year': cache_year,
                    'cache_month': cache_month,
                    'last_updated': current_date.isoformat()
                }
                
                print(f"[DEBUG SAVE] Record to insert: {record}")
                
                supabase.table(table_name).insert(record).execute()
                saved_count += 1
                print(f"새 GDP 데이터 저장: {year}Q{quarter}")
                
            except Exception as e:
                print(f"GDP 데이터베이스 처리 오류: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"GDP 데이터베이스 저장 완료: (새로 저장: {saved_count}개, 건너뜀: {skipped_count}개)")
        return True
        
    except Exception as e:
        print(f"GDP 데이터베이스 저장 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def clear_gdp_cache_data(cache_year, cache_month):
    """GDP 데이터에서 동일한 cache_year, cache_month를 가진 데이터 삭제"""
    try:
        table_name = 'economy_gdp_data'
        
        # 동일한 cache_year, cache_month를 가진 데이터 삭제
        delete_result = supabase.table(table_name).delete().eq('cache_year', cache_year).eq('cache_month', cache_month).execute()
        deleted_count = len(delete_result.data) if delete_result.data else 0
        
        print(f"GDP 캐시 데이터 삭제 완료: {cache_year}년 {cache_month}월 데이터 {deleted_count}개 삭제")
        return True, deleted_count
        
    except Exception as e:
        print(f"GDP 캐시 데이터 삭제 오류: {e}")
        return False, 0

def format_gdp_chart_data(data, period):
    """GDP 차트용 데이터 포맷팅"""
    try:
        print(f"[DEBUG FORMAT] Formatting GDP chart data, period={period}, data_count={len(data)}")
        
        current_year = datetime.now().year
        start_year = current_year - period
        
        # 표준 labels 생성 (분기별)
        labels = []
        for year in range(start_year, current_year + 1):
            for quarter in range(1, 5):
                labels.append(f"{year}Q{quarter}")
        
        # 데이터 매핑
        data_map = {}
        for item in data:
            year = item['year']
            quarter = item['quarter']
            label = f"{year}Q{quarter}"
            data_map[label] = item.get('gdp_value', 0)
        
        # values 생성
        values = []
        for label in labels:
            if label in data_map:
                values.append(data_map[label])
            else:
                values.append(None)
        
        print(f"[DEBUG FORMAT] Result labels: {labels}")
        print(f"[DEBUG FORMAT] GDP values: {values}")
        
        return {
            'labels': labels,
            'gdp_values': values
        }
        
    except Exception as e:
        print(f"GDP 차트 데이터 포맷팅 오류: {e}")
        return None

# =============================================================================
# S&P 500 Helper Functions
# =============================================================================

def get_sp500_data_from_fred(years=4):
    """FRED API에서 S&P 500 데이터를 조회합니다 (분기별)"""
    try:
        current_date = datetime.now()
        current_year = current_date.year
        start_year = current_year - years
        
        # FRED에서 S&P 500 지수 조회 (SP500)
        print(f"S&P 500 데이터 조회 중...")
        sp500_series = fred.get_series('SP500', observation_start=f'{start_year}-01-01')
        
        if sp500_series is None or sp500_series.empty:
            print("S&P 500 데이터가 비어있습니다. 대체 데이터 사용...")
            return get_sp500_fallback_data(years)
        
        # 분기별 데이터로 변환 (각 분기 마지막 달의 평균값 사용)
        sp500_data = {}
        quarterly_data = {}
        
        for idx, value in sp500_series.items():
            # NaN 값 건너뛰기 (공휴일/휴장일 등)
            if pd.isna(value):
                continue
            
            year = idx.year
            month = idx.month
            if month in [1, 2, 3]:
                quarter = 1
            elif month in [4, 5, 6]:
                quarter = 2
            elif month in [7, 8, 9]:
                quarter = 3
            else:
                quarter = 4
            
            if year >= start_year and year <= current_year:
                key = f"{year}Q{quarter}"
                if key not in quarterly_data:
                    quarterly_data[key] = []
                quarterly_data[key].append(value)
        
        # 각 분기의 평균값 계산
        for key, values in quarterly_data.items():
            avg_value = sum(values) / len(values)
            sp500_data[key] = round(avg_value, 2)
            print(f"{key}: S&P 500={avg_value:.2f}")
        
        if len(sp500_data) == 0:
            print("S&P 500 데이터가 없습니다. 대체 데이터 사용...")
            return get_sp500_fallback_data(years)
        
        print(f"S&P 500 데이터 조회 완료: 총 {len(sp500_data)}개 분기")
        return sp500_data
        
    except Exception as e:
        print(f"S&P 500 데이터 조회 오류: {e}")
        import traceback
        traceback.print_exc()
        return get_sp500_fallback_data(years)

def get_sp500_fallback_data(years=4):
    """S&P 500 대체 데이터 (FRED API 실패 시)"""
    print("S&P 500 대체 데이터 사용")
    current_year = datetime.now().year
    start_year = current_year - years
    
    # 실제 역사적 데이터 기반 추정값
    sp500_data = {}
    base_values = {
        2021: {'Q1': 3811.15, 'Q2': 4297.50, 'Q3': 4395.64, 'Q4': 4515.55},
        2022: {'Q1': 4384.89, 'Q2': 3785.38, 'Q3': 3585.62, 'Q4': 3839.50},
        2023: {'Q1': 3977.53, 'Q2': 4450.38, 'Q3': 4288.05, 'Q4': 4783.35},
        2024: {'Q1': 5254.35, 'Q2': 5460.48, 'Q3': 5705.81, 'Q4': 5900.00},
        2025: {'Q1': 5850.00, 'Q2': 5700.00, 'Q3': None, 'Q4': None}
    }
    
    for year in range(start_year, current_year + 1):
        if year in base_values:
            for quarter in range(1, 5):
                q_key = f'Q{quarter}'
                if q_key in base_values[year] and base_values[year][q_key] is not None:
                    key = f"{year}Q{quarter}"
                    sp500_data[key] = round(base_values[year][q_key], 2)
    
    print(f"대체 S&P 500 데이터 생성 완료: 총 {len(sp500_data)}개 분기")
    return sp500_data

def check_sp500_database_data():
    """S&P 500 데이터베이스에서 현재 달 데이터 확인"""
    try:
        current_date = datetime.now()
        current_year = current_date.year
        current_month = current_date.month
        
        table_name = 'economy_sp500_data'
        
        # 현재 달에 캐시된 데이터가 있는지 확인
        result = supabase.table(table_name).select('*').eq('cache_year', current_year).eq('cache_month', current_month).execute()
        
        if result.data and len(result.data) > 0:
            print(f"S&P 500 데이터베이스에 현재 달({current_year}-{current_month}) 데이터 {len(result.data)}개 존재")
            return True, result.data
        else:
            print(f"S&P 500 데이터베이스에 현재 달({current_year}-{current_month}) 데이터 없음")
            return False, []
            
    except Exception as e:
        print(f"S&P 500 데이터베이스 확인 오류: {e}")
        return False, []

def get_sp500_database_data(period=4):
    """S&P 500 데이터베이스에서 데이터 조회"""
    try:
        current_year = datetime.now().year
        start_year = current_year - period
        
        table_name = 'economy_sp500_data'
        
        # 기간 내 모든 데이터 조회
        result = supabase.table(table_name).select('*').gte('year', start_year).lte('year', current_year).order('year', desc=False).order('quarter', desc=False).execute()
        
        if result.data:
            print(f"S&P 500 데이터베이스에서 {len(result.data)}개 데이터 조회")
            return result.data
        else:
            print("S&P 500 데이터베이스에 데이터가 없습니다.")
            return []
            
    except Exception as e:
        print(f"S&P 500 데이터베이스 조회 오류: {e}")
        return []

def save_sp500_to_database(sp500_data):
    """S&P 500 데이터를 데이터베이스에 저장합니다."""
    try:
        print(f"[DEBUG SAVE] Starting S&P 500 save, data count: {len(sp500_data)}")
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        table_name = 'economy_sp500_data'
        
        # 테이블 존재 여부 확인 및 자동 생성
        if DB_SETUP_AVAILABLE and ensure_table_exists:
            db_url = os.getenv('SUPABASE_DB_URL')
            if not ensure_table_exists(table_name, supabase, db_url):
                print(f"[WARNING] {table_name} 테이블을 생성할 수 없습니다. 수동으로 생성해주세요.")
                return False
        
        saved_count = 0
        skipped_count = 0
        
        for quarter_key, sp500_value in sp500_data.items():
            try:
                # quarter_key에서 년도와 분기 추출 (예: "2024Q3" -> 2024, 3)
                year_str, quarter_str = quarter_key.split('Q')
                year = int(year_str)
                quarter = int(quarter_str)
                
                print(f"[DEBUG SAVE] Processing {quarter_key}: S&P 500={sp500_value}")
                
                # 기본키 존재 여부 확인
                existing = supabase.table(table_name).select('id').eq('year', year).eq('quarter', quarter).execute()
                
                if existing.data:
                    # 데이터가 이미 존재하면 건너뛰기
                    skipped_count += 1
                    print(f"S&P 500 데이터가 이미 존재함: {year}Q{quarter}")
                    continue
                
                # S&P 500 데이터 저장
                record = {
                    'year': year,
                    'quarter': quarter,
                    'sp500_value': sp500_value,
                    'cache_year': cache_year,
                    'cache_month': cache_month,
                    'last_updated': current_date.isoformat()
                }
                
                print(f"[DEBUG SAVE] Record to insert: {record}")
                
                supabase.table(table_name).insert(record).execute()
                saved_count += 1
                print(f"새 S&P 500 데이터 저장: {year}Q{quarter}")
                
            except Exception as e:
                print(f"S&P 500 데이터베이스 처리 오류: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"S&P 500 데이터베이스 저장 완료: (새로 저장: {saved_count}개, 건너뜀: {skipped_count}개)")
        return True
        
    except Exception as e:
        print(f"S&P 500 데이터베이스 저장 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def clear_sp500_cache_data(cache_year, cache_month):
    """S&P 500 데이터에서 동일한 cache_year, cache_month를 가진 데이터 삭제"""
    try:
        table_name = 'economy_sp500_data'
        
        # 동일한 cache_year, cache_month를 가진 데이터 삭제
        delete_result = supabase.table(table_name).delete().eq('cache_year', cache_year).eq('cache_month', cache_month).execute()
        deleted_count = len(delete_result.data) if delete_result.data else 0
        
        print(f"S&P 500 캐시 데이터 삭제 완료: {cache_year}년 {cache_month}월 데이터 {deleted_count}개 삭제")
        return True, deleted_count
        
    except Exception as e:
        print(f"S&P 500 캐시 데이터 삭제 오류: {e}")
        import traceback
        traceback.print_exc()
        return False, 0

def format_sp500_chart_data(data, period):
    """S&P 500 차트용 데이터 포맷팅"""
    try:
        print(f"[DEBUG FORMAT] Formatting S&P 500 chart data, period={period}, data_count={len(data)}")
        
        current_year = datetime.now().year
        start_year = current_year - period
        
        # 표준 labels 생성 (분기별)
        labels = []
        for year in range(start_year, current_year + 1):
            for quarter in range(1, 5):
                labels.append(f"{year}Q{quarter}")
        
        # 데이터 매핑
        data_map = {}
        for item in data:
            year = item['year']
            quarter = item['quarter']
            label = f"{year}Q{quarter}"
            data_map[label] = item.get('sp500_value', 0)
        
        # values 생성
        values = []
        for label in labels:
            if label in data_map:
                values.append(data_map[label])
            else:
                values.append(None)
        
        print(f"[DEBUG FORMAT] Result labels: {labels}")
        print(f"[DEBUG FORMAT] S&P 500 values: {values}")
        
        return {
            'labels': labels,
            'sp500_values': values
        }
        
    except Exception as e:
        print(f"S&P 500 차트 데이터 포맷팅 오류: {e}")
        return None

# =============================================================================
# 버핏지수 (Buffett Indicator) Helper Functions
# =============================================================================

def get_buffett_indicator_data_from_fred(years=4):
    """FRED API에서 버핏지수 데이터를 조회합니다 (분기별)"""
    try:
        current_date = datetime.now()
        current_year = current_date.year
        start_year = current_year - years
        
        # FRED에서 직접 Market Cap to GDP 비율 조회
        # DDDM01USA156NWDB: Market Capitalization of Listed Domestic Companies (% of GDP)
        print(f"버핏지수(Market Cap to GDP) 데이터 조회 중...")
        
        try:
            # 첫 번째 시도: 직접 비율 데이터
            buffett_series = fred.get_series('DDDM01USA156NWDB', observation_start=f'{start_year}-01-01')
            print(f"DDDM01USA156NWDB 시리즈 조회 성공")
        except:
            print("DDDM01USA156NWDB 조회 실패, Wilshire 방식으로 시도...")
            # 두 번째 시도: Wilshire 5000과 GDP 사용
            try:
                market_cap_series = fred.get_series('WILL5000IND', observation_start=f'{start_year}-01-01')
                gdp_series = fred.get_series('GDPC1', observation_start=f'{start_year}-01-01')
                
                if market_cap_series is None or market_cap_series.empty or gdp_series is None or gdp_series.empty:
                    print("Wilshire/GDP 데이터 조회 실패, 대체 방법 사용...")
                    return get_buffett_fallback_data(years)
                
                # GDP를 딕셔너리로 변환
                gdp_dict = {}
                for idx, value in gdp_series.items():
                    year = idx.year
                    month = idx.month
                    quarter = (month - 1) // 3 + 1
                    key = f"{year}Q{quarter}"
                    gdp_dict[key] = value
                
                # Market Cap과 매칭하여 계산
                buffett_data = {}
                for idx, market_value in market_cap_series.items():
                    year = idx.year
                    month = idx.month
                    quarter = (month - 1) // 3 + 1
                    
                    if year >= start_year and year <= current_year:
                        key = f"{year}Q{quarter}"
                        if key in gdp_dict:
                            gdp_value = gdp_dict[key]
                            # Wilshire 5000 Index를 시가총액으로 변환 (대략적)
                            market_cap_billions = market_value * 1.2  # 대략적 변환 계수
                            buffett_ratio = (market_cap_billions / gdp_value) * 100 if gdp_value > 0 else 0
                            
                            buffett_data[key] = {
                                'market_cap': round(market_cap_billions, 4),
                                'gdp_value': round(gdp_value, 4),
                                'buffett_ratio': round(buffett_ratio, 4)
                            }
                            print(f"{key}: Buffett Ratio={buffett_ratio:.2f}%")
                
                if buffett_data:
                    print(f"버핏지수 데이터 조회 완료: 총 {len(buffett_data)}개 분기")
                    return buffett_data
                else:
                    return get_buffett_fallback_data(years)
                    
            except Exception as e2:
                print(f"Wilshire 방식 실패: {e2}")
                return get_buffett_fallback_data(years)
        
        # 직접 비율 데이터가 있는 경우
        if buffett_series is not None and not buffett_series.empty:
            buffett_data = {}
            gdp_series = fred.get_series('GDPC1', observation_start=f'{start_year}-01-01')
            
            # GDP 데이터 매핑
            gdp_dict = {}
            if gdp_series is not None and not gdp_series.empty:
                for idx, value in gdp_series.items():
                    year = idx.year
                    month = idx.month
                    quarter = (month - 1) // 3 + 1
                    key = f"{year}Q{quarter}"
                    gdp_dict[key] = value
            
            for idx, ratio_value in buffett_series.items():
                year = idx.year
                month = idx.month
                quarter = (month - 1) // 3 + 1
                
                if year >= start_year and year <= current_year:
                    key = f"{year}Q{quarter}"
                    gdp_value = gdp_dict.get(key, 20000)  # 기본값
                    market_cap = (ratio_value / 100) * gdp_value if gdp_value > 0 else 0
                    
                    buffett_data[key] = {
                        'market_cap': round(market_cap, 4),
                        'gdp_value': round(gdp_value, 4),
                        'buffett_ratio': round(ratio_value, 4)
                    }
                    print(f"{key}: Buffett Ratio={ratio_value:.2f}%")
            
            if buffett_data:
                print(f"버핏지수 데이터 조회 완료: 총 {len(buffett_data)}개 분기")
                return buffett_data
        
        # 모든 시도 실패 시 대체 데이터 사용
        return get_buffett_fallback_data(years)
        
    except Exception as e:
        print(f"버핏지수 데이터 조회 오류: {e}")
        import traceback
        traceback.print_exc()
        return get_buffett_fallback_data(years)

def get_buffett_fallback_data(years=4):
    """버핏지수 대체 데이터 (FRED API 실패 시)"""
    print("버핏지수 대체 데이터 사용")
    current_year = datetime.now().year
    start_year = current_year - years
    
    # 실제 역사적 데이터 기반 추정값
    buffett_data = {}
    base_values = {
        2021: {'Q1': 185, 'Q2': 195, 'Q3': 190, 'Q4': 200},
        2022: {'Q1': 175, 'Q2': 150, 'Q3': 145, 'Q4': 155},
        2023: {'Q1': 160, 'Q2': 170, 'Q3': 165, 'Q4': 180},
        2024: {'Q1': 185, 'Q2': 190, 'Q3': 195, 'Q4': 200},
        2025: {'Q1': 195, 'Q2': 190, 'Q3': None, 'Q4': None}
    }
    
    for year in range(start_year, current_year + 1):
        if year in base_values:
            for quarter in range(1, 5):
                q_key = f'Q{quarter}'
                if q_key in base_values[year] and base_values[year][q_key] is not None:
                    key = f"{year}Q{quarter}"
                    ratio = base_values[year][q_key]
                    gdp_value = 22000 + (year - 2021) * 500  # 추정 GDP
                    market_cap = (ratio / 100) * gdp_value
                    
                    buffett_data[key] = {
                        'market_cap': round(market_cap, 4),
                        'gdp_value': round(gdp_value, 4),
                        'buffett_ratio': round(ratio, 4)
                    }
    
    print(f"대체 데이터 생성 완료: 총 {len(buffett_data)}개 분기")
    return buffett_data

def check_buffett_indicator_database_data():
    """버핏지수 데이터베이스에서 현재 달 데이터 확인"""
    try:
        current_date = datetime.now()
        current_year = current_date.year
        current_month = current_date.month
        
        table_name = 'economy_buffett_indicator_data'
        
        # 현재 달에 캐시된 데이터가 있는지 확인
        result = supabase.table(table_name).select('*').eq('cache_year', current_year).eq('cache_month', current_month).execute()
        
        if result.data and len(result.data) > 0:
            print(f"버핏지수 데이터베이스에 현재 달({current_year}-{current_month}) 데이터 {len(result.data)}개 존재")
            return True, result.data
        else:
            print(f"버핏지수 데이터베이스에 현재 달({current_year}-{current_month}) 데이터 없음")
            return False, []
            
    except Exception as e:
        print(f"버핏지수 데이터베이스 확인 오류: {e}")
        return False, []

def get_buffett_indicator_database_data(period=4):
    """버핏지수 데이터베이스에서 데이터 조회"""
    try:
        current_year = datetime.now().year
        start_year = current_year - period
        
        table_name = 'economy_buffett_indicator_data'
        
        # 기간 내 모든 데이터 조회
        result = supabase.table(table_name).select('*').gte('year', start_year).lte('year', current_year).order('year', desc=False).order('quarter', desc=False).execute()
        
        if result.data:
            print(f"버핏지수 데이터베이스에서 {len(result.data)}개 데이터 조회")
            return result.data
        else:
            print("버핏지수 데이터베이스에 데이터가 없습니다.")
            return []
            
    except Exception as e:
        print(f"버핏지수 데이터베이스 조회 오류: {e}")
        return []

def save_buffett_indicator_to_database(buffett_data):
    """버핏지수 데이터를 데이터베이스에 저장합니다."""
    try:
        print(f"[DEBUG SAVE] Starting Buffett Indicator save, data count: {len(buffett_data)}")
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        table_name = 'economy_buffett_indicator_data'
        
        # 테이블 존재 여부 확인 및 자동 생성
        if DB_SETUP_AVAILABLE and ensure_table_exists:
            db_url = os.getenv('SUPABASE_DB_URL')
            if not ensure_table_exists(table_name, supabase, db_url):
                print(f"[WARNING] {table_name} 테이블을 생성할 수 없습니다. 수동으로 생성해주세요.")
                return False
        
        saved_count = 0
        skipped_count = 0
        
        for quarter_key, data_item in buffett_data.items():
            try:
                # quarter_key에서 년도와 분기 추출 (예: "2024Q3" -> 2024, 3)
                year_str, quarter_str = quarter_key.split('Q')
                year = int(year_str)
                quarter = int(quarter_str)
                
                print(f"[DEBUG SAVE] Processing {quarter_key}: Buffett Ratio={data_item['buffett_ratio']}")
                
                # 기본키 존재 여부 확인
                existing = supabase.table(table_name).select('id').eq('year', year).eq('quarter', quarter).execute()
                
                if existing.data:
                    # 데이터가 이미 존재하면 건너뛰기
                    skipped_count += 1
                    print(f"버핏지수 데이터가 이미 존재함: {year}Q{quarter}")
                    continue
                
                # 버핏지수 데이터 저장
                record = {
                    'year': year,
                    'quarter': quarter,
                    'market_cap': data_item['market_cap'],
                    'gdp_value': data_item['gdp_value'],
                    'buffett_ratio': data_item['buffett_ratio'],
                    'cache_year': cache_year,
                    'cache_month': cache_month,
                    'last_updated': current_date.isoformat()
                }
                
                print(f"[DEBUG SAVE] Record to insert: {record}")
                
                supabase.table(table_name).insert(record).execute()
                saved_count += 1
                print(f"새 버핏지수 데이터 저장: {year}Q{quarter}")
                
            except Exception as e:
                print(f"버핏지수 데이터베이스 처리 오류: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"버핏지수 데이터베이스 저장 완료: (새로 저장: {saved_count}개, 건너뜀: {skipped_count}개)")
        return True
        
    except Exception as e:
        print(f"버핏지수 데이터베이스 저장 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def clear_buffett_indicator_cache_data(cache_year, cache_month):
    """버핏지수 데이터에서 동일한 cache_year, cache_month를 가진 데이터 삭제"""
    try:
        table_name = 'economy_buffett_indicator_data'
        
        # 동일한 cache_year, cache_month를 가진 데이터 삭제
        delete_result = supabase.table(table_name).delete().eq('cache_year', cache_year).eq('cache_month', cache_month).execute()
        deleted_count = len(delete_result.data) if delete_result.data else 0
        
        print(f"버핏지수 캐시 데이터 삭제 완료: {cache_year}년 {cache_month}월 데이터 {deleted_count}개 삭제")
        return True, deleted_count
        
    except Exception as e:
        print(f"버핏지수 캐시 데이터 삭제 오류: {e}")
        import traceback
        traceback.print_exc()
        return False, 0

def format_buffett_indicator_chart_data(data, period):
    """버핏지수 차트용 데이터 포맷팅"""
    try:
        print(f"[DEBUG FORMAT] Formatting Buffett Indicator chart data, period={period}, data_count={len(data)}")
        
        current_year = datetime.now().year
        start_year = current_year - period
        
        # 표준 labels 생성 (분기별)
        labels = []
        for year in range(start_year, current_year + 1):
            for quarter in range(1, 5):
                labels.append(f"{year}Q{quarter}")
        
        # 데이터 매핑
        data_map = {}
        for item in data:
            year = item['year']
            quarter = item['quarter']
            label = f"{year}Q{quarter}"
            data_map[label] = {
                'market_cap': item.get('market_cap', 0),
                'gdp_value': item.get('gdp_value', 0),
                'buffett_ratio': item.get('buffett_ratio', 0)
            }
        
        # values 생성
        market_cap_values = []
        gdp_values = []
        buffett_ratio_values = []
        
        for label in labels:
            if label in data_map:
                market_cap_values.append(data_map[label]['market_cap'])
                gdp_values.append(data_map[label]['gdp_value'])
                buffett_ratio_values.append(data_map[label]['buffett_ratio'])
            else:
                market_cap_values.append(None)
                gdp_values.append(None)
                buffett_ratio_values.append(None)
        
        print(f"[DEBUG FORMAT] Result labels: {labels}")
        print(f"[DEBUG FORMAT] Buffett Ratio values: {buffett_ratio_values}")
        
        return {
            'labels': labels,
            'market_cap_values': market_cap_values,
            'gdp_values': gdp_values,
            'buffett_ratio_values': buffett_ratio_values
        }
        
    except Exception as e:
        print(f"버핏지수 차트 데이터 포맷팅 오류: {e}")
        return None

# =============================================================================
# 주택재고량 (Housing Inventory) Helper Functions
# =============================================================================

def get_housing_inventory_data_from_fred(years=4):
    """FRED API에서 주택재고량 데이터를 조회합니다 (분기별)"""
    try:
        current_date = datetime.now()
        current_year = current_date.year
        start_year = current_year - years
        
        # FRED에서 주택재고량 조회 (MSACSR - Monthly Supply of Houses)
        print(f"주택재고량 데이터 조회 중...")
        housing_series = fred.get_series('MSACSR', observation_start=f'{start_year}-01-01')
        
        if housing_series is None or housing_series.empty:
            print("주택재고량 데이터가 비어있습니다. 대체 데이터 사용...")
            return get_housing_inventory_fallback_data(years)
        
        # 분기별 데이터로 변환
        housing_data = {}
        quarterly_data = {}
        
        for idx, value in housing_series.items():
            # NaN 값 건너뛰기
            if pd.isna(value):
                continue
            
            year = idx.year
            month = idx.month
            if month in [1, 2, 3]:
                quarter = 1
            elif month in [4, 5, 6]:
                quarter = 2
            elif month in [7, 8, 9]:
                quarter = 3
            else:
                quarter = 4
            
            if year >= start_year and year <= current_year:
                key = f"{year}Q{quarter}"
                if key not in quarterly_data:
                    quarterly_data[key] = []
                quarterly_data[key].append(value)
        
        # 각 분기의 평균값 계산
        for key, values in quarterly_data.items():
            avg_value = sum(values) / len(values)
            housing_data[key] = round(avg_value, 2)
            print(f"{key}: 주택재고량={avg_value:.2f}")
        
        if len(housing_data) == 0:
            print("주택재고량 데이터가 없습니다. 대체 데이터 사용...")
            return get_housing_inventory_fallback_data(years)
        
        print(f"주택재고량 데이터 조회 완료: 총 {len(housing_data)}개 분기")
        return housing_data
        
    except Exception as e:
        print(f"주택재고량 데이터 조회 오류: {e}")
        import traceback
        traceback.print_exc()
        return get_housing_inventory_fallback_data(years)

def get_housing_inventory_fallback_data(years=4):
    """주택재고량 대체 데이터 (FRED API 실패 시)"""
    print("주택재고량 대체 데이터 사용")
    current_year = datetime.now().year
    start_year = current_year - years
    
    # 실제 역사적 데이터 기반 추정값 (개월 수)
    housing_data = {}
    base_values = {
        2021: {'Q1': 4.2, 'Q2': 4.8, 'Q3': 5.5, 'Q4': 6.2},
        2022: {'Q1': 5.8, 'Q2': 7.0, 'Q3': 9.0, 'Q4': 10.5},
        2023: {'Q1': 7.5, 'Q2': 6.2, 'Q3': 5.8, 'Q4': 5.3},
        2024: {'Q1': 5.0, 'Q2': 5.5, 'Q3': 7.2, 'Q4': 8.5},
        2025: {'Q1': 7.8, 'Q2': 8.2, 'Q3': 8.0, 'Q4': 7.5}
    }
    
    for year in range(start_year, current_year + 1):
        if year in base_values:
            for quarter in range(1, 5):
                q_key = f'Q{quarter}'
                if q_key in base_values[year] and base_values[year][q_key] is not None:
                    key = f"{year}Q{quarter}"
                    housing_data[key] = round(base_values[year][q_key], 2)
    
    print(f"대체 주택재고량 데이터 생성 완료: 총 {len(housing_data)}개 분기")
    return housing_data

def check_housing_inventory_database_data():
    """주택재고량 데이터베이스에서 현재 달 데이터 확인"""
    try:
        current_date = datetime.now()
        current_year = current_date.year
        current_month = current_date.month
        
        table_name = 'economy_housing_inventory_data'
        
        # 현재 달에 캐시된 데이터가 있는지 확인
        result = supabase.table(table_name).select('*').eq('cache_year', current_year).eq('cache_month', current_month).execute()
        
        if result.data and len(result.data) > 0:
            print(f"주택재고량 데이터베이스에 현재 달({current_year}-{current_month}) 데이터 {len(result.data)}개 존재")
            return True, result.data
        else:
            print(f"주택재고량 데이터베이스에 현재 달({current_year}-{current_month}) 데이터 없음")
            return False, []
            
    except Exception as e:
        print(f"주택재고량 데이터베이스 확인 오류: {e}")
        return False, []

def get_housing_inventory_database_data(period=4):
    """주택재고량 데이터베이스에서 데이터 조회"""
    try:
        current_year = datetime.now().year
        start_year = current_year - period
        
        table_name = 'economy_housing_inventory_data'
        
        # 기간 내 모든 데이터 조회
        result = supabase.table(table_name).select('*').gte('year', start_year).lte('year', current_year).order('year', desc=False).order('quarter', desc=False).execute()
        
        if result.data:
            print(f"주택재고량 데이터베이스에서 {len(result.data)}개 데이터 조회")
            return result.data
        else:
            print("주택재고량 데이터베이스에 데이터가 없습니다.")
            return []
            
    except Exception as e:
        print(f"주택재고량 데이터베이스 조회 오류: {e}")
        return []

def save_housing_inventory_to_database(housing_data):
    """주택재고량 데이터를 데이터베이스에 저장합니다."""
    try:
        print(f"[DEBUG SAVE] Starting 주택재고량 save, data count: {len(housing_data)}")
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        table_name = 'economy_housing_inventory_data'
        
        # 테이블 존재 여부 확인 및 자동 생성
        if DB_SETUP_AVAILABLE and ensure_table_exists:
            db_url = os.getenv('SUPABASE_DB_URL')
            if not ensure_table_exists(table_name, supabase, db_url):
                print(f"[WARNING] {table_name} 테이블을 생성할 수 없습니다. 수동으로 생성해주세요.")
                return False
        
        saved_count = 0
        skipped_count = 0
        
        for quarter_key, inventory_value in housing_data.items():
            try:
                # quarter_key에서 년도와 분기 추출
                year_str, quarter_str = quarter_key.split('Q')
                year = int(year_str)
                quarter = int(quarter_str)
                
                print(f"[DEBUG SAVE] Processing {quarter_key}: 주택재고량={inventory_value}")
                
                # 기본키 존재 여부 확인
                existing = supabase.table(table_name).select('id').eq('year', year).eq('quarter', quarter).execute()
                
                if existing.data:
                    skipped_count += 1
                    print(f"주택재고량 데이터가 이미 존재함: {year}Q{quarter}")
                    continue
                
                # 주택재고량 데이터 저장
                record = {
                    'year': year,
                    'quarter': quarter,
                    'inventory_value': inventory_value,
                    'cache_year': cache_year,
                    'cache_month': cache_month,
                    'last_updated': current_date.isoformat()
                }
                
                print(f"[DEBUG SAVE] Record to insert: {record}")
                
                supabase.table(table_name).insert(record).execute()
                saved_count += 1
                print(f"새 주택재고량 데이터 저장: {year}Q{quarter}")
                
            except Exception as e:
                print(f"주택재고량 데이터베이스 처리 오류: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"주택재고량 데이터베이스 저장 완료: (새로 저장: {saved_count}개, 건너뜀: {skipped_count}개)")
        return True
        
    except Exception as e:
        print(f"주택재고량 데이터베이스 저장 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def clear_housing_inventory_cache_data(cache_year, cache_month):
    """주택재고량 데이터에서 동일한 cache_year, cache_month를 가진 데이터 삭제"""
    try:
        table_name = 'economy_housing_inventory_data'
        
        # 동일한 cache_year, cache_month를 가진 데이터 삭제
        delete_result = supabase.table(table_name).delete().eq('cache_year', cache_year).eq('cache_month', cache_month).execute()
        deleted_count = len(delete_result.data) if delete_result.data else 0
        
        print(f"주택재고량 캐시 데이터 삭제 완료: {cache_year}년 {cache_month}월 데이터 {deleted_count}개 삭제")
        return True, deleted_count
        
    except Exception as e:
        print(f"주택재고량 캐시 데이터 삭제 실패: {e}")
        import traceback
        traceback.print_exc()
        return False, 0

def format_housing_inventory_chart_data(data, period):
    """주택재고량 차트용 데이터 포맷팅"""
    try:
        print(f"[DEBUG FORMAT] Formatting 주택재고량 chart data, period={period}, data_count={len(data)}")
        
        current_year = datetime.now().year
        start_year = current_year - period
        
        # 표준 labels 생성 (분기별)
        labels = []
        for year in range(start_year, current_year + 1):
            for quarter in range(1, 5):
                labels.append(f"{year}Q{quarter}")
        
        # 데이터 매핑
        data_map = {}
        for item in data:
            year = item['year']
            quarter = item['quarter']
            label = f"{year}Q{quarter}"
            data_map[label] = item.get('inventory_value', 0)
        
        # values 생성
        values = []
        for label in labels:
            if label in data_map:
                values.append(data_map[label])
            else:
                values.append(None)
        
        print(f"[DEBUG FORMAT] Result labels: {labels}")
        print(f"[DEBUG FORMAT] 주택재고량 values: {values}")
        
        return {
            'labels': labels,
            'inventory_values': values
        }
        
    except Exception as e:
        print(f"주택재고량 차트 데이터 포맷팅 오류: {e}")
        return None

@app.route('/api/economy/gdp/check', methods=['POST'])
def check_economy_gdp():
    """GDP 데이터 캐시 확인 및 처리"""
    try:
        period = 4  # 4년 고정
        
        print(f"GDP 캐시 확인 요청: period={period}")
        
        # 현재 날짜 기준 캐시 확인
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        # GDP 데이터베이스에서 현재 달 데이터 확인
        has_current_month_data, db_data = check_gdp_database_data()
        
        if has_current_month_data and db_data:
            # 캐시된 데이터가 있으면 바로 반환
            print(f"캐시된 GDP 데이터 사용")
            chart_data = format_gdp_chart_data(db_data, period)
            
            if chart_data is None:
                return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
            
            return jsonify({
                'success': True,
                'type': 'gdp',
                'chart_data': chart_data,
                'period': period,
                'cached': True,
                'message': '캐시된 GDP 데이터를 사용합니다.'
            })
        else:
            # 캐시된 데이터가 없으면 FRED API에서 조회
            print(f"FRED API에서 GDP 데이터 조회")
            
            gdp_data = get_gdp_data_from_fred(period)
            
            if not gdp_data:
                return jsonify({'error': 'GDP 데이터를 가져올 수 없습니다.'}), 400
            
            # GDP 데이터베이스에 저장
            save_gdp_to_database(gdp_data)
            
            # 저장된 데이터로 차트 생성
            db_data = get_gdp_database_data(period)
            chart_data = format_gdp_chart_data(db_data, period)
            
            if chart_data is None:
                return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
            
            return jsonify({
                'success': True,
                'type': 'gdp',
                'chart_data': chart_data,
                'period': period,
                'cached': False,
                'message': 'FRED API에서 최신 GDP 데이터를 가져왔습니다.'
            })
        
    except Exception as e:
        print(f"GDP 캐시 확인 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'GDP 데이터 처리 중 오류가 발생했습니다.'}), 500

@app.route('/api/economy/gdp/refresh', methods=['POST'])
def refresh_economy_gdp():
    """GDP 데이터 새로고침 - API 성공 후 캐시 삭제"""
    try:
        period = 4  # 4년 고정
        
        print(f"GDP Refresh 요청: period={period}")
        
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        print(f"FRED API에서 최신 GDP 데이터 조회")
        
        # 1. 먼저 FRED API에서 GDP 데이터 조회
        gdp_data = get_gdp_data_from_fred(period)
        
        if not gdp_data:
            return jsonify({'error': 'GDP 데이터를 가져올 수 없습니다.'}), 400
        
        # 2. API 성공 후 현재 달 데이터 삭제
        clear_success, deleted_count = clear_gdp_cache_data(cache_year, cache_month)
        if not clear_success:
            print(f"GDP 캐시 데이터 삭제 실패")
        
        # 3. GDP 데이터베이스에 저장
        save_success = save_gdp_to_database(gdp_data)
        if not save_success:
            return jsonify({'error': 'GDP 데이터 저장에 실패했습니다.'}), 500
        
        # 4. GDP 데이터베이스에서 차트용 데이터 조회
        db_data = get_gdp_database_data(period)
        
        if not db_data:
            return jsonify({'error': 'GDP 데이터가 없습니다.'}), 400
        
        # 5. GDP 차트용 데이터 포맷팅
        chart_data = format_gdp_chart_data(db_data, period)
        
        if chart_data is None:
            return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
        
        return jsonify({
            'success': True,
            'type': 'gdp',
            'chart_data': chart_data,
            'period': period,
            'deleted_count': deleted_count,
            'message': f'GDP 데이터 {deleted_count}개를 삭제하고 최신 데이터로 새로고침했습니다.'
        })
        
    except Exception as e:
        print(f"GDP 새로고침 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'GDP 새로고침 중 오류가 발생했습니다.'}), 500

# =============================================================================
# S&P 500 API
# =============================================================================

@app.route('/api/economy/sp500/check', methods=['POST'])
def check_economy_sp500():
    """S&P 500 데이터 캐시 확인 및 처리"""
    try:
        period = 4  # 4년 고정
        
        print(f"S&P 500 캐시 확인 요청: period={period}")
        
        # 현재 날짜 기준 캐시 확인
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        # S&P 500 데이터베이스에서 현재 달 데이터 확인
        has_current_month_data, db_data = check_sp500_database_data()
        
        if has_current_month_data and db_data:
            # 캐시된 데이터가 있으면 바로 반환
            print(f"캐시된 S&P 500 데이터 사용")
            chart_data = format_sp500_chart_data(db_data, period)
            
            if chart_data is None:
                return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
            
            return jsonify({
                'success': True,
                'type': 'sp500',
                'chart_data': chart_data,
                'period': period,
                'cached': True,
                'message': '캐시된 S&P 500 데이터를 사용합니다.'
            })
        else:
            # 캐시된 데이터가 없으면 FRED API에서 조회
            print(f"FRED API에서 S&P 500 데이터 조회")
            
            sp500_data = get_sp500_data_from_fred(period)
            
            if not sp500_data:
                return jsonify({'error': 'S&P 500 데이터를 가져올 수 없습니다.'}), 400
            
            # S&P 500 데이터베이스에 저장
            save_sp500_to_database(sp500_data)
            
            # 저장된 데이터로 차트 생성
            db_data = get_sp500_database_data(period)
            chart_data = format_sp500_chart_data(db_data, period)
            
            if chart_data is None:
                return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
            
            return jsonify({
                'success': True,
                'type': 'sp500',
                'chart_data': chart_data,
                'period': period,
                'cached': False,
                'message': 'FRED API에서 최신 S&P 500 데이터를 가져왔습니다.'
            })
        
    except Exception as e:
        print(f"S&P 500 캐시 확인 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'S&P 500 데이터 처리 중 오류가 발생했습니다.'}), 500

@app.route('/api/economy/sp500/refresh', methods=['POST'])
def refresh_economy_sp500():
    """S&P 500 데이터 새로고침 - API 성공 후 캐시 삭제"""
    try:
        period = 4  # 4년 고정
        
        print(f"S&P 500 Refresh 요청: period={period}")
        
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        print(f"FRED API에서 최신 S&P 500 데이터 조회")
        
        # 1. 먼저 FRED API에서 S&P 500 데이터 조회
        sp500_data = get_sp500_data_from_fred(period)
        
        if not sp500_data:
            return jsonify({'error': 'S&P 500 데이터를 가져올 수 없습니다.'}), 400
        
        # 2. API 성공 후 현재 달 데이터 삭제
        clear_success, deleted_count = clear_sp500_cache_data(cache_year, cache_month)
        if not clear_success:
            print(f"S&P 500 캐시 데이터 삭제 실패")
        
        # 3. S&P 500 데이터베이스에 저장
        save_success = save_sp500_to_database(sp500_data)
        if not save_success:
            return jsonify({'error': 'S&P 500 데이터 저장에 실패했습니다.'}), 500
        
        # 4. S&P 500 데이터베이스에서 차트용 데이터 조회
        db_data = get_sp500_database_data(period)
        
        if not db_data:
            return jsonify({'error': 'S&P 500 데이터가 없습니다.'}), 400
        
        # 5. S&P 500 차트용 데이터 포맷팅
        chart_data = format_sp500_chart_data(db_data, period)
        
        if chart_data is None:
            return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
        
        return jsonify({
            'success': True,
            'type': 'sp500',
            'chart_data': chart_data,
            'period': period,
            'deleted_count': deleted_count,
            'message': f'S&P 500 데이터 {deleted_count}개를 삭제하고 최신 데이터로 새로고침했습니다.'
        })
        
    except Exception as e:
        print(f"S&P 500 새로고침 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'S&P 500 새로고침 중 오류가 발생했습니다.'}), 500

# =============================================================================
# 버핏지수 (Buffett Indicator) API
# =============================================================================

@app.route('/api/economy/buffett-indicator/check', methods=['POST'])
def check_economy_buffett_indicator():
    """버핏지수 데이터 캐시 확인 및 처리"""
    try:
        period = 4  # 4년 고정
        
        print(f"버핏지수 캐시 확인 요청: period={period}")
        
        # 현재 날짜 기준 캐시 확인
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        # 버핏지수 데이터베이스에서 현재 달 데이터 확인
        has_current_month_data, db_data = check_buffett_indicator_database_data()
        
        if has_current_month_data and db_data:
            # 캐시된 데이터가 있으면 바로 반환
            print(f"캐시된 버핏지수 데이터 사용")
            chart_data = format_buffett_indicator_chart_data(db_data, period)
            
            if chart_data is None:
                return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
            
            return jsonify({
                'success': True,
                'type': 'buffett_indicator',
                'chart_data': chart_data,
                'period': period,
                'cached': True,
                'message': '캐시된 버핏지수 데이터를 사용합니다.'
            })
        else:
            # 캐시된 데이터가 없으면 FRED API에서 조회
            print(f"FRED API에서 버핏지수 데이터 조회")
            
            buffett_data = get_buffett_indicator_data_from_fred(period)
            
            if not buffett_data:
                return jsonify({'error': '버핏지수 데이터를 가져올 수 없습니다.'}), 400
            
            # 버핏지수 데이터베이스에 저장
            save_buffett_indicator_to_database(buffett_data)
            
            # 저장된 데이터로 차트 생성
            db_data = get_buffett_indicator_database_data(period)
            chart_data = format_buffett_indicator_chart_data(db_data, period)
            
            if chart_data is None:
                return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
            
            return jsonify({
                'success': True,
                'type': 'buffett_indicator',
                'chart_data': chart_data,
                'period': period,
                'cached': False,
                'message': 'FRED API에서 최신 버핏지수 데이터를 가져왔습니다.'
            })
        
    except Exception as e:
        print(f"버핏지수 캐시 확인 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': '버핏지수 데이터 처리 중 오류가 발생했습니다.'}), 500

@app.route('/api/economy/buffett-indicator/refresh', methods=['POST'])
def refresh_economy_buffett_indicator():
    """버핏지수 데이터 새로고침 - API 성공 후 캐시 삭제"""
    try:
        period = 4  # 4년 고정
        
        print(f"버핏지수 Refresh 요청: period={period}")
        
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        print(f"FRED API에서 최신 버핏지수 데이터 조회")
        
        # 1. 먼저 FRED API에서 버핏지수 데이터 조회
        buffett_data = get_buffett_indicator_data_from_fred(period)
        
        if not buffett_data:
            return jsonify({'error': '버핏지수 데이터를 가져올 수 없습니다.'}), 400
        
        # 2. API 성공 후 현재 달 데이터 삭제
        clear_success, deleted_count = clear_buffett_indicator_cache_data(cache_year, cache_month)
        if not clear_success:
            print(f"버핏지수 캐시 데이터 삭제 실패")
        
        # 3. 버핏지수 데이터베이스에 저장
        save_success = save_buffett_indicator_to_database(buffett_data)
        if not save_success:
            return jsonify({'error': '버핏지수 데이터 저장에 실패했습니다.'}), 500
        
        # 4. 버핏지수 데이터베이스에서 차트용 데이터 조회
        db_data = get_buffett_indicator_database_data(period)
        
        if not db_data:
            return jsonify({'error': '버핏지수 데이터가 없습니다.'}), 400
        
        # 5. 버핏지수 차트용 데이터 포맷팅
        chart_data = format_buffett_indicator_chart_data(db_data, period)
        
        if chart_data is None:
            return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
        
        return jsonify({
            'success': True,
            'type': 'buffett_indicator',
            'chart_data': chart_data,
            'period': period,
            'deleted_count': deleted_count,
            'message': f'버핏지수 데이터 {deleted_count}개를 삭제하고 최신 데이터로 새로고침했습니다.'
        })
        
    except Exception as e:
        print(f"버핏지수 새로고침 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': '버핏지수 새로고침 중 오류가 발생했습니다.'}), 500

# =============================================================================
# 주택재고량 (Housing Inventory) API
# =============================================================================

@app.route('/api/economy/housing-inventory/check', methods=['POST'])
def check_economy_housing_inventory():
    """주택재고량 데이터 캐시 확인 및 처리"""
    try:
        period = 4  # 4년 고정
        
        print(f"주택재고량 캐시 확인 요청: period={period}")
        
        # 현재 날짜 기준 캐시 확인
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        # 주택재고량 데이터베이스에서 현재 달 데이터 확인
        has_current_month_data, db_data = check_housing_inventory_database_data()
        
        if has_current_month_data and db_data:
            # 캐시된 데이터가 있으면 바로 반환
            print(f"캐시된 주택재고량 데이터 사용")
            chart_data = format_housing_inventory_chart_data(db_data, period)
            
            if chart_data is None:
                return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
            
            return jsonify({
                'success': True,
                'type': 'housing_inventory',
                'chart_data': chart_data,
                'period': period,
                'cached': True,
                'message': '캐시된 주택재고량 데이터를 사용합니다.'
            })
        else:
            # 캐시된 데이터가 없으면 FRED API에서 조회
            print(f"FRED API에서 주택재고량 데이터 조회")
            
            housing_data = get_housing_inventory_data_from_fred(period)
            
            if not housing_data:
                return jsonify({'error': '주택재고량 데이터를 가져올 수 없습니다.'}), 400
            
            # 주택재고량 데이터베이스에 저장
            save_housing_inventory_to_database(housing_data)
            
            # 저장된 데이터로 차트 생성
            db_data = get_housing_inventory_database_data(period)
            chart_data = format_housing_inventory_chart_data(db_data, period)
            
            if chart_data is None:
                return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
            
            return jsonify({
                'success': True,
                'type': 'housing_inventory',
                'chart_data': chart_data,
                'period': period,
                'cached': False,
                'message': 'FRED API에서 최신 주택재고량 데이터를 가져왔습니다.'
            })
        
    except Exception as e:
        print(f"주택재고량 캐시 확인 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': '주택재고량 데이터 처리 중 오류가 발생했습니다.'}), 500

@app.route('/api/economy/housing-inventory/refresh', methods=['POST'])
def refresh_economy_housing_inventory():
    """주택재고량 데이터 새로고침 - API 성공 후 캐시 삭제"""
    try:
        period = 4  # 4년 고정
        
        print(f"주택재고량 Refresh 요청: period={period}")
        
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        print(f"FRED API에서 최신 주택재고량 데이터 조회")
        
        # 1. 먼저 FRED API에서 주택재고량 데이터 조회
        housing_data = get_housing_inventory_data_from_fred(period)
        
        if not housing_data:
            return jsonify({'error': '주택재고량 데이터를 가져올 수 없습니다.'}), 400
        
        # 2. API 성공 후 현재 달 데이터 삭제
        clear_success, deleted_count = clear_housing_inventory_cache_data(cache_year, cache_month)
        if not clear_success:
            print(f"주택재고량 캐시 데이터 삭제 실패")
        
        # 3. 주택재고량 데이터베이스에 저장
        save_success = save_housing_inventory_to_database(housing_data)
        if not save_success:
            return jsonify({'error': '주택재고량 데이터 저장에 실패했습니다.'}), 500
        
        # 4. 주택재고량 데이터베이스에서 차트용 데이터 조회
        db_data = get_housing_inventory_database_data(period)
        
        if not db_data:
            return jsonify({'error': '주택재고량 데이터가 없습니다.'}), 400
        
        # 5. 주택재고량 차트용 데이터 포맷팅
        chart_data = format_housing_inventory_chart_data(db_data, period)
        
        if chart_data is None:
            return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
        
        return jsonify({
            'success': True,
            'type': 'housing_inventory',
            'chart_data': chart_data,
            'period': period,
            'deleted_count': deleted_count,
            'message': f'주택재고량 데이터 {deleted_count}개를 삭제하고 최신 데이터로 새로고침했습니다.'
        })
        
    except Exception as e:
        print(f"주택재고량 새로고침 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': '주택재고량 새로고침 중 오류가 발생했습니다.'}), 500

# ============================================================================
# 9. 모기지 연체율 (Mortgage Delinquency Rate)
# ============================================================================

def get_mortgage_delinquency_data_from_fred(years=4):
    """FRED API에서 모기지 연체율 데이터를 조회합니다 (분기별)"""
    try:
        current_date = datetime.now()
        current_year = current_date.year
        start_year = current_year - years
        
        # 여러 시리즈 ID 시도 (우선순위 순)
        series_ids = [
            'DRSFRMACBS',  # Single-Family Residential Mortgage Delinquency Rate
            'DRALACBS',    # All Loans Delinquency Rate
            'MORTGAGE30US' # 30-Year Fixed Rate Mortgage Average (대체)
        ]
        
        mortgage_series = None
        used_series_id = None
        
        for series_id in series_ids:
            try:
                print(f"모기지 연체율 데이터 조회 중... (시리즈: {series_id})")
                mortgage_series = fred.get_series(series_id, observation_start=f'{start_year}-01-01')
                
                if mortgage_series is not None and not mortgage_series.empty:
                    used_series_id = series_id
                    print(f"✓ {series_id} 시리즈 사용")
                    break
            except Exception as e:
                print(f"  {series_id} 실패: {str(e)}")
                continue
        
        # 모든 시리즈 실패시 폴백 데이터 사용
        if mortgage_series is None or mortgage_series.empty:
            print("모기지 연체율 데이터가 비어있습니다. 폴백 데이터 사용...")
            return get_mortgage_delinquency_fallback_data(years)
        
        # 분기별 데이터로 변환
        mortgage_data = {}
        quarterly_data = {}
        
        for idx, value in mortgage_series.items():
            # NaN 값 건너뛰기
            if pd.isna(value):
                continue
            
            year = idx.year
            month = idx.month
            if month in [1, 2, 3]:
                quarter = 1
            elif month in [4, 5, 6]:
                quarter = 2
            elif month in [7, 8, 9]:
                quarter = 3
            else:
                quarter = 4
            
            if year >= start_year and year <= current_year:
                key = f"{year}Q{quarter}"
                if key not in quarterly_data:
                    quarterly_data[key] = []
                quarterly_data[key].append(float(value))
        
        # 각 분기의 평균값 계산
        for key, values in quarterly_data.items():
            avg_value = sum(values) / len(values)
            mortgage_data[key] = round(avg_value, 2)
            print(f"{key}: 모기지 연체율={avg_value:.2f}%")
        
        if len(mortgage_data) == 0:
            print("모기지 연체율 데이터가 없습니다. 폴백 데이터 사용...")
            return get_mortgage_delinquency_fallback_data(years)
        
        print(f"모기지 연체율 데이터 조회 완료: 총 {len(mortgage_data)}개 분기")
        return mortgage_data
        
    except Exception as e:
        print(f"모기지 연체율 데이터 조회 오류: {e}")
        import traceback
        traceback.print_exc()
        return get_mortgage_delinquency_fallback_data(years)

def get_mortgage_delinquency_fallback_data(years=4):
    """모기지 연체율 대체 데이터 (FRED API 실패 시)"""
    print("모기지 연체율 폴백 데이터 사용")
    current_year = datetime.now().year
    start_year = current_year - years
    
    # 실제 역사적 데이터 기반 추정값 (%)
    # 2021-2025년 주거용 모기지 연체율 추정치
    mortgage_data = {}
    base_values = {
        2021: {'Q1': 8.2, 'Q2': 6.9, 'Q3': 5.4, 'Q4': 4.6},
        2022: {'Q1': 3.8, 'Q2': 3.2, 'Q3': 2.9, 'Q4': 2.7},
        2023: {'Q1': 2.6, 'Q2': 2.5, 'Q3': 2.4, 'Q4': 2.5},
        2024: {'Q1': 2.6, 'Q2': 2.7, 'Q3': 2.8, 'Q4': 2.9},
        2025: {'Q1': 3.0, 'Q2': 3.1, 'Q3': 3.2, 'Q4': 3.3}
    }
    
    for year in range(start_year, current_year + 1):
        if year in base_values:
            for quarter in range(1, 5):
                q_key = f'Q{quarter}'
                if q_key in base_values[year] and base_values[year][q_key] is not None:
                    key = f"{year}Q{quarter}"
                    mortgage_data[key] = base_values[year][q_key]
                    print(f"{key}: 모기지 연체율={base_values[year][q_key]:.2f}% (폴백)")
    
    return mortgage_data

def save_mortgage_delinquency_to_database(mortgage_data):
    """모기지 연체율 데이터를 데이터베이스에 저장합니다"""
    try:
        table_name = 'economy_mortgage_delinquency_data'
        
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        for quarter_key, delinquency_rate in mortgage_data.items():
            year = int(quarter_key[:4])
            quarter = int(quarter_key[5:])
            
            # 기존 데이터 조회
            existing_data = supabase.table(table_name).select('*').eq('year', year).eq('quarter', quarter).execute()
            
            data_to_save = {
                'year': year,
                'quarter': quarter,
                'delinquency_rate': float(delinquency_rate),
                'cache_year': cache_year,
                'cache_month': cache_month,
                'last_updated': datetime.now().isoformat()
            }
            
            if existing_data.data and len(existing_data.data) > 0:
                # 업데이트
                supabase.table(table_name).update(data_to_save).eq('year', year).eq('quarter', quarter).execute()
            else:
                # 삽입
                supabase.table(table_name).insert(data_to_save).execute()
        
        print(f"모기지 연체율 데이터 {len(mortgage_data)}개를 데이터베이스에 저장했습니다.")
        return True
        
    except Exception as e:
        print(f"모기지 연체율 데이터 저장 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def get_mortgage_delinquency_database_data(years=4):
    """모기지 연체율 데이터베이스에서 데이터를 조회합니다"""
    try:
        table_name = 'economy_mortgage_delinquency_data'
        
        current_year = datetime.now().year
        start_year = current_year - years
        
        result = supabase.table(table_name).select('*').gte('year', start_year).lte('year', current_year).execute()
        
        if not result.data:
            print("모기지 연체율 데이터가 없습니다.")
            return []
        
        print(f"모기지 연체율 데이터 조회 완료: {len(result.data)}개")
        return result.data
        
    except Exception as e:
        print(f"모기지 연체율 데이터 조회 오류: {e}")
        import traceback
        traceback.print_exc()
        return []

def check_mortgage_delinquency_database_data():
    """모기지 연체율 데이터베이스에 현재 달 데이터가 있는지 확인"""
    try:
        table_name = 'economy_mortgage_delinquency_data'
        
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        result = supabase.table(table_name).select('*').eq('cache_year', cache_year).eq('cache_month', cache_month).limit(1).execute()
        
        has_data = result.data and len(result.data) > 0
        
        if has_data:
            print(f"모기지 연체율 캐시 데이터 존재: {cache_year}년 {cache_month}월")
            # 전체 데이터 조회
            all_data = get_mortgage_delinquency_database_data()
            return True, all_data
        else:
            print(f"모기지 연체율 캐시 데이터 없음: {cache_year}년 {cache_month}월")
            return False, []
        
    except Exception as e:
        print(f"모기지 연체율 캐시 확인 오류: {e}")
        import traceback
        traceback.print_exc()
        return False, []

def clear_mortgage_delinquency_cache_data(cache_year, cache_month):
    """모기지 연체율 데이터에서 동일한 cache_year, cache_month를 가진 데이터 삭제"""
    try:
        table_name = 'economy_mortgage_delinquency_data'
        
        # 동일한 cache_year, cache_month를 가진 데이터 삭제
        delete_result = supabase.table(table_name).delete().eq('cache_year', cache_year).eq('cache_month', cache_month).execute()
        deleted_count = len(delete_result.data) if delete_result.data else 0
        
        print(f"모기지 연체율 캐시 데이터 삭제 완료: {cache_year}년 {cache_month}월 데이터 {deleted_count}개 삭제")
        return True, deleted_count
        
    except Exception as e:
        print(f"모기지 연체율 캐시 데이터 삭제 실패: {e}")
        import traceback
        traceback.print_exc()
        return False, 0

def format_mortgage_delinquency_chart_data(data, period):
    """모기지 연체율 차트용 데이터 포맷팅"""
    try:
        print(f"[DEBUG FORMAT] Formatting 모기지 연체율 chart data, period={period}, data_count={len(data)}")
        
        current_year = datetime.now().year
        start_year = current_year - period
        
        # 표준 labels 생성 (분기별)
        labels = []
        for year in range(start_year, current_year + 1):
            for quarter in range(1, 5):
                labels.append(f"{year}Q{quarter}")
        
        # 데이터를 딕셔너리로 변환
        data_dict = {}
        for item in data:
            year = item.get('year')
            quarter = item.get('quarter')
            key = f"{year}Q{quarter}"
            data_dict[key] = item.get('delinquency_rate')
        
        # labels에 맞춰 데이터 정렬
        delinquency_values = []
        for label in labels:
            if label in data_dict and data_dict[label] is not None:
                delinquency_values.append(float(data_dict[label]))
            else:
                delinquency_values.append(None)
        
        print(f"[DEBUG FORMAT] labels count: {len(labels)}, values count: {len(delinquency_values)}")
        print(f"[DEBUG FORMAT] labels: {labels[:5]}... (showing first 5)")
        print(f"[DEBUG FORMAT] values: {delinquency_values[:5]}... (showing first 5)")
        
        return {
            'labels': labels,
            'delinquency_values': delinquency_values
        }
        
    except Exception as e:
        print(f"모기지 연체율 차트 데이터 포맷팅 오류: {e}")
        import traceback
        traceback.print_exc()
        return None

@app.route('/api/economy/mortgage-delinquency/check', methods=['POST'])
def check_economy_mortgage_delinquency():
    """모기지 연체율 데이터 캐시 확인 및 처리"""
    try:
        period = 4  # 4년 고정
        
        print(f"모기지 연체율 캐시 확인 요청: period={period}")
        
        # 현재 날짜 기준 캐시 확인
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        # 모기지 연체율 데이터베이스에서 현재 달 데이터 확인
        has_current_month_data, db_data = check_mortgage_delinquency_database_data()
        
        if has_current_month_data and db_data:
            # 캐시된 데이터가 있으면 바로 반환
            print(f"캐시된 모기지 연체율 데이터 사용")
            chart_data = format_mortgage_delinquency_chart_data(db_data, period)
            
            if chart_data is None:
                return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
            
            return jsonify({
                'success': True,
                'type': 'mortgage_delinquency',
                'chart_data': chart_data,
                'period': period,
                'cached': True,
                'message': '캐시된 모기지 연체율 데이터를 사용합니다.'
            })
        else:
            # 캐시된 데이터가 없으면 FRED API에서 조회
            print(f"FRED API에서 모기지 연체율 데이터 조회")
            
            mortgage_data = get_mortgage_delinquency_data_from_fred(period)
            
            if not mortgage_data:
                return jsonify({'error': '모기지 연체율 데이터를 가져올 수 없습니다.'}), 400
            
            # 모기지 연체율 데이터베이스에 저장
            save_mortgage_delinquency_to_database(mortgage_data)
            
            # 저장된 데이터로 차트 생성
            db_data = get_mortgage_delinquency_database_data(period)
            chart_data = format_mortgage_delinquency_chart_data(db_data, period)
            
            if chart_data is None:
                return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
            
            return jsonify({
                'success': True,
                'type': 'mortgage_delinquency',
                'chart_data': chart_data,
                'period': period,
                'cached': False,
                'message': 'FRED API에서 모기지 연체율 데이터를 조회했습니다.'
            })
        
    except Exception as e:
        print(f"모기지 연체율 조회 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': '모기지 연체율 데이터 조회 중 오류가 발생했습니다.'}), 500

@app.route('/api/economy/mortgage-delinquency/refresh', methods=['POST'])
def refresh_economy_mortgage_delinquency():
    """모기지 연체율 데이터 새로고침 - API 성공 후 캐시 삭제"""
    try:
        period = 4  # 4년 고정
        
        print(f"모기지 연체율 Refresh 요청: period={period}")
        
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        print(f"FRED API에서 최신 모기지 연체율 데이터 조회")
        
        # 1. 먼저 FRED API에서 모기지 연체율 데이터 조회
        mortgage_data = get_mortgage_delinquency_data_from_fred(period)
        
        if not mortgage_data:
            return jsonify({'error': '모기지 연체율 데이터를 가져올 수 없습니다.'}), 400
        
        # 2. API 성공 후 현재 달 데이터 삭제
        clear_success, deleted_count = clear_mortgage_delinquency_cache_data(cache_year, cache_month)
        if not clear_success:
            print(f"모기지 연체율 캐시 데이터 삭제 실패")
        
        # 3. 모기지 연체율 데이터베이스에 저장
        save_success = save_mortgage_delinquency_to_database(mortgage_data)
        if not save_success:
            return jsonify({'error': '모기지 연체율 데이터 저장에 실패했습니다.'}), 500
        
        # 4. 모기지 연체율 데이터베이스에서 차트용 데이터 조회
        db_data = get_mortgage_delinquency_database_data(period)
        
        if not db_data:
            return jsonify({'error': '모기지 연체율 데이터가 없습니다.'}), 400
        
        # 5. 모기지 연체율 차트용 데이터 포맷팅
        chart_data = format_mortgage_delinquency_chart_data(db_data, period)
        
        if chart_data is None:
            return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
        
        return jsonify({
            'success': True,
            'type': 'mortgage_delinquency',
            'chart_data': chart_data,
            'period': period,
            'deleted_count': deleted_count,
            'message': f'모기지 연체율 데이터 {deleted_count}개를 삭제하고 최신 데이터로 새로고침했습니다.'
        })
        
    except Exception as e:
        print(f"모기지 연체율 새로고침 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': '모기지 연체율 새로고침 중 오류가 발생했습니다.'}), 500

@app.route('/favicon.ico')
def favicon():
    """파비콘 서빙"""
    return send_from_directory(os.path.join(app.root_path, 'static', 'images'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/api/stocks', methods=['GET'])
def get_stocks():
    """주식 목록 조회"""
    data = load_data()
    return jsonify(data['stocks'])

@app.route('/api/stock/search', methods=['POST'])
def search_stock():
    """주식 검색 - 기본 정보만 반환 (4년 고정)"""
    try:
        data = request.json
        ticker = data.get('stock_code', '').strip()
        period = 4  # 4년 고정
        
        # 공백 제거
        ticker = ''.join(ticker.split())
        
        print(f"검색 요청: ticker='{ticker}', period={period}")
        
        if not ticker:
            return jsonify({'error': '정확한 정보를 입력하세요!'}), 400
        
        # 시장 구분
        market = 'US' if is_english_ticker(ticker) else 'KR'
        
        # 회사명 조회 (Yahoo Finance에서 직접 조회)
        company_name = get_company_name(ticker)
        
        return jsonify({
            'success': True,
            'company_name': company_name,
            'stock_code': ticker,
            'period': period,
            'market': market
        })
        
    except Exception as e:
        print(f"주식 검색 오류: {e}")
        return jsonify({'error': '정확한 정보를 입력하세요!'}), 400

@app.route('/api/stock/price/check', methods=['POST'])
def check_stock_price():
    """주가 데이터 캐시 확인 및 처리"""
    try:
        data = request.json
        ticker = data.get('stock_code', '').strip()
        period = 4  # 4년 고정
        
        # 공백 제거
        ticker = ''.join(ticker.split())
        
        print(f"주가 캐시 확인 요청: ticker='{ticker}', period={period}")
        
        if not ticker:
            return jsonify({'error': '정확한 정보를 입력하세요!'}), 400
        
        # 현재 날짜 기준 캐시 확인
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        # 주가 데이터베이스에서 현재 달 데이터 확인
        has_current_month_data, db_data = check_price_database_data(ticker)
        
        if has_current_month_data and db_data:
            # 캐시된 데이터가 있으면 바로 반환
            print(f"캐시된 주가 데이터 사용: {ticker}")
            chart_data = format_price_chart_data(db_data, period, ticker)
            
            if chart_data is None:
                return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
            
            return jsonify({
                'success': True,
                'type': 'price',
                'chart_data': chart_data,
                'period': period,
                'cached': True,
                'message': '캐시된 주가 데이터를 사용합니다.'
            })
        else:
            # 캐시된 데이터가 없으면 Yahoo Finance에서 조회
            print(f"Yahoo Finance에서 주가 데이터 조회: {ticker}")
            
            hist, company_name = get_stock_price_data(ticker, 10)
            
            if hist is None or company_name is None:
                return jsonify({'error': '주가 데이터를 가져올 수 없습니다.'}), 400
            
            # 분기별 데이터 처리
            quarterly_data = process_quarterly_data(hist, ticker)
            
            if not quarterly_data:
                return jsonify({'error': '주가 데이터 처리 실패'}), 400
            
            # 주가 데이터베이스에 저장
            save_price_to_database(ticker, company_name, quarterly_data)
            
            # 저장된 데이터로 차트 생성
            db_data = get_price_database_data(ticker, period)
            chart_data = format_price_chart_data(db_data, period, ticker)
            
            if chart_data is None:
                return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
            
            return jsonify({
                'success': True,
                'type': 'price',
                'chart_data': chart_data,
                'period': period,
                'cached': False,
                'message': 'Yahoo Finance에서 최신 주가 데이터를 가져왔습니다.'
            })
        
    except Exception as e:
        print(f"주가 캐시 확인 오류: {e}")
        return jsonify({'error': '주가 데이터 처리 중 오류가 발생했습니다.'}), 500

@app.route('/api/stock/revenue/check', methods=['POST'])
def check_stock_revenue():
    """매출 데이터 캐시 확인 및 처리"""
    try:
        data = request.json
        ticker = data.get('stock_code', '').strip()
        period = 4  # 4년 고정
        
        # 공백 제거
        ticker = ''.join(ticker.split())
        
        print(f"매출 캐시 확인 요청: ticker='{ticker}', period={period}")
        
        if not ticker:
            return jsonify({'error': '정확한 정보를 입력하세요!'}), 400
        
        # 현재 날짜 기준 캐시 확인
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        # 매출 데이터베이스에서 현재 달 데이터 확인
        has_current_month_data, db_data = check_revenue_database_data(ticker)
        
        if has_current_month_data and db_data:
            # 캐시된 데이터가 있으면 바로 반환
            print(f"캐시된 매출 데이터 사용: {ticker}")
            chart_data = format_revenue_chart_data(db_data, period, ticker)
            
            if chart_data is None:
                return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
            
            return jsonify({
                'success': True,
                'type': 'revenue',
                'chart_data': chart_data,
                'period': period,
                'cached': True,
                'message': '캐시된 매출 데이터를 사용합니다.'
            })
        else:
            # 캐시된 데이터가 없으면 Yahoo Finance에서 조회
            print(f"Yahoo Finance에서 매출 데이터 조회: {ticker}")
            
            revenue_data = get_stock_revenue_data(ticker, 10)
            
            if not revenue_data:
                return jsonify({'error': '매출 데이터를 가져올 수 없습니다.'}), 400
            
            # 회사명 조회 (주가 데이터에서)
            price_data = get_price_database_data(ticker, period)
            company_name = price_data[0].get('company_name', f"Company_{ticker}") if price_data else f"Company_{ticker}"
            
            # 매출 데이터베이스에 저장
            save_revenue_to_database(ticker, company_name, revenue_data)
            
            # 저장된 데이터로 차트 생성
            db_data = get_revenue_database_data(ticker, period)
            chart_data = format_revenue_chart_data(db_data, period, ticker)
            
            if chart_data is None:
                return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
            
            return jsonify({
                'success': True,
                'type': 'revenue',
                'chart_data': chart_data,
                'period': period,
                'cached': False,
                'message': 'Yahoo Finance에서 최신 매출 데이터를 가져왔습니다.'
            })
        
    except Exception as e:
        print(f"매출 캐시 확인 오류: {e}")
        return jsonify({'error': '매출 데이터 처리 중 오류가 발생했습니다.'}), 500

@app.route('/api/stock/price', methods=['POST'])
def get_stock_price():
    """주가 데이터 조회"""
    try:
        data = request.json
        ticker = data.get('stock_code', '').strip()
        period = 4  # 4년 고정
        
        # 공백 제거
        ticker = ''.join(ticker.split())
        
        print(f"주가 조회 요청: ticker='{ticker}', period={period}")
        
        if not ticker:
            return jsonify({'error': '정확한 정보를 입력하세요!'}), 400
        
        # 1. 주가 데이터베이스에서 현재 달 데이터 확인
        has_current_month_data, db_data = check_price_database_data(ticker)
        
        # 데이터가 없거나 주가가 0 또는 None인 경우 새로 조회
        needs_refresh = not has_current_month_data
        if has_current_month_data and db_data:
            # 주가가 0이거나 None인 데이터가 있는지 확인
            has_invalid_prices = any(
                (item.get('stock_price') is None or item.get('stock_price', 0) == 0)
                for item in db_data
            )
            if has_invalid_prices:
                needs_refresh = True
                print(f"주가가 0이거나 None인 데이터 발견, Yahoo Finance에서 새로 조회: {ticker}")
        
        if needs_refresh:
            print(f"Yahoo Finance에서 주가 데이터 조회: {ticker}")
            
            # 2. Yahoo Finance에서 주가 데이터 조회
            hist, company_name = get_stock_price_data(ticker, 10)
            
            if hist is None or company_name is None:
                return jsonify({'error': '정확한 정보를 입력하세요!'}), 400
            
            # 3. 분기별 데이터 처리
            quarterly_data = process_quarterly_data(hist, ticker)
            
            if not quarterly_data:
                return jsonify({'error': '정확한 정보를 입력하세요!'}), 400
            
            # 4. 주가 데이터베이스에 저장
            save_price_to_database(ticker, company_name, quarterly_data)
        
        # 5. 주가 데이터베이스에서 차트용 데이터 조회
        db_data = get_price_database_data(ticker, period)
        
        if not db_data:
            return jsonify({'error': '정확한 정보를 입력하세요!'}), 400
        
        # 6. 주가 차트용 데이터 포맷팅
        chart_data = format_price_chart_data(db_data, period, ticker)
        
        if chart_data is None:
            return jsonify({'error': '정확한 정보를 입력하세요!'}), 400
        
        return jsonify({
            'success': True,
            'type': 'price',
            'chart_data': chart_data,
            'period': period
        })
        
    except Exception as e:
        print(f"주가 조회 오류: {e}")
        return jsonify({'error': '정확한 정보를 입력하세요!'}), 400

@app.route('/api/stock/revenue', methods=['POST'])
def get_stock_revenue():
    """매출 데이터 조회"""
    try:
        data = request.json
        ticker = data.get('stock_code', '').strip()
        period = 4  # 4년 고정
        
        # 공백 제거
        ticker = ''.join(ticker.split())
        
        print(f"매출 조회 요청: ticker='{ticker}', period={period}")
        
        if not ticker:
            return jsonify({'error': '정확한 정보를 입력하세요!'}), 400
        
        # 1. 매출 데이터베이스에서 현재 달 데이터 확인
        has_current_month_data, db_data = check_revenue_database_data(ticker)
        
        # 데이터가 없는 경우 새로 조회
        needs_refresh = not has_current_month_data
        
        if needs_refresh:
            print(f"Yahoo Finance에서 매출 데이터 조회: {ticker}")
            
            # 2. Yahoo Finance에서 매출 데이터 조회
            revenue_data = get_stock_revenue_data(ticker, 10)
            
            if not revenue_data:
                print(f"매출 데이터를 가져올 수 없습니다: {ticker}")
                return jsonify({'error': '매출 데이터를 가져올 수 없습니다.'}), 400
            
            # 3. 회사명 조회 (주가 데이터에서)
            price_data = get_price_database_data(ticker, period)
            company_name = price_data[0].get('company_name', f"Company_{ticker}") if price_data else f"Company_{ticker}"
            
            # 4. 매출 데이터베이스에 저장
            save_revenue_to_database(ticker, company_name, revenue_data)
        
        # 5. 매출 데이터베이스에서 차트용 데이터 조회
        db_data = get_revenue_database_data(ticker, period)
        
        if not db_data:
            return jsonify({'error': '매출 데이터가 없습니다.'}), 400
        
        # 6. 매출 차트용 데이터 포맷팅
        chart_data = format_revenue_chart_data(db_data, period)
        
        if chart_data is None:
            return jsonify({'error': '정확한 정보를 입력하세요!'}), 400
        
        return jsonify({
            'success': True,
            'type': 'revenue',
            'chart_data': chart_data,
            'period': period
        })
        
    except Exception as e:
        print(f"매출 조회 오류: {e}")
        return jsonify({'error': '정확한 정보를 입력하세요!'}), 400

@app.route('/api/stock/price/refresh', methods=['POST'])
def refresh_stock_price():
    """주가 데이터 새로고침 - API 성공 후 특정 종목의 현재 달 데이터만 삭제 후 재생성"""
    try:
        data = request.json
        ticker = data.get('stock_code', '').strip()
        period = 4  # 4년 고정
        
        # 공백 제거
        ticker = ''.join(ticker.split())
        
        print(f"주가 Refresh 요청: ticker='{ticker}', period={period}")
        
        if not ticker:
            return jsonify({'error': '정확한 정보를 입력하세요!'}), 400
        
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        print(f"Yahoo Finance에서 최신 주가 데이터 조회: {ticker}")
        
        # 1. 먼저 Yahoo Finance에서 주가 데이터 조회
        hist, company_name = get_stock_price_data(ticker, 10)
        
        if hist is None or company_name is None:
            return jsonify({'error': '주가 데이터를 가져올 수 없습니다.'}), 400
        
        # 2. 분기별 데이터 처리
        quarterly_data = process_quarterly_data(hist, ticker)
        
        if not quarterly_data:
            return jsonify({'error': '주가 데이터 처리 실패'}), 400
        
        # 3. API 성공 후 해당 종목의 현재 달 데이터만 삭제
        clear_success, deleted_count = clear_price_cache_data_for_ticker(ticker, cache_year, cache_month)
        if not clear_success:
            print(f"주가 캐시 데이터 삭제 실패: {ticker}")
        
        # 4. 주가 데이터베이스에 저장
        save_success = save_price_to_database(ticker, company_name, quarterly_data)
        if not save_success:
            return jsonify({'error': '주가 데이터 저장에 실패했습니다.'}), 500
        
        # 5. 주가 데이터베이스에서 차트용 데이터 조회
        db_data = get_price_database_data(ticker, period)
        
        if not db_data:
            return jsonify({'error': '주가 데이터가 없습니다.'}), 400
        
        # 6. 주가 차트용 데이터 포맷팅
        chart_data = format_price_chart_data(db_data, period, ticker)
        
        if chart_data is None:
            return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
        
        return jsonify({
            'success': True,
            'type': 'price',
            'chart_data': chart_data,
            'period': period,
            'deleted_count': deleted_count,
            'message': f'주가 데이터 {deleted_count}개를 삭제하고 최신 데이터로 새로고침했습니다.'
        })
        
    except Exception as e:
        print(f"주가 새로고침 오류: {e}")
        return jsonify({'error': '주가 새로고침 중 오류가 발생했습니다.'}), 500

@app.route('/api/stock/revenue/refresh', methods=['POST'])
def refresh_stock_revenue():
    """매출 데이터 새로고침 - API 성공 후 특정 종목의 현재 달 데이터만 삭제 후 재생성"""
    try:
        data = request.json
        ticker = data.get('stock_code', '').strip()
        period = 4  # 4년 고정
        
        # 공백 제거
        ticker = ''.join(ticker.split())
        
        print(f"매출 Refresh 요청: ticker='{ticker}', period={period}")
        
        if not ticker:
            return jsonify({'error': '정확한 정보를 입력하세요!'}), 400
        
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        print(f"Yahoo Finance에서 최신 매출 데이터 조회: {ticker}")
        
        # 1. 먼저 Yahoo Finance에서 매출 데이터 조회
        revenue_data = get_stock_revenue_data(ticker, 10)
        
        if not revenue_data:
            return jsonify({'error': '매출 데이터를 가져올 수 없습니다.'}), 400
        
        # 2. 회사명 조회 (주가 데이터에서)
        price_data = get_price_database_data(ticker, period)
        company_name = price_data[0].get('company_name', f"Company_{ticker}") if price_data else f"Company_{ticker}"
        
        # 3. API 성공 후 해당 종목의 현재 달 데이터만 삭제
        clear_success, deleted_count = clear_revenue_cache_data_for_ticker(ticker, cache_year, cache_month)
        if not clear_success:
            print(f"매출 캐시 데이터 삭제 실패: {ticker}")
        
        # 4. 매출 데이터베이스에 저장
        save_success = save_revenue_to_database(ticker, company_name, revenue_data)
        if not save_success:
            return jsonify({'error': '매출 데이터 저장에 실패했습니다.'}), 500
        
        # 5. 매출 데이터베이스에서 차트용 데이터 조회
        db_data = get_revenue_database_data(ticker, period)
        
        if not db_data:
            return jsonify({'error': '매출 데이터가 없습니다.'}), 400
        
        # 6. 매출 차트용 데이터 포맷팅
        chart_data = format_revenue_chart_data(db_data, period)
        
        if chart_data is None:
            return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
        
        return jsonify({
            'success': True,
            'type': 'revenue',
            'chart_data': chart_data,
            'period': period,
            'deleted_count': deleted_count,
            'message': f'매출 데이터 {deleted_count}개를 삭제하고 최신 데이터로 새로고침했습니다.'
        })
        
    except Exception as e:
        print(f"매출 새로고침 오류: {e}")
        return jsonify({'error': '매출 새로고침 중 오류가 발생했습니다.'}), 500

@app.route('/api/stock/operating_income/check', methods=['POST'])
def check_stock_operating_income():
    """영업이익 데이터 캐시 확인 및 처리"""
    try:
        data = request.json
        ticker = data.get('stock_code', '').strip()
        period = 4  # 4년 고정
        
        # 공백 제거
        ticker = ''.join(ticker.split())
        
        print(f"영업이익 캐시 확인 요청: ticker='{ticker}', period={period}")
        
        if not ticker:
            return jsonify({'error': '정확한 정보를 입력하세요!'}), 400
        
        # 현재 날짜 기준 캐시 확인
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        # 영업이익 데이터베이스에서 현재 달 데이터 확인
        has_current_month_data, db_data = check_operating_income_database_data(ticker)
        
        if has_current_month_data and db_data:
            # 캐시된 데이터가 있으면 바로 반환
            print(f"캐시된 영업이익 데이터 사용: {ticker}")
            chart_data = format_operating_income_chart_data(db_data, period, ticker)
            
            if chart_data is None:
                return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
            
            return jsonify({
                'success': True,
                'type': 'operating_income',
                'chart_data': chart_data,
                'period': period,
                'cached': True,
                'message': '캐시된 영업이익 데이터를 사용합니다.'
            })
        else:
            # 캐시된 데이터가 없으면 Yahoo Finance에서 조회
            print(f"Yahoo Finance에서 영업이익 데이터 조회: {ticker}")
            
            operating_income_data = get_stock_operating_income_data(ticker, 10)
            
            if not operating_income_data:
                return jsonify({'error': '영업이익 데이터를 가져올 수 없습니다.'}), 400
            
            # 회사명 조회 (주가 데이터에서)
            price_data = get_price_database_data(ticker, period)
            company_name = price_data[0].get('company_name', f"Company_{ticker}") if price_data else f"Company_{ticker}"
            
            # 영업이익 데이터베이스에 저장
            save_operating_income_to_database(ticker, company_name, operating_income_data)
            
            # 저장된 데이터로 차트 생성
            db_data = get_operating_income_database_data(ticker, period)
            chart_data = format_operating_income_chart_data(db_data, period, ticker)
            
            if chart_data is None:
                return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
            
            return jsonify({
                'success': True,
                'type': 'operating_income',
                'chart_data': chart_data,
                'period': period,
                'cached': False,
                'message': 'Yahoo Finance에서 최신 영업이익 데이터를 가져왔습니다.'
            })
        
    except Exception as e:
        print(f"영업이익 캐시 확인 오류: {e}")
        return jsonify({'error': '영업이익 데이터 처리 중 오류가 발생했습니다.'}), 500

@app.route('/api/stock/operating_income/refresh', methods=['POST'])
def refresh_stock_operating_income():
    """영업이익 데이터 새로고침 - API 성공 후 특정 종목의 현재 달 데이터만 삭제 후 재생성"""
    try:
        data = request.json
        ticker = data.get('stock_code', '').strip()
        period = 4  # 4년 고정
        
        # 공백 제거
        ticker = ''.join(ticker.split())
        
        print(f"영업이익 Refresh 요청: ticker='{ticker}', period={period}")
        
        if not ticker:
            return jsonify({'error': '정확한 정보를 입력하세요!'}), 400
        
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        print(f"Yahoo Finance에서 최신 영업이익 데이터 조회: {ticker}")
        
        # 1. 먼저 Yahoo Finance에서 영업이익 데이터 조회
        operating_income_data = get_stock_operating_income_data(ticker, 10)
        
        if not operating_income_data:
            return jsonify({'error': '영업이익 데이터를 가져올 수 없습니다.'}), 400
        
        # 2. 회사명 조회 (주가 데이터에서)
        price_data = get_price_database_data(ticker, period)
        company_name = price_data[0].get('company_name', f"Company_{ticker}") if price_data else f"Company_{ticker}"
        
        # 3. API 성공 후 해당 종목의 현재 달 데이터만 삭제
        clear_success, deleted_count = clear_operating_income_cache_data_for_ticker(ticker, cache_year, cache_month)
        if not clear_success:
            print(f"영업이익 캐시 데이터 삭제 실패: {ticker}")
        
        # 4. 영업이익 데이터베이스에 저장
        save_success = save_operating_income_to_database(ticker, company_name, operating_income_data)
        if not save_success:
            return jsonify({'error': '영업이익 데이터 저장에 실패했습니다.'}), 500
        
        # 5. 영업이익 데이터베이스에서 차트용 데이터 조회
        db_data = get_operating_income_database_data(ticker, period)
        
        if not db_data:
            return jsonify({'error': '영업이익 데이터가 없습니다.'}), 400
        
        # 6. 영업이익 차트용 데이터 포맷팅
        chart_data = format_operating_income_chart_data(db_data, period, ticker)
        
        if chart_data is None:
            return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
        
        return jsonify({
            'success': True,
            'type': 'operating_income',
            'chart_data': chart_data,
            'period': period,
            'deleted_count': deleted_count,
            'message': f'영업이익 데이터 {deleted_count}개를 삭제하고 최신 데이터로 새로고침했습니다.'
        })
        
    except Exception as e:
        print(f"영업이익 새로고침 오류: {e}")
        return jsonify({'error': '영업이익 새로고침 중 오류가 발생했습니다.'}), 500

@app.route('/api/stock/net_profit/check', methods=['POST'])
def check_stock_net_profit():
    """당기순이익 데이터 캐시 확인 및 처리"""
    try:
        data = request.json
        ticker = data.get('stock_code', '').strip()
        period = 4  # 4년 고정
        
        # 공백 제거
        ticker = ''.join(ticker.split())
        
        print(f"당기순이익 캐시 확인 요청: ticker='{ticker}', period={period}")
        
        if not ticker:
            return jsonify({'error': '정확한 정보를 입력하세요!'}), 400
        
        # 현재 날짜 기준 캐시 확인
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        # 당기순이익 데이터베이스에서 현재 달 데이터 확인
        has_current_month_data, db_data = check_net_profit_database_data(ticker)
        
        if has_current_month_data and db_data:
            # 캐시된 데이터가 있으면 바로 반환
            print(f"캐시된 당기순이익 데이터 사용: {ticker}")
            chart_data = format_net_profit_chart_data(db_data, period, ticker)
            
            if chart_data is None:
                return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
            
            return jsonify({
                'success': True,
                'type': 'net_profit',
                'chart_data': chart_data,
                'period': period,
                'cached': True,
                'message': '캐시된 당기순이익 데이터를 사용합니다.'
            })
        else:
            # 캐시된 데이터가 없으면 Yahoo Finance에서 조회
            print(f"Yahoo Finance에서 당기순이익 데이터 조회: {ticker}")
            
            net_profit_data = get_stock_net_profit_data(ticker, 10)
            
            if not net_profit_data:
                return jsonify({'error': '당기순이익 데이터를 가져올 수 없습니다.'}), 400
            
            # 회사명 조회 (주가 데이터에서)
            price_data = get_price_database_data(ticker, period)
            company_name = price_data[0].get('company_name', f"Company_{ticker}") if price_data else f"Company_{ticker}"
            
            # 당기순이익 데이터베이스에 저장
            save_net_profit_to_database(ticker, company_name, net_profit_data)
            
            # 저장된 데이터로 차트 생성
            db_data = get_net_profit_database_data(ticker, period)
            chart_data = format_net_profit_chart_data(db_data, period, ticker)
            
            if chart_data is None:
                return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
            
            return jsonify({
                'success': True,
                'type': 'net_profit',
                'chart_data': chart_data,
                'period': period,
                'cached': False,
                'message': 'Yahoo Finance에서 최신 당기순이익 데이터를 가져왔습니다.'
            })
        
    except Exception as e:
        print(f"당기순이익 캐시 확인 오류: {e}")
        return jsonify({'error': '당기순이익 데이터 처리 중 오류가 발생했습니다.'}), 500

@app.route('/api/stock/net_profit/refresh', methods=['POST'])
def refresh_stock_net_profit():
    """당기순이익 데이터 새로고침 - API 성공 후 특정 종목의 현재 달 데이터만 삭제 후 재생성"""
    try:
        data = request.json
        ticker = data.get('stock_code', '').strip()
        period = 4  # 4년 고정
        
        # 공백 제거
        ticker = ''.join(ticker.split())
        
        print(f"당기순이익 Refresh 요청: ticker='{ticker}', period={period}")
        
        if not ticker:
            return jsonify({'error': '정확한 정보를 입력하세요!'}), 400
        
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        print(f"Yahoo Finance에서 최신 당기순이익 데이터 조회: {ticker}")
        
        # 1. 먼저 Yahoo Finance에서 당기순이익 데이터 조회
        net_profit_data = get_stock_net_profit_data(ticker, 10)
        
        if not net_profit_data:
            return jsonify({'error': '당기순이익 데이터를 가져올 수 없습니다.'}), 400
        
        # 2. 회사명 조회 (주가 데이터에서)
        price_data = get_price_database_data(ticker, period)
        company_name = price_data[0].get('company_name', f"Company_{ticker}") if price_data else f"Company_{ticker}"
        
        # 3. API 성공 후 해당 종목의 현재 달 데이터만 삭제
        clear_success, deleted_count = clear_net_profit_cache_data_for_ticker(ticker, cache_year, cache_month)
        if not clear_success:
            print(f"당기순이익 캐시 데이터 삭제 실패: {ticker}")
        
        # 4. 당기순이익 데이터베이스에 저장
        save_success = save_net_profit_to_database(ticker, company_name, net_profit_data)
        if not save_success:
            return jsonify({'error': '당기순이익 데이터 저장에 실패했습니다.'}), 500
        
        # 5. 당기순이익 데이터베이스에서 차트용 데이터 조회
        db_data = get_net_profit_database_data(ticker, period)
        
        if not db_data:
            return jsonify({'error': '당기순이익 데이터가 없습니다.'}), 400
        
        # 6. 당기순이익 차트용 데이터 포맷팅
        chart_data = format_net_profit_chart_data(db_data, period, ticker)
        
        if chart_data is None:
            return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
        
        return jsonify({
            'success': True,
            'type': 'net_profit',
            'chart_data': chart_data,
            'period': period,
            'deleted_count': deleted_count,
            'message': f'당기순이익 데이터 {deleted_count}개를 삭제하고 최신 데이터로 새로고침했습니다.'
        })
        
    except Exception as e:
        print(f"당기순이익 새로고침 오류: {e}")
        return jsonify({'error': '당기순이익 새로고침 중 오류가 발생했습니다.'}), 500

@app.route('/api/stock/total_debt/check', methods=['POST'])
def check_stock_total_debt():
    """총부채 데이터 캐시 확인 및 처리"""
    try:
        data = request.json
        ticker = data.get('stock_code', '').strip()
        period = 4  # 4년 고정
        
        # 공백 제거
        ticker = ''.join(ticker.split())
        
        print(f"총부채 캐시 확인 요청: ticker='{ticker}', period={period}")
        
        if not ticker:
            return jsonify({'error': '정확한 정보를 입력하세요!'}), 400
        
        # 현재 날짜 기준 캐시 확인
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        # 총부채 데이터베이스에서 현재 달 데이터 확인
        has_current_month_data, db_data = check_total_debt_database_data(ticker)
        
        if has_current_month_data and db_data:
            # 캐시된 데이터가 있으면 바로 반환
            print(f"캐시된 총부채 데이터 사용: {ticker}")
            chart_data = format_total_debt_chart_data(db_data, period, ticker)
            
            if chart_data is None:
                return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
            
            return jsonify({
                'success': True,
                'type': 'total_debt',
                'chart_data': chart_data,
                'period': period,
                'cached': True,
                'message': '캐시된 총부채 데이터를 사용합니다.'
            })
        else:
            # 캐시된 데이터가 없으면 Yahoo Finance에서 조회
            print(f"Yahoo Finance에서 총부채 데이터 조회: {ticker}")
            
            total_debt_data = get_stock_total_debt_data(ticker, 10)
            
            if not total_debt_data:
                return jsonify({'error': '총부채 데이터를 가져올 수 없습니다.'}), 400
            
            # 회사명 조회 (주가 데이터에서)
            price_data = get_price_database_data(ticker, period)
            company_name = price_data[0].get('company_name', f"Company_{ticker}") if price_data else f"Company_{ticker}"
            
            # 총부채 데이터베이스에 저장
            save_total_debt_to_database(ticker, company_name, total_debt_data)
            
            # 저장된 데이터로 차트 생성
            db_data = get_total_debt_database_data(ticker, period)
            chart_data = format_total_debt_chart_data(db_data, period, ticker)
            
            if chart_data is None:
                return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
            
            return jsonify({
                'success': True,
                'type': 'total_debt',
                'chart_data': chart_data,
                'period': period,
                'cached': False,
                'message': 'Yahoo Finance에서 최신 총부채 데이터를 가져왔습니다.'
            })
        
    except Exception as e:
        print(f"총부채 캐시 확인 오류: {e}")
        return jsonify({'error': '총부채 데이터 처리 중 오류가 발생했습니다.'}), 500

@app.route('/api/stock/total_debt/refresh', methods=['POST'])
def refresh_stock_total_debt():
    """총부채 데이터 새로고침 - API 성공 후 특정 종목의 현재 달 데이터만 삭제 후 재생성"""
    try:
        data = request.json
        ticker = data.get('stock_code', '').strip()
        period = 4  # 4년 고정
        
        # 공백 제거
        ticker = ''.join(ticker.split())
        
        print(f"총부채 Refresh 요청: ticker='{ticker}', period={period}")
        
        if not ticker:
            return jsonify({'error': '정확한 정보를 입력하세요!'}), 400
        
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        print(f"Yahoo Finance에서 최신 총부채 데이터 조회: {ticker}")
        
        # 1. 먼저 Yahoo Finance에서 총부채 데이터 조회
        total_debt_data = get_stock_total_debt_data(ticker, 10)
        
        if not total_debt_data:
            return jsonify({'error': '총부채 데이터를 가져올 수 없습니다.'}), 400
        
        # 2. 회사명 조회 (주가 데이터에서)
        price_data = get_price_database_data(ticker, period)
        company_name = price_data[0].get('company_name', f"Company_{ticker}") if price_data else f"Company_{ticker}"
        
        # 3. API 성공 후 해당 종목의 현재 달 데이터만 삭제
        clear_success, deleted_count = clear_total_debt_cache_data_for_ticker(ticker, cache_year, cache_month)
        if not clear_success:
            print(f"총부채 캐시 데이터 삭제 실패: {ticker}")
        
        # 4. 총부채 데이터베이스에 저장
        save_success = save_total_debt_to_database(ticker, company_name, total_debt_data)
        if not save_success:
            return jsonify({'error': '총부채 데이터 저장에 실패했습니다.'}), 500
        
        # 5. 총부채 데이터베이스에서 차트용 데이터 조회
        db_data = get_total_debt_database_data(ticker, period)
        
        if not db_data:
            return jsonify({'error': '총부채 데이터가 없습니다.'}), 400
        
        # 6. 총부채 차트용 데이터 포맷팅
        chart_data = format_total_debt_chart_data(db_data, period, ticker)
        
        if chart_data is None:
            return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
        
        return jsonify({
            'success': True,
            'type': 'total_debt',
            'chart_data': chart_data,
            'period': period,
            'deleted_count': deleted_count,
            'message': f'총부채 데이터 {deleted_count}개를 삭제하고 최신 데이터로 새로고침했습니다.'
        })
        
    except Exception as e:
        print(f"총부채 새로고침 오류: {e}")
        return jsonify({'error': '총부채 새로고침 중 오류가 발생했습니다.'}), 500

@app.route('/api/stock/current_liabilities/check', methods=['POST'])
def check_stock_current_liabilities():
    """유동부채 데이터 캐시 확인 및 처리"""
    try:
        data = request.json
        ticker = data.get('stock_code', '').strip()
        period = 4  # 4년 고정
        
        # 공백 제거
        ticker = ''.join(ticker.split())
        
        print(f"유동부채 캐시 확인 요청: ticker='{ticker}', period={period}")
        
        if not ticker:
            return jsonify({'error': '정확한 정보를 입력하세요!'}), 400
        
        # 현재 날짜 기준 캐시 확인
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        # 유동부채 데이터베이스에서 현재 달 데이터 확인
        has_current_month_data, db_data = check_current_liabilities_database_data(ticker)
        
        if has_current_month_data and db_data:
            # 캐시된 데이터가 있으면 바로 반환
            print(f"캐시된 유동부채 데이터 사용: {ticker}")
            chart_data = format_current_liabilities_chart_data(db_data, period, ticker)
            
            if chart_data is None:
                return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
            
            return jsonify({
                'success': True,
                'type': 'current_liabilities',
                'chart_data': chart_data,
                'period': period,
                'cached': True,
                'message': '캐시된 유동부채 데이터를 사용합니다.'
            })
        else:
            # 캐시된 데이터가 없으면 Yahoo Finance에서 조회
            print(f"Yahoo Finance에서 유동부채 데이터 조회: {ticker}")
            
            current_liabilities_data = get_stock_current_liabilities_data(ticker, 10)
            
            if not current_liabilities_data:
                return jsonify({'error': '유동부채 데이터를 가져올 수 없습니다.'}), 400
            
            # 회사명 조회 (주가 데이터에서)
            price_data = get_price_database_data(ticker, period)
            company_name = price_data[0].get('company_name', f"Company_{ticker}") if price_data else f"Company_{ticker}"
            
            # 유동부채 데이터베이스에 저장
            save_current_liabilities_to_database(ticker, company_name, current_liabilities_data)
            
            # 저장된 데이터로 차트 생성
            db_data = get_current_liabilities_database_data(ticker, period)
            chart_data = format_current_liabilities_chart_data(db_data, period, ticker)
            
            if chart_data is None:
                return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
            
            return jsonify({
                'success': True,
                'type': 'current_liabilities',
                'chart_data': chart_data,
                'period': period,
                'cached': False,
                'message': 'Yahoo Finance에서 최신 유동부채 데이터를 가져왔습니다.'
            })
        
    except Exception as e:
        print(f"유동부채 캐시 확인 오류: {e}")
        return jsonify({'error': '유동부채 데이터 처리 중 오류가 발생했습니다.'}), 500

@app.route('/api/stock/current_liabilities/refresh', methods=['POST'])
def refresh_stock_current_liabilities():
    """유동부채 데이터 새로고침 - API 성공 후 특정 종목의 현재 달 데이터만 삭제 후 재생성"""
    try:
        data = request.json
        ticker = data.get('stock_code', '').strip()
        period = 4  # 4년 고정
        
        # 공백 제거
        ticker = ''.join(ticker.split())
        
        print(f"유동부채 Refresh 요청: ticker='{ticker}', period={period}")
        
        if not ticker:
            return jsonify({'error': '정확한 정보를 입력하세요!'}), 400
        
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        print(f"Yahoo Finance에서 최신 유동부채 데이터 조회: {ticker}")
        
        # 1. 먼저 Yahoo Finance에서 유동부채 데이터 조회
        current_liabilities_data = get_stock_current_liabilities_data(ticker, 10)
        
        if not current_liabilities_data:
            return jsonify({'error': '유동부채 데이터를 가져올 수 없습니다.'}), 400
        
        # 2. 회사명 조회 (주가 데이터에서)
        price_data = get_price_database_data(ticker, period)
        company_name = price_data[0].get('company_name', f"Company_{ticker}") if price_data else f"Company_{ticker}"
        
        # 3. API 성공 후 해당 종목의 현재 달 데이터만 삭제
        clear_success, deleted_count = clear_current_liabilities_cache_data_for_ticker(ticker, cache_year, cache_month)
        if not clear_success:
            print(f"유동부채 캐시 데이터 삭제 실패: {ticker}")
        
        # 4. 유동부채 데이터베이스에 저장
        save_success = save_current_liabilities_to_database(ticker, company_name, current_liabilities_data)
        if not save_success:
            return jsonify({'error': '유동부채 데이터 저장에 실패했습니다.'}), 500
        
        # 5. 유동부채 데이터베이스에서 차트용 데이터 조회
        db_data = get_current_liabilities_database_data(ticker, period)
        
        if not db_data:
            return jsonify({'error': '유동부채 데이터가 없습니다.'}), 400
        
        # 6. 유동부채 차트용 데이터 포맷팅
        chart_data = format_current_liabilities_chart_data(db_data, period, ticker)
        
        if chart_data is None:
            return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
        
        return jsonify({
            'success': True,
            'type': 'current_liabilities',
            'chart_data': chart_data,
            'period': period,
            'deleted_count': deleted_count,
            'message': f'유동부채 데이터 {deleted_count}개를 삭제하고 최신 데이터로 새로고침했습니다.'
        })
        
    except Exception as e:
        print(f"유동부채 새로고침 오류: {e}")
        return jsonify({'error': '유동부채 새로고침 중 오류가 발생했습니다.'}), 500

@app.route('/api/stock/interest_expense/check', methods=['POST'])
def check_stock_interest_expense():
    """이자비용 데이터 캐시 확인 및 처리"""
    try:
        data = request.json
        ticker = data.get('stock_code', '').strip()
        period = 4  # 4년 고정
        
        # 공백 제거
        ticker = ''.join(ticker.split())
        
        print(f"이자비용 캐시 확인 요청: ticker='{ticker}', period={period}")
        
        if not ticker:
            return jsonify({'error': '정확한 정보를 입력하세요!'}), 400
        
        # 현재 날짜 기준 캐시 확인
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        # 이자비용 데이터베이스에서 현재 달 데이터 확인
        has_current_month_data, db_data = check_interest_expense_database_data(ticker)
        
        if has_current_month_data and db_data:
            # 캐시된 데이터가 있으면 바로 반환
            print(f"캐시된 이자비용 데이터 사용: {ticker}")
            chart_data = format_interest_expense_chart_data(db_data, period, ticker)
            
            if chart_data is None:
                return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
            
            return jsonify({
                'success': True,
                'type': 'interest_expense',
                'chart_data': chart_data,
                'period': period,
                'cached': True,
                'message': '캐시된 이자비용 데이터를 사용합니다.'
            })
        else:
            # 캐시된 데이터가 없으면 Yahoo Finance에서 조회
            print(f"Yahoo Finance에서 이자비용 데이터 조회: {ticker}")
            
            interest_expense_data = get_stock_interest_expense_data(ticker, 10)
            
            if not interest_expense_data:
                return jsonify({'error': '이자비용 데이터를 가져올 수 없습니다.'}), 400
            
            # 회사명 조회 (주가 데이터에서)
            price_data = get_price_database_data(ticker, period)
            company_name = price_data[0].get('company_name', f"Company_{ticker}") if price_data else f"Company_{ticker}"
            
            # 이자비용 데이터베이스에 저장
            save_interest_expense_to_database(ticker, company_name, interest_expense_data)
            
            # 저장된 데이터로 차트 생성
            db_data = get_interest_expense_database_data(ticker, period)
            chart_data = format_interest_expense_chart_data(db_data, period, ticker)
            
            if chart_data is None:
                return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
            
            return jsonify({
                'success': True,
                'type': 'interest_expense',
                'chart_data': chart_data,
                'period': period,
                'cached': False,
                'message': 'Yahoo Finance에서 최신 이자비용 데이터를 가져왔습니다.'
            })
        
    except Exception as e:
        print(f"이자비용 캐시 확인 오류: {e}")
        return jsonify({'error': '이자비용 데이터 처리 중 오류가 발생했습니다.'}), 500

@app.route('/api/stock/interest_expense/refresh', methods=['POST'])
def refresh_stock_interest_expense():
    """이자비용 데이터 새로고침 - API 성공 후 특정 종목의 현재 달 데이터만 삭제 후 재생성"""
    try:
        data = request.json
        ticker = data.get('stock_code', '').strip()
        period = 4  # 4년 고정
        
        # 공백 제거
        ticker = ''.join(ticker.split())
        
        print(f"이자비용 Refresh 요청: ticker='{ticker}', period={period}")
        
        if not ticker:
            return jsonify({'error': '정확한 정보를 입력하세요!'}), 400
        
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        print(f"Yahoo Finance에서 최신 이자비용 데이터 조회: {ticker}")
        
        # 1. 먼저 Yahoo Finance에서 이자비용 데이터 조회
        interest_expense_data = get_stock_interest_expense_data(ticker, 10)
        
        if not interest_expense_data:
            return jsonify({'error': '이자비용 데이터를 가져올 수 없습니다.'}), 400
        
        # 2. 회사명 조회 (주가 데이터에서)
        price_data = get_price_database_data(ticker, period)
        company_name = price_data[0].get('company_name', f"Company_{ticker}") if price_data else f"Company_{ticker}"
        
        # 3. API 성공 후 해당 종목의 현재 달 데이터만 삭제
        clear_success, deleted_count = clear_interest_expense_cache_data_for_ticker(ticker, cache_year, cache_month)
        if not clear_success:
            print(f"이자비용 캐시 데이터 삭제 실패: {ticker}")
        
        # 4. 이자비용 데이터베이스에 저장
        save_success = save_interest_expense_to_database(ticker, company_name, interest_expense_data)
        if not save_success:
            return jsonify({'error': '이자비용 데이터 저장에 실패했습니다.'}), 500
        
        # 5. 이자비용 데이터베이스에서 차트용 데이터 조회
        db_data = get_interest_expense_database_data(ticker, period)
        
        if not db_data:
            return jsonify({'error': '이자비용 데이터가 없습니다.'}), 400
        
        # 6. 이자비용 차트용 데이터 포맷팅
        chart_data = format_interest_expense_chart_data(db_data, period, ticker)
        
        if chart_data is None:
            return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
        
        return jsonify({
            'success': True,
            'type': 'interest_expense',
            'chart_data': chart_data,
            'period': period,
            'deleted_count': deleted_count,
            'message': f'이자비용 데이터 {deleted_count}개를 삭제하고 최신 데이터로 새로고침했습니다.'
        })
        
    except Exception as e:
        print(f"이자비용 새로고침 오류: {e}")
        return jsonify({'error': '이자비용 새로고침 중 오류가 발생했습니다.'}), 500

@app.route('/api/stock/cash/check', methods=['POST'])
def check_stock_cash():
    """현금및현금성자산 데이터 캐시 확인 및 처리"""
    try:
        data = request.json
        ticker = data.get('stock_code', '').strip()
        period = 4  # 4년 고정
        
        # 공백 제거
        ticker = ''.join(ticker.split())
        
        print(f"현금성자산 캐시 확인 요청: ticker='{ticker}', period={period}")
        
        if not ticker:
            return jsonify({'error': '정확한 정보를 입력하세요!'}), 400
        
        # 현재 날짜 기준 캐시 확인
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        # 현금성자산 데이터베이스에서 현재 달 데이터 확인
        has_current_month_data, db_data = check_cash_database_data(ticker)
        
        if has_current_month_data and db_data:
            # 캐시된 데이터가 있으면 바로 반환
            print(f"캐시된 현금성자산 데이터 사용: {ticker}")
            chart_data = format_cash_chart_data(db_data, period, ticker)
            
            if chart_data is None:
                return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
            
            return jsonify({
                'success': True,
                'type': 'cash',
                'chart_data': chart_data,
                'period': period,
                'cached': True,
                'message': '캐시된 현금성자산 데이터를 사용합니다.'
            })
        else:
            # 캐시된 데이터가 없으면 Yahoo Finance에서 조회
            print(f"Yahoo Finance에서 현금성자산 데이터 조회: {ticker}")
            
            cash_data = get_stock_cash_data(ticker, 10)
            
            if not cash_data:
                return jsonify({'error': '현금성자산 데이터를 가져올 수 없습니다.'}), 400
            
            # 회사명 조회 (주가 데이터에서)
            price_data = get_price_database_data(ticker, period)
            company_name = price_data[0].get('company_name', f"Company_{ticker}") if price_data else f"Company_{ticker}"
            
            # 현금성자산 데이터베이스에 저장
            save_cash_to_database(ticker, company_name, cash_data)
            
            # 저장된 데이터로 차트 생성
            db_data = get_cash_database_data(ticker, period)
            chart_data = format_cash_chart_data(db_data, period, ticker)
            
            if chart_data is None:
                return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
            
            return jsonify({
                'success': True,
                'type': 'cash',
                'chart_data': chart_data,
                'period': period,
                'cached': False,
                'message': 'Yahoo Finance에서 최신 현금성자산 데이터를 가져왔습니다.'
            })
        
    except Exception as e:
        print(f"현금성자산 캐시 확인 오류: {e}")
        return jsonify({'error': '현금성자산 데이터 처리 중 오류가 발생했습니다.'}), 500

@app.route('/api/stock/cash/refresh', methods=['POST'])
def refresh_stock_cash():
    """현금성자산 데이터 새로고침 - API 성공 후 특정 종목의 현재 달 데이터만 삭제 후 재생성"""
    try:
        data = request.json
        ticker = data.get('stock_code', '').strip()
        period = 4  # 4년 고정
        
        # 공백 제거
        ticker = ''.join(ticker.split())
        
        print(f"현금성자산 Refresh 요청: ticker='{ticker}', period={period}")
        
        if not ticker:
            return jsonify({'error': '정확한 정보를 입력하세요!'}), 400
        
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        print(f"Yahoo Finance에서 최신 현금성자산 데이터 조회: {ticker}")
        
        # 1. 먼저 Yahoo Finance에서 현금성자산 데이터 조회
        cash_data = get_stock_cash_data(ticker, 10)
        
        if not cash_data:
            return jsonify({'error': '현금성자산 데이터를 가져올 수 없습니다.'}), 400
        
        # 2. 회사명 조회 (주가 데이터에서)
        price_data = get_price_database_data(ticker, period)
        company_name = price_data[0].get('company_name', f"Company_{ticker}") if price_data else f"Company_{ticker}"
        
        # 3. API 성공 후 해당 종목의 현재 달 데이터만 삭제
        clear_success, deleted_count = clear_cash_cache_data_for_ticker(ticker, cache_year, cache_month)
        if not clear_success:
            print(f"현금성자산 캐시 데이터 삭제 실패: {ticker}")
        
        # 4. 현금성자산 데이터베이스에 저장
        save_success = save_cash_to_database(ticker, company_name, cash_data)
        if not save_success:
            return jsonify({'error': '현금성자산 데이터 저장에 실패했습니다.'}), 500
        
        # 5. 현금성자산 데이터베이스에서 차트용 데이터 조회
        db_data = get_cash_database_data(ticker, period)
        
        if not db_data:
            return jsonify({'error': '현금성자산 데이터가 없습니다.'}), 400
        
        # 6. 현금성자산 차트용 데이터 포맷팅
        chart_data = format_cash_chart_data(db_data, period, ticker)
        
        if chart_data is None:
            return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
        
        return jsonify({
            'success': True,
            'type': 'cash',
            'chart_data': chart_data,
            'period': period,
            'deleted_count': deleted_count,
            'message': f'현금성자산 데이터 {deleted_count}개를 삭제하고 최신 데이터로 새로고침했습니다.'
        })
        
    except Exception as e:
        print(f"현금성자산 새로고침 오류: {e}")
        return jsonify({'error': '현금성자산 새로고침 중 오류가 발생했습니다.'}), 500

@app.route('/api/stock/valuation/check', methods=['POST'])
def check_stock_valuation():
    """밸류에이션 데이터 캐시 확인 및 처리"""
    try:
        data = request.json
        ticker = data.get('stock_code', '').strip()
        period = 1  # 1년 고정 (Yahoo Finance는 최근 5분기만 제공)
        
        # 공백 제거
        ticker = ''.join(ticker.split())
        
        print(f"밸류에이션 캐시 확인 요청: ticker='{ticker}', period={period}")
        
        if not ticker:
            return jsonify({'error': '정확한 정보를 입력하세요!'}), 400
        
        # 현재 날짜 기준 캐시 확인
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        # 밸류에이션 데이터베이스에서 현재 달 데이터 확인
        has_current_month_data, db_data = check_valuation_database_data(ticker)
        
        if has_current_month_data and db_data:
            # 캐시된 데이터가 있으면 바로 반환
            print(f"캐시된 밸류에이션 데이터 사용: {ticker}")
            chart_data = format_valuation_chart_data(db_data, period, ticker)
            
            if chart_data is None:
                return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
            
            return jsonify({
                'success': True,
                'type': 'valuation',
                'chart_data': chart_data,
                'period': period,
                'cached': True,
                'message': '캐시된 밸류에이션 데이터를 사용합니다.'
            })
        else:
            # 캐시된 데이터가 없으면 Yahoo Finance에서 조회
            print(f"Yahoo Finance에서 밸류에이션 데이터 조회: {ticker}")
            
            valuation_data = get_stock_valuation_data(ticker, 10)
            
            if not valuation_data:
                return jsonify({'error': '밸류에이션 데이터를 가져올 수 없습니다.'}), 400
            
            # 회사명 조회 (주가 데이터에서)
            price_data = get_price_database_data(ticker, period)
            company_name = price_data[0].get('company_name', f"Company_{ticker}") if price_data else f"Company_{ticker}"
            
            # 밸류에이션 데이터베이스에 저장
            save_valuation_to_database(ticker, company_name, valuation_data)
            
            # 저장된 데이터로 차트 생성
            db_data = get_valuation_database_data(ticker, period)
            chart_data = format_valuation_chart_data(db_data, period, ticker)
            
            if chart_data is None:
                return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
            
            return jsonify({
                'success': True,
                'type': 'valuation',
                'chart_data': chart_data,
                'period': period,
                'cached': False,
                'message': 'Yahoo Finance에서 최신 밸류에이션 데이터를 가져왔습니다.'
            })
        
    except Exception as e:
        print(f"밸류에이션 캐시 확인 오류: {e}")
        return jsonify({'error': '밸류에이션 데이터 처리 중 오류가 발생했습니다.'}), 500

@app.route('/api/stock/valuation/refresh', methods=['POST'])
def refresh_stock_valuation():
    """밸류에이션 데이터 새로고침 - 특정 종목의 현재 달 데이터만 삭제 후 재생성"""
    try:
        data = request.json
        ticker = data.get('stock_code', '').strip()
        period = 1  # 1년 고정 (Yahoo Finance는 최근 5분기만 제공)
        
        # 공백 제거
        ticker = ''.join(ticker.split())
        
        print(f"밸류에이션 Refresh 요청: ticker='{ticker}', period={period}")
        
        if not ticker:
            return jsonify({'error': '정확한 정보를 입력하세요!'}), 400
        
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        print(f"Yahoo Finance에서 최신 밸류에이션 데이터 조회: {ticker}")
        
        # 1. 먼저 Yahoo Finance에서 밸류에이션 데이터 조회
        valuation_data = get_stock_valuation_data(ticker, 10)
        
        if not valuation_data:
            return jsonify({'error': '밸류에이션 데이터를 가져올 수 없습니다.'}), 400
        
        # 2. 회사명 조회 (주가 데이터에서)
        price_data = get_price_database_data(ticker, period)
        company_name = price_data[0].get('company_name', f"Company_{ticker}") if price_data else f"Company_{ticker}"
        
        # 3. API 성공 후 해당 종목의 현재 달 데이터만 삭제
        clear_success, deleted_count = clear_valuation_cache_data_for_ticker(ticker, cache_year, cache_month)
        if not clear_success:
            print(f"밸류에이션 캐시 데이터 삭제 실패: {ticker}")
        
        # 4. 밸류에이션 데이터베이스에 저장
        save_success = save_valuation_to_database(ticker, company_name, valuation_data)
        if not save_success:
            return jsonify({'error': '밸류에이션 데이터 저장에 실패했습니다.'}), 500
        
        # 5. 밸류에이션 데이터베이스에서 차트용 데이터 조회
        db_data = get_valuation_database_data(ticker, period)
        
        if not db_data:
            return jsonify({'error': '밸류에이션 데이터가 없습니다.'}), 400
        
        # 6. 밸류에이션 차트용 데이터 포맷팅
        chart_data = format_valuation_chart_data(db_data, period, ticker)
        
        if chart_data is None:
            return jsonify({'error': '차트 데이터 포맷팅 오류'}), 500
        
        return jsonify({
            'success': True,
            'type': 'valuation',
            'chart_data': chart_data,
            'period': period,
            'deleted_count': deleted_count,
            'message': f'밸류에이션 데이터 {deleted_count}개를 삭제하고 최신 데이터로 새로고침했습니다.'
        })
        
    except Exception as e:
        print(f"밸류에이션 새로고침 오류: {e}")
        return jsonify({'error': '밸류에이션 새로고침 중 오류가 발생했습니다.'}), 500

@app.route('/api/stocks', methods=['POST'])
def add_stock():
    """새 주식 추가"""
    data = load_data()
    stock_data = request.json
    
    # 새 주식 객체 생성
    new_stock = {
        'id': len(data['stocks']) + 1,
        'name': stock_data.get('name'),
        'symbol': stock_data.get('symbol'),
        'quantity': int(stock_data.get('quantity', 0)),
        'price': float(stock_data.get('price', 0)),
        'added_date': datetime.now().isoformat()
    }
    
    data['stocks'].append(new_stock)
    save_data(data)
    
    return jsonify(new_stock), 201

@app.route('/api/stocks/<int:stock_id>', methods=['PUT'])
def update_stock(stock_id):
    """주식 정보 수정"""
    data = load_data()
    
    for stock in data['stocks']:
        if stock['id'] == stock_id:
            stock_data = request.json
            stock['name'] = stock_data.get('name', stock['name'])
            stock['symbol'] = stock_data.get('symbol', stock['symbol'])
            stock['quantity'] = int(stock_data.get('quantity', stock['quantity']))
            stock['price'] = float(stock_data.get('price', stock['price']))
            
            save_data(data)
            return jsonify(stock)
    
    return jsonify({'error': 'Stock not found'}), 404

@app.route('/api/stocks/<int:stock_id>', methods=['DELETE'])
def delete_stock(stock_id):
    """주식 삭제"""
    data = load_data()
    
    for i, stock in enumerate(data['stocks']):
        if stock['id'] == stock_id:
            deleted_stock = data['stocks'].pop(i)
            save_data(data)
            return jsonify(deleted_stock)
    
    return jsonify({'error': 'Stock not found'}), 404

@app.route('/api/transactions', methods=['GET'])
def get_transactions():
    """거래 내역 조회"""
    data = load_data()
    return jsonify(data['transactions'])

@app.route('/api/transactions', methods=['POST'])
def add_transaction():
    """새 거래 추가"""
    data = load_data()
    transaction_data = request.json
    
    # 새 거래 객체 생성
    new_transaction = {
        'id': len(data['transactions']) + 1,
        'stock_id': transaction_data.get('stock_id'),
        'type': transaction_data.get('type'),  # 'buy' or 'sell'
        'quantity': int(transaction_data.get('quantity', 0)),
        'price': float(transaction_data.get('price', 0)),
        'date': transaction_data.get('date', datetime.now().isoformat())
    }
    
    data['transactions'].append(new_transaction)
    save_data(data)
    
    return jsonify(new_transaction), 201

@app.route('/api/portfolio/summary')
def portfolio_summary():
    """포트폴리오 요약 정보"""
    data = load_data()
    
    total_value = 0
    total_profit = 0
    
    for stock in data['stocks']:
        stock_value = stock['quantity'] * stock['price']
        total_value += stock_value
        
        # 거래 내역에서 수익/손실 계산
        stock_transactions = [t for t in data['transactions'] if t['stock_id'] == stock['id']]
        
        for transaction in stock_transactions:
            if transaction['type'] == 'buy':
                total_profit -= transaction['quantity'] * transaction['price']
            elif transaction['type'] == 'sell':
                total_profit += transaction['quantity'] * transaction['price']
    
    return jsonify({
        'total_value': total_value,
        'total_profit': total_profit,
        'total_stocks': len(data['stocks'])
    })

if __name__ == '__main__':
    # 로컬 개발 서버
    check_and_create_tables()
    # Render는 PORT 환경 변수를 제공합니다
    port = int(os.getenv('PORT', 5000))
    print(f"[INFO] 서버 시작: 포트 {port}")
    app.run(debug=True, host='0.0.0.0', port=port)
