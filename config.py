import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

class Config:
    # Supabase 설정
    SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://xrdwcnarfdxszqbboylt.supabase.co')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY', 'your_supabase_anon_key')
    
    # OpenDart API 키 (DART API 키는 사용자가 직접 발급받아야 함)
    DART_API_KEY = os.getenv('DART_API_KEY', 'your_dart_api_key')
    
    # 한국투자증권 API (주가 데이터용 - 선택사항)
    KIS_API_KEY = os.getenv('KIS_API_KEY', 'your_kis_api_key')
    KIS_API_SECRET = os.getenv('KIS_API_SECRET', 'your_kis_api_secret')
