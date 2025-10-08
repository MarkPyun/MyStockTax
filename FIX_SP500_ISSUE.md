# S&P 500 그래프 데이터 표시 오류 수정 가이드

## 문제 요약
버핏지수는 정상적으로 표시되지만 S&P 500 그래프에 데이터가 표시되지 않는 문제

## 원인
데이터베이스의 `economy_sp500_data` 테이블에서 `sp500_value` 컬럼이 `DECIMAL(10,4)` 타입으로 정의되어 있어, S&P 500 지수의 큰 값(5000~6000대)을 저장할 때 정밀도 문제가 발생할 수 있습니다.

## 수정 사항
1. **데이터베이스 컬럼 타입 변경**: `DECIMAL(10,4)` → `DECIMAL(12,2)`
2. **애플리케이션 코드 수정**: 데이터 반올림 정밀도 조정 (4자리 → 2자리)

## 수정 절차

### 1단계: 데이터베이스 수정
Supabase 대시보드에 로그인하여 SQL Editor에서 다음 SQL을 실행하세요:

```sql
-- S&P 500 컬럼 타입 변경
ALTER TABLE economy_sp500_data 
ALTER COLUMN sp500_value TYPE DECIMAL(12,2);

-- 캐시된 데이터 삭제 (현재 월 데이터만)
DELETE FROM economy_sp500_data 
WHERE cache_year = EXTRACT(YEAR FROM CURRENT_DATE) 
  AND cache_month = EXTRACT(MONTH FROM CURRENT_DATE);

-- 변경 사항 확인
SELECT column_name, data_type, numeric_precision, numeric_scale
FROM information_schema.columns
WHERE table_name = 'economy_sp500_data' AND column_name = 'sp500_value';
```

또는 제공된 `fix_sp500_column.sql` 파일을 실행하세요.

### 2단계: 애플리케이션 코드 수정 완료 확인
다음 파일들이 이미 수정되었습니다:
- ✅ `app.py` - S&P 500 데이터 반올림 정밀도 조정 (4자리 → 2자리)
- ✅ `setup_tables.sql` - 테이블 생성 스크립트 업데이트

### 3단계: 애플리케이션 재시작
```bash
# 로컬 환경
python app.py

# 또는 Flask 개발 서버
flask run

# Vercel에 배포된 경우
# Git에 변경사항 커밋 후 푸시하면 자동 배포됩니다
```

### 4단계: 데이터 새로고침
1. 웹 애플리케이션에서 "Economy & Trade" 페이지로 이동
2. S&P 500 차트 섹션의 새로고침 버튼(🔄)을 클릭
3. 데이터가 새로 로드되고 차트가 표시되는지 확인

## 변경 사항 상세

### 데이터베이스 스키마
**변경 전:**
```sql
sp500_value DECIMAL(10,4)  -- 최대 6자리.4자리 (999999.9999)
```

**변경 후:**
```sql
sp500_value DECIMAL(12,2)  -- 최대 10자리.2자리 (9999999999.99)
```

### 애플리케이션 코드
**app.py의 `get_sp500_data_from_fred()` 함수:**
```python
# 변경 전
sp500_data[key] = round(avg_value, 4)

# 변경 후
sp500_data[key] = round(avg_value, 2)
```

**app.py의 `get_sp500_fallback_data()` 함수:**
```python
# 변경 전
sp500_data[key] = round(base_values[year][q_key], 4)

# 변경 후
sp500_data[key] = round(base_values[year][q_key], 2)
```

## 검증 방법

### 1. 데이터베이스 확인
```sql
-- S&P 500 데이터가 올바르게 저장되었는지 확인
SELECT year, quarter, sp500_value, cache_year, cache_month, last_updated
FROM economy_sp500_data
ORDER BY year DESC, quarter DESC
LIMIT 10;
```

### 2. 웹 인터페이스 확인
- Economy & Trade 페이지에서 S&P 500 차트가 올바르게 표시되는지 확인
- 최근 데이터 포인트가 5000-6000 범위에 있는지 확인
- 차트가 정상적으로 렌더링되는지 확인

### 3. 브라우저 콘솔 확인
F12를 눌러 개발자 도구를 열고 Console 탭에서:
- "S&P 500 차트 데이터:" 메시지 확인
- `sp500_values` 배열에 값이 있는지 확인
- 에러 메시지가 없는지 확인

## 문제 해결

### 여전히 데이터가 표시되지 않는 경우:

1. **브라우저 캐시 삭제**
   - Ctrl + Shift + R (Windows/Linux)
   - Cmd + Shift + R (Mac)

2. **데이터베이스 전체 초기화** (마지막 수단)
   ```sql
   -- 모든 S&P 500 데이터 삭제
   DELETE FROM economy_sp500_data;
   
   -- 테이블 재생성 (선택사항)
   DROP TABLE IF EXISTS economy_sp500_data;
   -- 그런 다음 setup_tables.sql의 CREATE TABLE 문 실행
   ```

3. **API 키 확인**
   - FRED API 키가 올바르게 설정되어 있는지 확인
   - `.env` 파일에 `FRED_API_KEY` 변수가 있는지 확인

4. **로그 확인**
   - 터미널에서 애플리케이션 로그 확인
   - "S&P 500 데이터 조회 중..." 메시지 확인
   - 오류 메시지가 있는지 확인

## 예상 결과
- S&P 500 차트에 최근 4년간의 분기별 데이터가 표시됩니다
- 2021년부터 현재까지의 데이터가 꺾은선 그래프로 표시됩니다
- 최신 데이터 포인트는 5000-6000 범위에 있어야 합니다

## 추가 참고사항
- 버핏지수가 정상적으로 작동한다면, 데이터베이스 연결과 API 설정은 정상입니다
- S&P 500 데이터는 매월 첫 조회 시 FRED API에서 가져오고 캐시됩니다
- 새로고침 버튼을 누르면 현재 월의 캐시를 삭제하고 최신 데이터를 가져옵니다

