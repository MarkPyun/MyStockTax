"""
Vercel Serverless Function Entry Point
"""
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

print(f"[Vercel] Python version: {sys.version}")
print(f"[Vercel] Project root: {project_root}")
print(f"[Vercel] Python path: {sys.path[:3]}")

# Flask 앱 임포트
try:
    from app import app
    print("[Vercel] ✓ Flask app imported successfully")
    
    # Vercel은 이 변수를 찾습니다
    handler = app
    
except Exception as e:
    print(f"[Vercel] ✗ Error importing app: {e}")
    import traceback
    traceback.print_exc()
    raise

