# 데이터베이스 자동 설정 가이드

## 개요

MyStockTax 애플리케이션은 **자동 테이블 생성** 기능을 지원합니다.
API 쿼리가 들어올 때 필요한 테이블이 없으면 자동으로 생성됩니다.

---

## 🚀 빠른 시작

### 1. 환경 변수 설정

프로젝트 루트에 `.env` 파일을 생성하고 다음 내용을 추가하세요:

```bash
# Supabase PostgreSQL 연결 URL
SUPABASE_DB_URL=postgresql://postgres.xrdwcnarfdxszqbboylt:YOUR_PASSWORD@aws-0-ap-northeast-2.pooler.supabase.com:6543/postgres
```

**YOUR_PASSWORD 찾는 방법:**
1. https://supabase.com 로그인
2. 프로젝트 선택: `xrdwcnarfdxszqbboylt`
3. Settings → Database → Connection string
4. `Password` 확인 (프로젝트 생성 시 설정한 비밀번호)

### 2. psycopg2 패키지 설치

```bash
pip install psycopg2-binary
```

### 3. 애플리케이션 실행

```bash
python app.py
```

이제 주식 데이터를 조회하면 **자동으로 테이블이 생성**됩니다!

---

## 🔧 작동 방식

### 자동 테이블 생성 흐름

1. **API 요청 수신** (예: `/api/stock/price/check`)
2. **테이블 존재 여부 확인** (`stock_price_data` 테이블)
3. **테이블이 없으면**:
   - `db_setup.py`의 `ensure_table_exists()` 함수 호출
   - PostgreSQL에 직접 연결하여 테이블 생성
   - 관련 인덱스도 자동 생성
4. **데이터 저장** 및 응답

### 현재 지원되는 테이블

`db_setup.py` 파일의 `TABLE_SCHEMAS`에 정의된 테이블들이 자동 생성됩니다:

- `stock_price_data` - 주가 데이터
- `stock_revenue_data` - 매출 데이터
- `stock_operating_income_data` - 영업이익 데이터

---

## 📋 새로운 데이터 항목 추가하기

향후 새로운 데이터 항목(예: 당기순이익, EPS 등)을 추가하려면:

### 1. `db_setup.py`에 테이블 스키마 추가

```python
TABLE_SCHEMAS = {
    # ... 기존 테이블들 ...
    
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
}
```

### 2. `app.py`에 save 함수 추가

```python
def save_net_profit_to_database(stock_code, company_name, net_profit_data):
    """당기순이익 데이터를 데이터베이스에 저장합니다."""
    try:
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        # 테이블 이름
        table_name = 'stock_net_profit_data'
        
        # 테이블 존재 여부 확인 및 자동 생성
        if DB_SETUP_AVAILABLE and ensure_table_exists:
            db_url = os.getenv('SUPABASE_DB_URL')
            if not ensure_table_exists(table_name, supabase, db_url):
                print(f"⚠️  {table_name} 테이블을 생성할 수 없습니다.")
                return False
        
        # ... 데이터 저장 로직 ...
```

### 3. API 엔드포인트 추가

```python
@app.route('/api/stock/net_profit/check', methods=['POST'])
def check_stock_net_profit():
    """당기순이익 데이터 캐시 확인 및 처리"""
    # ... 구현 ...
```

이렇게 하면 **새로운 데이터 항목도 자동으로 테이블이 생성**됩니다!

---

## 🛠️ 수동 테이블 생성 (선택사항)

환경 변수 설정 없이 수동으로 테이블을 생성하려면:

### 방법 1: Python 스크립트 실행

```bash
python db_setup.py
```

이 스크립트는:
- 테이블 존재 여부 확인
- `setup_tables.sql` 파일 생성
- 수동 생성 안내 출력

### 방법 2: Supabase 대시보드에서 직접 실행

1. https://xrdwcnarfdxszqbboylt.supabase.co 로그인
2. 왼쪽 메뉴에서 **SQL Editor** 클릭
3. `setup_tables.sql` 파일의 내용을 복사해서 실행

---

## 🔍 트러블슈팅

### "Could not find the table" 오류

**원인:** 테이블이 없고, 자동 생성도 실패한 경우

**해결방법:**
1. `.env` 파일에 `SUPABASE_DB_URL`이 올바르게 설정되었는지 확인
2. 비밀번호가 정확한지 확인
3. 수동으로 `setup_tables.sql` 실행

### "psycopg2" 모듈을 찾을 수 없음

```bash
pip install psycopg2-binary
```

### SUPABASE_DB_URL 찾기

Supabase 대시보드:
1. Settings → Database
2. Connection string 섹션
3. `Connection pooling` 또는 `Direct connection` 선택
4. URL 복사

---

## 📚 참고 자료

- **db_setup.py**: 테이블 스키마 정의 및 자동 생성 로직
- **setup_tables.sql**: SQL 파일 (자동 생성됨)
- **app.py**: save 함수들에서 `ensure_table_exists()` 호출

---

## ✨ 장점

1. **자동화**: 테이블이 없으면 자동 생성
2. **확장성**: 새로운 항목 추가 시 스키마만 정의하면 됨
3. **유연성**: 수동/자동 생성 모두 지원
4. **편의성**: 개발자가 SQL을 직접 실행할 필요 없음


