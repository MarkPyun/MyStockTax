"""
Vercel Serverless Function Entry Point
"""
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Flask 앱 임포트
from app import app

# Vercel의 WSGI 핸들러 - app을 직접 export
handler = app

