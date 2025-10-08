# MyStockTax - 주식 분석 및 세금 계산 시스템

한국 및 미국 주식 분석, 경제 지표, 세금 시뮬레이터를 제공하는 통합 웹 애플리케이션입니다.

## 🎯 주요 기능

### 📈 Stock 분석
- 주가, 매출, 영업이익, 당기순이익, 부채, 현금 등 재무제표 분석
- 분기별/연간 데이터 차트
- 월 단위 데이터 캐싱
- 한국/미국 주식 지원

### 🌍 Economy & Trade
- 미국 국채금리, CPI, 제조업 생산지수, 실업률, GDP
- S&P 500 지수, 버핏지수, 주택재고량
- **모기지 연체율** (신규 추가!)
- FRED API 연동

### 💰 Tax 분석
- 10가지 세금 계산기 (소득세, 부가세, 증권거래세 등)
- 월별 납부 일정 자동 생성
- 상세 계산 내역 및 절세 팁

## 🚀 빠른 시작

### 1. 저장소 클론
```bash
git clone https://github.com/your-username/StockandTax.git
cd StockandTax
```

### 2. 필수 패키지 설치
```bash
pip install -r requirements.txt
```

### 3. 환경 변수 설정
`env.example` 파일을 복사하여 `.env` 파일을 생성하고 API 키를 입력하세요:

```bash
# .env 파일 생성
cp env.example .env
```

`.env` 파일 내용:
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key
FRED_API_KEY=your_fred_api_key
SUPABASE_DB_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
```

### 4. Supabase 테이블 설정 (최초 1회만)

**⚠️ 중요: 애플리케이션 실행 전에 반드시 수행해야 합니다!**

1. Supabase 대시보드 접속
2. 왼쪽 메뉴에서 **SQL Editor** 클릭
3. **New Query** 버튼 클릭
4. 프로젝트 루트의 `setup_tables.sql` 파일 내용을 복사해서 붙여넣기
5. **RUN** 버튼 클릭

> 📝 `setup_tables.sql`에는 15개의 테이블 스키마가 포함되어 있습니다.

### 5. 애플리케이션 실행
```bash
python app.py
```

브라우저에서 http://localhost:5000 접속

## 📊 데이터베이스 테이블

시스템은 15개의 테이블을 사용합니다:

**주식 데이터 (8개)**
- stock_price_data, stock_revenue_data, stock_operating_income_data
- stock_net_profit_data, stock_total_debt_data, stock_current_liabilities_data
- stock_interest_expense_data, stock_cash_data

**경제 지표 (7개)**
- economy_treasury_data, economy_cpi_data, economy_industrial_production_data
- economy_unemployment_data, economy_gdp_data, economy_sp500_data
- economy_buffett_indicator_data, economy_housing_inventory_data
- economy_mortgage_delinquency_data

### 지원 시장
- **미국 주식**: 영문 티커 (예: AAPL, MSFT, GOOGL)
- **한국 주식**: 종목 코드 (예: 005930, 035420)

## 🔧 새로운 재무 항목 추가 방법

새로운 항목(예: 당기순이익, ROE 등)을 추가할 때:

1. **setup_tables.sql** 파일에 새 테이블 SQL 추가
2. **app.py**의 `required_tables` 딕셔너리에 테이블 추가
3. Supabase에서 `setup_tables.sql` 실행
4. 매출/영업이익과 동일한 패턴으로 함수 구현

## 📁 프로젝트 구조

```
StockandTax/
├── app.py                      # Flask 백엔드
├── setup_tables.sql            # Supabase 테이블 생성 스크립트
├── data.json                   # 로컬 데이터 저장
├── templates/
│   ├── base.html              # 기본 템플릿
│   ├── index.html             # Stock 분석 페이지
│   ├── tax_analysis.html      # Tax 분석 페이지
│   └── economy_trade.html     # Economy & Trade 페이지
└── static/
    └── images/
        └── favicon.ico
```

## 🛠️ 기술 스택

- **Backend**: Flask, Python 3.10+
- **Database**: Supabase (PostgreSQL)
- **API**: Yahoo Finance (yfinance), FRED API
- **Frontend**: HTML, JavaScript, Bootstrap 5, Chart.js
- **Data**: Pandas
- **Deployment**: Vercel (Serverless)

## 📝 참고사항

- 데이터는 Yahoo Finance API에서 자동 수집
- 캐시는 월 단위로 관리 (매달 자동 갱신)
- 분기별 실적발표 일정에 맞춰 데이터 표시
- 4년 고정 기간 (최근 3년 + 현재년도)

## 🌐 배포 (Vercel)

### GitHub에 푸시하기 전 체크리스트

✅ `.env` 파일이 `.gitignore`에 포함되어 있는지 확인  
✅ API 키가 하드코딩되지 않았는지 확인  
✅ 불필요한 파일 제거 (백업 파일, 테스트 파일)

### Vercel 배포 단계

1. **GitHub에 푸시**
```bash
git add .
git commit -m "Deploy MyStockTax application"
git push origin main
```

2. **Vercel 프로젝트 생성**
- [Vercel](https://vercel.com)에 로그인
- **New Project** → GitHub 저장소 선택
- Framework Preset: **Other** 선택

3. **환경 변수 설정**
Vercel 대시보드에서 Environment Variables 추가:
```
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
FRED_API_KEY=your_fred_api_key
```

4. **배포 완료**
- Deploy 버튼 클릭
- 자동으로 빌드 및 배포됩니다

> 📝 `vercel.json`, `requirements-vercel.txt` 파일이 이미 포함되어 있습니다.

## 🐛 문제 해결

### 테이블 없음 오류
앱 실행 시 "테이블 없음" 메시지가 나오면:
→ `setup_tables.sql`을 Supabase SQL Editor에서 실행

### 데이터가 0으로 표시
→ 새로고침 버튼 클릭 또는 브라우저 캐시 삭제

### API 호출 실패
→ 인터넷 연결 확인, Yahoo Finance 서비스 상태 확인

### 환경 변수 오류
→ `.env` 파일이 올바르게 설정되어 있는지 확인
→ Vercel 배포 시 Environment Variables 설정 확인

## 📄 라이선스

MIT License

## 👨‍💻 개발자

MyStockTax Team
