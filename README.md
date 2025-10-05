# 주식 & 세금 관리 웹 애플리케이션

PC와 모바일에서 모두 사용 가능한 반응형 주식 포트폴리오 관리 웹 애플리케이션입니다.

## 🚀 주요 기능

- **포트폴리오 관리**: 주식 보유 현황 및 수익률 추적
- **거래 기록**: 매수/매도 거래 내역 관리
- **대시보드**: 실시간 포트폴리오 요약 정보
- **반응형 디자인**: PC와 모바일 모두 최적화
- **데이터 저장**: JSON 파일 기반 로컬 데이터 저장

## 🛠️ 기술 스택

- **Backend**: Python Flask
- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **UI Framework**: Bootstrap 5
- **Icons**: Font Awesome
- **데이터 저장**: JSON 파일

## 📦 설치 및 실행

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 애플리케이션 실행

```bash
python app.py
```

### 3. 브라우저에서 접속

```
http://localhost:5000
```

## 📱 모바일 지원

- 반응형 디자인으로 모든 디바이스에서 최적화
- 터치 친화적인 UI/UX
- 모바일 브라우저에서 PWA(Progressive Web App) 지원

## 🔧 API 엔드포인트

### 주식 관리
- `GET /api/stocks` - 주식 목록 조회
- `POST /api/stocks` - 새 주식 추가
- `PUT /api/stocks/<id>` - 주식 정보 수정
- `DELETE /api/stocks/<id>` - 주식 삭제

### 거래 관리
- `GET /api/transactions` - 거래 내역 조회
- `POST /api/transactions` - 새 거래 추가

### 포트폴리오
- `GET /api/portfolio/summary` - 포트폴리오 요약

## 📊 데이터 구조

### 주식 (Stock)
```json
{
  "id": 1,
  "name": "삼성전자",
  "symbol": "005930",
  "quantity": 100,
  "price": 75000,
  "added_date": "2024-01-01T00:00:00"
}
```

### 거래 (Transaction)
```json
{
  "id": 1,
  "stock_id": 1,
  "type": "buy",
  "quantity": 10,
  "price": 70000,
  "date": "2024-01-01"
}
```

## 🎨 UI/UX 특징

- **다크 모드 지원**: 시스템 설정에 따른 자동 다크 모드
- **부드러운 애니메이션**: 카드 호버 효과 및 전환 애니메이션
- **직관적인 네비게이션**: 아이콘과 함께하는 명확한 메뉴
- **반응형 그리드**: 화면 크기에 따른 자동 레이아웃 조정

## 🔒 보안 및 데이터

- 로컬 JSON 파일 저장으로 데이터 프라이버시 보장
- CORS 설정으로 외부 접근 제어
- 입력 데이터 검증 및 에러 처리

## 🚀 배포 옵션

### 로컬 개발
```bash
python app.py
```

### 프로덕션 배포
```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## 📈 향후 개발 계획

- [ ] 사용자 인증 시스템
- [ ] 실시간 주가 연동
- [ ] 세금 계산 기능
- [ ] 차트 및 그래프 시각화
- [ ] 데이터베이스 연동
- [ ] PWA 기능 강화

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 📞 지원

문제가 발생하거나 제안사항이 있으시면 이슈를 생성해 주세요.
