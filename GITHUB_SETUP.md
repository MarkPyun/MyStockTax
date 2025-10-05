# 🐙 GitHub 저장소 설정 가이드

이 문서는 로컬 프로젝트를 GitHub 저장소에 업로드하는 단계별 가이드입니다.

## 📋 1단계: GitHub에서 새 저장소 생성

### GitHub 웹사이트에서 저장소 생성
1. [GitHub.com](https://github.com)에 로그인
2. 우측 상단의 "+" 버튼 클릭 → "New repository" 선택
3. 저장소 정보 입력:
   ```
   Repository name: stock-tax-manager
   Description: PC와 모바일에서 사용 가능한 주식 & 세금 관리 웹 애플리케이션
   Visibility: Public (Vercel 무료 플랜 사용 시)
   ```
4. **중요**: "Add a README file", "Add .gitignore", "Choose a license" 체크 해제
5. "Create repository" 클릭

## 🔗 2단계: 원격 저장소 연결

### 명령어 실행 (PowerShell에서)
```powershell
# 원격 저장소 추가 (GitHub 저장소 URL로 변경하세요)
git remote add origin https://github.com/YOUR_USERNAME/stock-tax-manager.git

# 현재 브랜치를 main으로 변경
git branch -M main

# GitHub에 푸시
git push -u origin main
```

### GitHub 저장소 URL 찾는 방법
1. GitHub 저장소 페이지에서 초록색 "Code" 버튼 클릭
2. "HTTPS" 탭에서 URL 복사
3. 위 명령어의 `YOUR_USERNAME`을 실제 GitHub 사용자명으로 변경

## ✅ 3단계: 업로드 확인

### GitHub에서 확인
1. GitHub 저장소 페이지 새로고침
2. 다음 파일들이 업로드되었는지 확인:
   - `app.py` (메인 애플리케이션)
   - `templates/` 폴더 (HTML 템플릿)
   - `requirements.txt` (Python 의존성)
   - `vercel.json` (Vercel 배포 설정)
   - `README.md` (프로젝트 문서)
   - `DEPLOYMENT.md` (배포 가이드)

## 🔄 4단계: 향후 업데이트 방법

### 코드 수정 후 GitHub 업데이트
```powershell
# 변경사항 확인
git status

# 모든 변경사항 추가
git add .

# 커밋 메시지와 함께 커밋
git commit -m "Update: 새로운 기능 추가"

# GitHub에 푸시
git push origin main
```

## 🚀 5단계: Vercel 연동 준비

GitHub 저장소가 준비되면 다음 단계로 진행:
1. [Vercel 대시보드](https://vercel.com/dashboard) 접속
2. "New Project" 클릭
3. GitHub 저장소 선택
4. 자동 배포 설정 완료

## 🔧 문제 해결

### 자주 발생하는 문제들

1. **인증 오류 (401 Unauthorized)**
   ```powershell
   # GitHub Personal Access Token 사용
   git remote set-url origin https://YOUR_TOKEN@github.com/YOUR_USERNAME/stock-tax-manager.git
   ```

2. **브랜치 충돌**
   ```powershell
   # 강제 푸시 (주의: 기존 내용 덮어씀)
   git push -f origin main
   ```

3. **파일 크기 제한**
   - GitHub는 100MB 이상 파일 업로드 제한
   - 대용량 파일은 Git LFS 사용 권장

## 📝 추가 설정 (선택사항)

### GitHub Pages 설정 (정적 사이트용)
1. 저장소 → Settings → Pages
2. Source를 "Deploy from a branch" 선택
3. Branch를 "main" 선택
4. Save 클릭

### Issues 및 Wiki 활성화
1. 저장소 → Settings → Features
2. Issues, Wiki 체크박스 활성화

---

**다음 단계**: GitHub 저장소 준비가 완료되면 `DEPLOYMENT.md` 파일의 Vercel 배포 가이드를 따라 진행하세요!
