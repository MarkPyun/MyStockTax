# 🐙 GitHub & Vercel 배포 완전 가이드

**GitHub 계정**: a01099910788@gmail.com

## 📋 1단계: GitHub에서 새 저장소 생성

### GitHub 웹사이트에서 저장소 생성
1. [GitHub.com](https://github.com)에 로그인 (a01099910788@gmail.com)
2. 우측 상단의 "+" 버튼 클릭 → "New repository" 선택
3. 저장소 정보 입력:
   ```
   Repository name: stock-tax-manager
   Description: PC와 모바일에서 사용 가능한 주식 & 세금 관리 웹 애플리케이션
   Visibility: Public ✅ (Vercel 무료 플랜 사용 시 필수)
   ```
4. **중요**: 다음 항목들은 체크 해제:
   - ❌ Add a README file
   - ❌ Add .gitignore  
   - ❌ Choose a license
5. "Create repository" 클릭

## 🔗 2단계: 로컬 프로젝트를 GitHub에 연결

### PowerShell에서 다음 명령어들을 순서대로 실행:

```powershell
# 1. 원격 저장소 추가
git remote add origin https://github.com/a01099910788/stock-tax-manager.git

# 2. 현재 브랜치를 main으로 변경
git branch -M main

# 3. GitHub에 푸시 (첫 번째 업로드)
git push -u origin main
```

### 만약 인증 오류가 발생한다면:
```powershell
# GitHub Personal Access Token 사용
# 1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
# 2. "Generate new token" 클릭
# 3. 권한 선택: repo (전체 선택)
# 4. 토큰 복사 후 아래 명령어 사용:

git remote set-url origin https://YOUR_TOKEN@github.com/a01099910788/stock-tax-manager.git
git push -u origin main
```

## 🌐 3단계: Vercel 배포

### Vercel 대시보드에서 배포
1. [Vercel.com](https://vercel.com)에 가입/로그인
2. GitHub 계정과 연동
3. "New Project" 버튼 클릭
4. 저장소 선택: `a01099910788/stock-tax-manager`
5. "Import" 클릭

### 프로젝트 설정
```
Project Name: stock-tax-manager
Framework Preset: Other
Root Directory: ./
Build Command: (비워두기)
Output Directory: (비워두기)
Install Command: pip install -r requirements-vercel.txt
```

### 환경 변수 (현재는 필요 없음)
- 현재 애플리케이션은 환경 변수가 필요하지 않습니다.

### 배포 실행
1. "Deploy" 버튼 클릭
2. 배포 진행 상황 확인 (약 2-3분 소요)
3. 완료 후 제공되는 URL 확인

## ✅ 4단계: 배포 확인

### 배포 완료 후 확인사항
1. **Vercel URL**: `https://stock-tax-manager-xxx.vercel.app`
2. **모바일 테스트**: 스마트폰에서 URL 접속
3. **기능 테스트**: 주식 추가, 거래 기록 등 모든 기능 확인

## 🔄 5단계: 자동 배포 설정 확인

### GitHub 연동으로 자동 배포
- ✅ GitHub 저장소와 Vercel이 연동됨
- ✅ `main` 브랜치에 푸시할 때마다 자동 배포
- ✅ Pull Request 생성 시 미리보기 배포

### 코드 수정 후 배포 테스트
```powershell
# 코드 수정 후
git add .
git commit -m "Update: 새로운 기능 추가"
git push origin main

# Vercel에서 자동 배포 확인 (약 2-3분 소요)
```

## 📱 6단계: 모바일 최적화 확인

### 모바일에서 테스트할 기능들
1. **반응형 레이아웃**: 화면 크기별 UI 확인
2. **터치 인터페이스**: 버튼 터치 반응성
3. **네비게이션**: 햄버거 메뉴 작동
4. **모달**: 주식 추가, 거래 기록 모달
5. **폼 입력**: 키보드 입력 최적화

## 🔧 문제 해결

### 자주 발생하는 문제들

1. **GitHub 인증 오류**
   ```powershell
   # Personal Access Token 생성 후 사용
   git config --global user.name "Your Name"
   git config --global user.email "a01099910788@gmail.com"
   ```

2. **Vercel 빌드 오류**
   - `requirements-vercel.txt` 파일 확인
   - Python 버전 호환성 확인 (`runtime.txt`)

3. **모바일 접속 문제**
   - HTTPS 확인
   - 브라우저 캐시 삭제
   - 다른 브라우저에서 테스트

## 📊 배포 후 관리

### 정기적인 업데이트
```powershell
# 로컬에서 코드 수정
# ...

# GitHub에 업데이트
git add .
git commit -m "Update: 버그 수정 또는 새 기능 추가"
git push origin main

# Vercel에서 자동 배포 확인
```

### 모니터링
- Vercel 대시보드에서 배포 상태 확인
- GitHub에서 코드 변경 이력 관리
- 사용자 피드백 수집 및 개선

---

## 🎯 최종 확인 체크리스트

- [ ] GitHub 저장소 생성 완료
- [ ] 로컬 코드 업로드 완료  
- [ ] Vercel 프로젝트 생성 완료
- [ ] 배포 성공 확인
- [ ] PC에서 접속 테스트
- [ ] 모바일에서 접속 테스트
- [ ] 모든 기능 정상 작동 확인

**배포 완료 후 URL**: `https://stock-tax-manager-xxx.vercel.app`

---

**🚀 성공적인 배포를 위해 위 단계들을 순서대로 진행해주세요!**
