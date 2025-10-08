-- MyStockTax 데이터베이스 테이블 생성 스크립트
-- Supabase SQL Editor에서 이 파일을 실행하세요.

-- 주가 데이터

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
        

CREATE INDEX IF NOT EXISTS idx_stock_price_code_year ON stock_price_data(stock_code, year);
CREATE INDEX IF NOT EXISTS idx_stock_price_cache ON stock_price_data(cache_year, cache_month);

-- 매출 데이터

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
        

CREATE INDEX IF NOT EXISTS idx_stock_revenue_code_year ON stock_revenue_data(stock_code, year);
CREATE INDEX IF NOT EXISTS idx_stock_revenue_cache ON stock_revenue_data(cache_year, cache_month);

-- 영업이익 데이터

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
        

CREATE INDEX IF NOT EXISTS idx_stock_operating_income_code_year ON stock_operating_income_data(stock_code, year);
CREATE INDEX IF NOT EXISTS idx_stock_operating_income_cache ON stock_operating_income_data(cache_year, cache_month);

-- 당기순이익 데이터

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
        

CREATE INDEX IF NOT EXISTS idx_stock_net_profit_code_year ON stock_net_profit_data(stock_code, year);
CREATE INDEX IF NOT EXISTS idx_stock_net_profit_cache ON stock_net_profit_data(cache_year, cache_month);

-- 총부채 데이터

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
        

CREATE INDEX IF NOT EXISTS idx_stock_total_debt_code_year ON stock_total_debt_data(stock_code, year);
CREATE INDEX IF NOT EXISTS idx_stock_total_debt_cache ON stock_total_debt_data(cache_year, cache_month);

-- 유동부채 데이터

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
        

CREATE INDEX IF NOT EXISTS idx_stock_current_liabilities_code_year ON stock_current_liabilities_data(stock_code, year);
CREATE INDEX IF NOT EXISTS idx_stock_current_liabilities_cache ON stock_current_liabilities_data(cache_year, cache_month);

-- 이자비용 데이터

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
        

CREATE INDEX IF NOT EXISTS idx_stock_interest_expense_code_year ON stock_interest_expense_data(stock_code, year);
CREATE INDEX IF NOT EXISTS idx_stock_interest_expense_cache ON stock_interest_expense_data(cache_year, cache_month);

-- 현금및현금성자산 데이터

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
        

CREATE INDEX IF NOT EXISTS idx_stock_cash_code_year ON stock_cash_data(stock_code, year);
CREATE INDEX IF NOT EXISTS idx_stock_cash_cache ON stock_cash_data(cache_year, cache_month);

-- 미국 국채금리 데이터 (5년물 vs 3개월물)

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
        

CREATE INDEX IF NOT EXISTS idx_economy_treasury_year ON economy_treasury_data(year);
CREATE INDEX IF NOT EXISTS idx_economy_treasury_cache ON economy_treasury_data(cache_year, cache_month);

-- CPI (소비자물가지수) 데이터

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
        

CREATE INDEX IF NOT EXISTS idx_economy_cpi_year ON economy_cpi_data(year);
CREATE INDEX IF NOT EXISTS idx_economy_cpi_cache ON economy_cpi_data(cache_year, cache_month);

-- 제조업 생산지수 데이터

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
        

CREATE INDEX IF NOT EXISTS idx_economy_industrial_production_year ON economy_industrial_production_data(year);
CREATE INDEX IF NOT EXISTS idx_economy_industrial_production_cache ON economy_industrial_production_data(cache_year, cache_month);

-- 실업률 데이터

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
        

CREATE INDEX IF NOT EXISTS idx_economy_unemployment_year ON economy_unemployment_data(year);
CREATE INDEX IF NOT EXISTS idx_economy_unemployment_cache ON economy_unemployment_data(cache_year, cache_month);

-- GDP (국내총생산) 데이터

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
        

CREATE INDEX IF NOT EXISTS idx_economy_gdp_year ON economy_gdp_data(year);
CREATE INDEX IF NOT EXISTS idx_economy_gdp_cache ON economy_gdp_data(cache_year, cache_month);

-- 버핏지수 (Wilshire 5000) 데이터

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
        

CREATE INDEX IF NOT EXISTS idx_economy_buffett_year ON economy_buffett_data(year);
CREATE INDEX IF NOT EXISTS idx_economy_buffett_cache ON economy_buffett_data(cache_year, cache_month);

-- 모기지 연체율 데이터

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
        

CREATE INDEX IF NOT EXISTS idx_economy_mortgage_delinquency_year ON economy_mortgage_delinquency_data(year);
CREATE INDEX IF NOT EXISTS idx_economy_mortgage_delinquency_cache ON economy_mortgage_delinquency_data(cache_year, cache_month);

-- PBR, PER, EV/EBITDA 밸류에이션 지표 데이터

            CREATE TABLE IF NOT EXISTS stock_valuation_data (
                id SERIAL PRIMARY KEY,
                stock_code VARCHAR(20) NOT NULL,
                company_name VARCHAR(200),
                year INTEGER NOT NULL,
                quarter INTEGER NOT NULL,
                pbr DECIMAL(10,4),
                per DECIMAL(10,4),
                ev_ebitda DECIMAL(10,4),
                cache_year INTEGER,
                cache_month INTEGER,
                last_updated TIMESTAMP DEFAULT NOW(),
                UNIQUE(stock_code, year, quarter)
            );
        

CREATE INDEX IF NOT EXISTS idx_stock_valuation_code_year ON stock_valuation_data(stock_code, year);
CREATE INDEX IF NOT EXISTS idx_stock_valuation_cache ON stock_valuation_data(cache_year, cache_month);

