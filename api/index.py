"""
Vercel Serverless Function Entry Point
"""
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Flask 앱 임포트
from app import app

# Vercel은 이 변수를 찾습니다
handler = app

