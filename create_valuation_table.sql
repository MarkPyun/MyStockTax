-- PBR, PER, EV/EBITDA 밸류에이션 지표 데이터 테이블
-- Supabase SQL Editor에서 이 쿼리를 실행하세요.

CREATE TABLE IF NOT EXISTS stock_valuation_data (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(20) NOT NULL,
    company_name VARCHAR(200),
    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    pbr DECIMAL(10,4),          -- PBR (Price to Book Ratio)
    per DECIMAL(10,4),          -- PER (Price to Earnings Ratio)
    ev_ebitda DECIMAL(10,4),    -- EV/EBITDA (Enterprise Value to EBITDA)
    cache_year INTEGER,
    cache_month INTEGER,
    last_updated TIMESTAMP DEFAULT NOW(),
    UNIQUE(stock_code, year, quarter)
);

-- 인덱스 생성 (검색 성능 향상)
CREATE INDEX IF NOT EXISTS idx_stock_valuation_code_year ON stock_valuation_data(stock_code, year);
CREATE INDEX IF NOT EXISTS idx_stock_valuation_cache ON stock_valuation_data(cache_year, cache_month);

-- 테이블 확인
SELECT 'stock_valuation_data 테이블이 성공적으로 생성되었습니다.' AS message;

