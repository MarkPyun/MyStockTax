# MyStockTax 개발 가이드

## 📋 목차
1. [시스템 아키텍처](#시스템-아키텍처)
2. [새로운 항목 추가 방법](#새로운-항목-추가-방법)
3. [표준화된 차트 포맷팅](#표준화된-차트-포맷팅)
4. [캐시 시스템](#캐시-시스템)

---

## 시스템 아키텍처

### 핵심 원칙
- **독립성**: 각 항목(주가, 매출, 당기순이익 등)은 독립적으로 동작
- **표준화**: 모든 항목은 동일한 기간 표시 방식 사용
- **순차성**: UI는 순차적으로 로딩되어 디버깅 용이
- **캐시**: 현재 달 데이터는 캐시하여 API 호출 최소화

### 데이터 흐름
```
검색 요청
  ↓
1. 기본 정보 조회 (/api/stock/search)
  ↓
2. 주가 데이터 처리 (/api/stock/price/check)
   - 캐시 확인 (cache_year, cache_month)
   - 없으면 Yahoo API 조회 → DB 저장
   - 차트 출력
  ↓
3. 매출 데이터 처리 (/api/stock/revenue/check)
   - 캐시 확인 (cache_year, cache_month)
   - 없으면 Yahoo API 조회 → DB 저장
   - 차트 출력
  ↓
4. [향후 추가 항목들도 동일한 패턴]
```

---

## 새로운 항목 추가 방법

### 1. 데이터베이스 테이블 생성

Supabase 대시보드에서 SQL Editor를 열고 실행:

```sql
-- 예시: 당기순이익(Net Profit) 테이블
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
    UNIQUE(stock_code, year, quarter, net_profit)
);
```

**중요**: 
- 키값은 `UNIQUE(stock_code, year, quarter, [항목명])` 조합 사용
- `cache_year`, `cache_month` 컬럼 필수

---

### 2. 데이터베이스 함수 추가 (app.py)

#### 2-1. 캐시 확인 함수
```python
def check_net_profit_database_data(stock_code):
    """당기순이익 데이터베이스에서 현재 달 데이터 확인"""
    try:
        current_date = datetime.now()
        current_year = current_date.year
        current_month = current_date.month
        
        table_name = 'stock_net_profit_data'
        
        result = supabase.table(table_name).select('*').eq('stock_code', stock_code).eq('cache_year', current_year).eq('cache_month', current_month).execute()
        
        if result.data:
            return True, result.data
        else:
            return False, []
            
    except Exception as e:
        print(f"당기순이익 데이터베이스 조회 오류: {e}")
        return False, []
```

#### 2-2. 데이터 조회 함수
```python
def get_net_profit_database_data(stock_code, period=5):
    """당기순이익 데이터베이스에서 차트용 데이터 조회"""
    try:
        current_year = datetime.now().year
        start_year = current_year - period
        
        table_name = 'stock_net_profit_data'
        
        result = supabase.table(table_name).select('*').eq('stock_code', stock_code).gte('year', start_year).order('year', desc=False).order('quarter', desc=False).execute()
        
        return result.data if result.data else []
        
    except Exception as e:
        print(f"당기순이익 데이터베이스 조회 오류: {e}")
        return []
```

#### 2-3. 데이터 저장 함수
```python
def save_net_profit_to_database(stock_code, company_name, net_profit_data):
    """당기순이익 데이터를 데이터베이스에 저장"""
    try:
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        table_name = 'stock_net_profit_data'
        
        saved_count = 0
        skipped_count = 0
        
        for quarter_key, net_profit_value in net_profit_data.items():
            try:
                year_str, quarter_str = quarter_key.split('Q')
                year = int(year_str)
                quarter = int(quarter_str)
                
                existing = supabase.table(table_name).select('id').eq('stock_code', stock_code).eq('year', year).eq('quarter', quarter).execute()
                
                if existing.data:
                    skipped_count += 1
                    continue
                
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
                
                supabase.table(table_name).insert(record).execute()
                saved_count += 1
                
            except Exception as e:
                print(f"당기순이익 데이터베이스 처리 오류: {e}")
                continue
        
        print(f"당기순이익 데이터베이스 저장 완료: {stock_code} (새로 저장: {saved_count}개, 건너뜀: {skipped_count}개)")
        return True
        
    except Exception as e:
        print(f"당기순이익 데이터베이스 저장 실패: {e}")
        return False
```

#### 2-4. 캐시 삭제 함수 (Refresh용)
```python
def clear_net_profit_cache_data_for_ticker(ticker, cache_year, cache_month):
    """특정 종목의 당기순이익 데이터에서 현재 달 데이터 삭제"""
    try:
        table_name = 'stock_net_profit_data'
        
        delete_result = supabase.table(table_name).delete().eq('stock_code', ticker).eq('cache_year', cache_year).eq('cache_month', cache_month).execute()
        deleted_count = len(delete_result.data) if delete_result.data else 0
        
        print(f"당기순이익 캐시 데이터 삭제 완료: {ticker} {cache_year}년 {cache_month}월 데이터 {deleted_count}개 삭제")
        return True, deleted_count
        
    except Exception as e:
        print(f"당기순이익 캐시 데이터 삭제 오류: {e}")
        return False, 0
```

---

### 3. 차트 포맷팅 함수 추가

**표준화된 함수 사용 (중요!):**

```python
def format_net_profit_chart_data(data, period):
    """당기순이익 차트용 데이터 포맷팅 - 표준화된 함수 사용"""
    result = format_chart_data_by_period(data, period, 'net_profit', 'sum')
    if result:
        return {
            'labels': result['labels'],
            'net_profits': result['values']
        }
    return None
```

**파라미터 설명:**
- `data`: 데이터베이스에서 조회한 데이터
- `period`: 표시 기간 (5년 또는 10년)
- `'net_profit'`: 데이터베이스 컬럼명
- `'sum'`: 집계 방식 (평균: 'average', 합계: 'sum')

**집계 방식 선택 기준:**
- `'average'`: 주가, 비율 등 (예: 영업이익률, ROE)
- `'sum'`: 매출, 순이익 등 금액 항목

---

### 4. API 엔드포인트 추가

#### 4-1. 캐시 확인 API
```python
@app.route('/api/stock/netprofit/check', methods=['POST'])
def check_stock_net_profit():
    """당기순이익 데이터 캐시 확인 및 처리"""
    try:
        data = request.json
        ticker = data.get('stock_code', '').strip()
        period = int(data.get('period', 5))
        
        ticker = ''.join(ticker.split())
        
        if not ticker:
            return jsonify({'error': '정확한 정보를 입력하세요!'}), 400
        
        # 캐시 확인
        has_current_month_data, db_data = check_net_profit_database_data(ticker)
        
        if has_current_month_data and db_data:
            # 캐시된 데이터 사용
            chart_data = format_net_profit_chart_data(db_data, period)
            
            return jsonify({
                'success': True,
                'type': 'net_profit',
                'chart_data': chart_data,
                'period': period,
                'cached': True,
                'message': '캐시된 당기순이익 데이터를 사용합니다.'
            })
        else:
            # Yahoo Finance에서 조회
            net_profit_data = get_stock_net_profit_data(ticker, 10)
            
            if not net_profit_data:
                return jsonify({'error': '당기순이익 데이터를 가져올 수 없습니다.'}), 400
            
            # 회사명 조회
            price_data = get_price_database_data(ticker, period)
            company_name = price_data[0].get('company_name', f"Company_{ticker}") if price_data else f"Company_{ticker}"
            
            # 데이터베이스에 저장
            save_net_profit_to_database(ticker, company_name, net_profit_data)
            
            # 저장된 데이터로 차트 생성
            db_data = get_net_profit_database_data(ticker, period)
            chart_data = format_net_profit_chart_data(db_data, period)
            
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
```

#### 4-2. Refresh API
```python
@app.route('/api/stock/netprofit/refresh', methods=['POST'])
def refresh_stock_net_profit():
    """당기순이익 데이터 새로고침"""
    try:
        data = request.json
        ticker = data.get('stock_code', '').strip()
        period = int(data.get('period', 5))
        
        ticker = ''.join(ticker.split())
        
        if not ticker:
            return jsonify({'error': '정확한 정보를 입력하세요!'}), 400
        
        # 현재 달 데이터 삭제
        current_date = datetime.now()
        cache_year = current_date.year
        cache_month = current_date.month
        
        clear_success, deleted_count = clear_net_profit_cache_data_for_ticker(ticker, cache_year, cache_month)
        
        # Yahoo Finance에서 재조회
        net_profit_data = get_stock_net_profit_data(ticker, 10)
        
        if not net_profit_data:
            return jsonify({'error': '당기순이익 데이터를 가져올 수 없습니다.'}), 400
        
        # 회사명 조회
        price_data = get_price_database_data(ticker, period)
        company_name = price_data[0].get('company_name', f"Company_{ticker}") if price_data else f"Company_{ticker}"
        
        # 데이터베이스에 저장
        save_net_profit_to_database(ticker, company_name, net_profit_data)
        
        # 저장된 데이터로 차트 생성
        db_data = get_net_profit_database_data(ticker, period)
        chart_data = format_net_profit_chart_data(db_data, period)
        
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
```

---

### 5. 프론트엔드 추가 (templates/index.html)

#### 5-1. HTML 차트 영역 추가
```html
<!-- 당기순이익 차트 -->
<div class="mb-4">
    <h4 class="mb-3">
        3. 당기순이익 
        <button class="btn btn-sm btn-outline-success ms-2" onclick="refreshNetProfitData()" title="당기순이익 데이터 새로고침">
            <i class="fas fa-sync-alt"></i>
        </button>
    </h4>
    <div class="card">
        <div class="card-body">
            <canvas id="netProfitChart" width="400" height="200"></canvas>
        </div>
    </div>
</div>
```

#### 5-2. JavaScript 함수 추가
```javascript
// 당기순이익 데이터 처리 함수
async function processNetProfitData(ticker, period) {
    try {
        document.getElementById('loadingMessage').innerHTML = `
            <i class="fas fa-spinner fa-spin fa-2x mb-3"></i>
            <p>3. 당기순이익 데이터를 처리하고 있습니다...</p>
        `;
        
        const response = await fetch('/api/stock/netprofit/check', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ stock_code: ticker, period: parseInt(period) })
        });
        
        const result = await response.json();
        
        if (result.success) {
            displayNetProfitChart(result.chart_data);
            console.log(result.message);
        } else {
            console.error('당기순이익 데이터 처리 실패:', result.error);
        }
    } catch (error) {
        console.error('당기순이익 데이터 처리 오류:', error);
        throw error;
    }
}

// 당기순이익 차트 생성
function displayNetProfitChart(chartData) {
    const ctx = document.getElementById('netProfitChart').getContext('2d');
    
    if (window.netProfitChartInstance) {
        window.netProfitChartInstance.destroy();
    }
    
    window.netProfitChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: chartData.labels,
            datasets: [{
                label: '당기순이익 (억원)',
                data: chartData.net_profits,
                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                borderColor: 'rgba(75, 192, 192, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

// Refresh 버튼 함수
async function refreshNetProfitData() {
    const searchTerm = document.getElementById('mainSearchInput').value.trim();
    const period = document.getElementById('periodSelect').value;
    
    if (!searchTerm) {
        showError('검색어를 입력하세요.');
        return;
    }
    
    showLoading('당기순이익 데이터를 새로고침하고 있습니다...');
    
    try {
        const response = await fetch('/api/stock/netprofit/refresh', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ stock_code: searchTerm, period: parseInt(period) })
        });
        
        const result = await response.json();
        
        if (result.success) {
            displayNetProfitChart(result.chart_data);
            console.log(result.message);
        } else {
            showError(result.error || '당기순이익 데이터 새로고침에 실패했습니다.');
        }
    } catch (error) {
        console.error('당기순이익 새로고침 오류:', error);
        showError('당기순이익 새로고침 중 오류가 발생했습니다.');
    } finally {
        hideLoading();
    }
}
```

#### 5-3. performSearch 함수에 추가
```javascript
async function performSearch() {
    // ... 기존 코드 ...
    
    // 2. 주가 데이터 순차적 로딩
    await processPriceData(searchTerm, period);
    
    // 3. 매출 데이터 순차적 로딩
    await processRevenueData(searchTerm, period);
    
    // 4. 당기순이익 데이터 순차적 로딩
    await processNetProfitData(searchTerm, period);
    
    // ... 이후 추가 항목들 ...
}
```

---

## 표준화된 차트 포맷팅

### format_chart_data_by_period() 함수

**모든 항목은 이 함수를 사용하여 동일한 기간 표시 방식을 보장합니다.**

```python
def format_chart_data_by_period(data, period, value_key, aggregation_type='average', ticker=None):
    """
    표준화된 차트 데이터 포맷팅 함수
    
    Args:
        data: 데이터베이스에서 조회한 데이터 리스트
        period: 표시 기간 (년)
        value_key: 데이터에서 추출할 값의 키 (예: 'stock_price', 'revenue')
        aggregation_type: 년도별 집계 방식 ('average' 또는 'sum')
        ticker: 주식 코드 (선택사항)
    
    Returns:
        {'labels': [...], 'values': [...]} 형태의 차트 데이터
    """
```

**기간 표시 규칙:**
- 이전 년도: 년도별로 표시 (예: 2020, 2021, 2022)
- 현재 년도: 분기별로 표시 (예: 2025Q1, 2025Q2)

**집계 방식:**
- `'average'`: 년도별 평균 계산 (주가, 비율 등)
- `'sum'`: 년도별 합계 계산 (매출, 순이익 등)

---

## 캐시 시스템

### 캐시 로직
1. 현재 달 데이터가 있으면 캐시 사용
2. 없으면 Yahoo API 조회 후 저장
3. Refresh 버튼: 현재 달 데이터만 삭제 후 재조회

### 캐시 키
- `cache_year`: 데이터 저장 년도
- `cache_month`: 데이터 저장 월

### 장점
- API 호출 최소화
- 빠른 응답 속도
- 종목별 독립적 캐시 관리

---

## 체크리스트

새로운 항목 추가 시 확인사항:

- [ ] Supabase 테이블 생성 (UNIQUE 키 확인)
- [ ] 캐시 확인 함수 추가
- [ ] 데이터 조회 함수 추가
- [ ] 데이터 저장 함수 추가
- [ ] 캐시 삭제 함수 추가
- [ ] 차트 포맷팅 함수 추가 (표준 함수 사용)
- [ ] API 엔드포인트 추가 (/check, /refresh)
- [ ] HTML 차트 영역 추가
- [ ] JavaScript 처리 함수 추가
- [ ] JavaScript 차트 생성 함수 추가
- [ ] JavaScript Refresh 함수 추가
- [ ] performSearch에 순차 호출 추가

---

## 문의

문제가 발생하면 기존 주가/매출 코드를 참고하세요. 모든 항목은 동일한 패턴을 따릅니다.

