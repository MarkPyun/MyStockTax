# 🚀 Vercel 배포 가이드

이 문서는 주식 & 세금 관리 웹 애플리케이션을 GitHub과 Vercel을 통해 배포하는 방법을 설명합니다.

## 📋 사전 준비사항

1. **GitHub 계정**
2. **Vercel 계정** ([vercel.com](https://vercel.com)에서 가입)
3. **Git 설치** (로컬에서 버전 관리용)

## 🔧 1단계: GitHub 저장소 생성

### GitHub에서 새 저장소 생성
1. GitHub에 로그인
2. 우측 상단의 "+" 버튼 클릭 → "New repository" 선택
3. 저장소 정보 입력:
   - **Repository name**: `stock-tax-manager` (또는 원하는 이름)
   - **Description**: `PC와 모바일에서 사용 가능한 주식 & 세금 관리 웹 애플리케이션`
   - **Public** 선택 (Vercel 무료 플랜 사용 시)
   - "Create repository" 클릭

## 📤 2단계: 로컬 프로젝트를 GitHub에 업로드

### Git 초기화 및 커밋
```bash
# Git 저장소 초기화
git init

# 원격 저장소 추가 (GitHub 저장소 URL로 변경)
git remote add origin https://github.com/your-username/stock-tax-manager.git

# 모든 파일 추가
git add .

# 첫 번째 커밋
git commit -m "Initial commit: 주식 & 세금 관리 웹 애플리케이션"

# 메인 브랜치로 푸시
git branch -M main
git push -u origin main
```

## 🌐 3단계: Vercel 배포

### Vercel 대시보드에서 배포
1. [Vercel 대시보드](https://vercel.com/dashboard)에 로그인
2. "New Project" 버튼 클릭
3. GitHub 저장소 선택:
   - "Import Git Repository" 섹션에서 생성한 저장소 선택
   - "Import" 클릭

### 프로젝트 설정
1. **Project Name**: `stock-tax-manager` (또는 원하는 이름)
2. **Framework Preset**: "Other" 선택
3. **Root Directory**: `./` (기본값)
4. **Build Command**: 비워두기 (기본값 사용)
5. **Output Directory**: 비워두기 (기본값 사용)
6. **Install Command**: `pip install -r requirements-vercel.txt`

### 환경 변수 설정 (선택사항)
현재 애플리케이션은 환경 변수가 필요하지 않지만, 향후 확장 시:
- `FLASK_ENV=production`
- `PYTHONPATH=.`

### 배포 실행
1. "Deploy" 버튼 클릭
2. 배포 진행 상황 확인 (약 2-3분 소요)
3. 배포 완료 후 제공되는 URL로 접속 테스트

## 🔄 4단계: 자동 배포 설정

### GitHub 연동으로 자동 배포
- Vercel과 GitHub 저장소가 연동되면 자동으로 배포 설정됨
- `main` 브랜치에 푸시할 때마다 자동 배포
- Pull Request 생성 시 미리보기 배포

### 배포 확인
```bash
# 코드 수정 후
git add .
git commit -m "Update: 새로운 기능 추가"
git push origin main

# Vercel에서 자동 배포 확인
```

## 📱 5단계: 도메인 설정 (선택사항)

### 커스텀 도메인 연결
1. Vercel 대시보드에서 프로젝트 선택
2. "Settings" → "Domains" 이동
3. 원하는 도메인 입력
4. DNS 설정에 따라 도메인 연결

### 기본 Vercel 도메인
- `https://stock-tax-manager.vercel.app` 형태의 도메인 자동 제공
- HTTPS 자동 적용

## 🛠️ 6단계: 로컬 개발 및 테스트

### 로컬에서 실행
```bash
# 의존성 설치
pip install -r requirements.txt

# 개발 서버 실행
python app.py

# http://localhost:5000 에서 확인
```

### Vercel CLI 사용 (선택사항)
```bash
# Vercel CLI 설치
npm i -g vercel

# 프로젝트 폴더에서
vercel login
vercel

# 로컬에서 Vercel 환경 테스트
vercel dev
```

## 🔍 문제 해결

### 자주 발생하는 문제들

1. **배포 실패 - Python 버전 문제**
   - Vercel은 Python 3.9를 기본으로 사용
   - `runtime.txt` 파일로 버전 지정 가능

2. **모듈 import 오류**
   - `requirements-vercel.txt`에 모든 의존성 포함 확인
   - Flask-CORS 등 필요한 패키지 추가

3. **정적 파일 로드 오류**
   - `vercel.json`에서 라우팅 설정 확인
   - 템플릿 파일 경로 확인

4. **데이터 저장 문제**
   - Vercel은 서버리스 환경이므로 파일 시스템 저장 제한
   - 데이터베이스 연동 권장 (PostgreSQL, MongoDB 등)

## 📈 성능 최적화

### Vercel 최적화 팁
1. **정적 파일 캐싱**: CSS, JS 파일 최적화
2. **이미지 최적화**: WebP 포맷 사용
3. **번들 크기 최적화**: 불필요한 의존성 제거
4. **CDN 활용**: Vercel의 글로벌 CDN 자동 활용

## 🔒 보안 고려사항

1. **환경 변수**: 민감한 정보는 환경 변수로 관리
2. **HTTPS**: Vercel에서 자동 HTTPS 적용
3. **CORS**: 필요한 경우 CORS 설정 조정
4. **Rate Limiting**: API 호출 제한 고려

## 📞 지원

문제가 발생하거나 추가 도움이 필요한 경우:
- Vercel 문서: [vercel.com/docs](https://vercel.com/docs)
- GitHub Issues: 프로젝트 저장소에서 이슈 생성
- Flask 문서: [flask.palletsprojects.com](https://flask.palletsprojects.com/)

---

**배포 완료 후**: `https://your-project-name.vercel.app`에서 애플리케이션에 접속할 수 있습니다!
