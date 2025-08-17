# Test Scripts

이 폴더는 auto-trader 시스템의 다양한 기능을 테스트하기 위한 스크립트들을 포함합니다.

## 📁 파일 구성

### Python 테스트 스크립트

#### `test_stock_signal.py`
- **목적**: KIS API를 통한 주식 거래 신호 테스트
- **기능**: 
  - 주식 매수/매도 신호 전송
  - 지정가/시장가 주문 테스트
  - 주식 잔고 조회
  - 주식 현재가 조회
- **사용법**: `python test/test_stock_signal.py`

#### `test_ta_signal.py`
- **목적**: 신규 TradingView Signal API 테스트 (레거시 ta-signal 대체)
- **기능**:
  - 신규 `/api/tradingview/signal` 엔드포인트 테스트
  - 암호화폐 지정가/시장가 매수/매도 테스트
  - 간소화된 페이로드 구조 사용
  - 향상된 에러 처리 및 응답 확인
- **API 변경사항**:
  - 레거시: `/ta-signal` → 신규: `/api/tradingview/signal`
  - 중첩된 객체 구조 제거
  - 직접적인 ticker/action/price/quantity 필드 사용
- **사용법**: `python test/test_ta_signal.py`

#### `test_pine_script.py`
- **목적**: Pine Script 전략 테스트
- **기능**:
  - Pine Script 기반 전략 검증
  - 백테스팅 결과 확인
- **사용법**: `python test/test_pine_script.py`

#### `test.py`
- **목적**: 일반적인 시스템 기능 테스트
- **기능**:
  - 기본 API 연결 테스트
  - 시스템 상태 확인
- **사용법**: `python test/test.py`

### JSON 테스트 데이터

#### `test_stock_requests.json`
- **목적**: 주식 거래 API 테스트용 JSON 샘플
- **내용**:
  - 주식 매수/매도 신호 샘플
  - 인기 한국 주식 종목 코드
  - curl 명령어 예제
  - TradingView 웹훅 시뮬레이션 데이터

#### `test_requests.json`
- **목적**: 신규 API 테스트용 JSON 샘플 (레거시 ta-signal 대체)
- **내용**:
  - 신규 `/api/tradingview/signal` API 샘플
  - 간소화된 페이로드 구조
  - 암호화폐 거래 신호 샘플 (지정가/시장가)
  - 다양한 API 엔드포인트 테스트 데이터
  - curl 명령어 예제
  - API 마이그레이션 가이드

## 🚀 빠른 시작

### 1. 전체 시스템 테스트
```bash
# 서버 실행 (별도 터미널)
python main.py

# 주식 거래 시스템 테스트
python test/test_stock_signal.py

# 암호화폐 거래 시스템 테스트
python test/test_ta_signal.py
```

### 2. 개별 기능 테스트
```bash
# Pine Script 전략 테스트
python test/test_pine_script.py

# 기본 시스템 기능 테스트
python test/test.py
```

### 3. API 테스트 (curl) - 신규 API
```bash
# 신규 암호화폐 매수 신호
curl -X POST http://localhost:5000/api/tradingview/signal \
  -H "Content-Type: application/json" \
  -d '{"ticker":"BTCKRW","action":"buy","price":95000000,"quantity":0.001,"strategy":"Test"}'

# 신규 암호화폐 매도 신호  
curl -X POST http://localhost:5000/api/tradingview/signal \
  -H "Content-Type: application/json" \
  -d '{"ticker":"BTCKRW","action":"sell","price":94000000,"quantity":0.001,"strategy":"Test"}'

# 암호화폐 잔고 조회
curl -X GET http://localhost:5000/api/trading/balance

# 주식 거래 API (test_stock_requests.json 참조)
curl -X GET http://localhost:5000/api/trading/stock-price/005930
```

## 📋 테스트 시나리오

### 주식 거래 테스트 순서
1. 서버 상태 확인
2. 주식 현재가 조회
3. 주식 잔고 조회
4. 시장가 매수 주문
5. 지정가 매수 주문
6. 지정가 매도 주문
7. 시장가 매도 주문

### 암호화폐 거래 테스트 순서 (신규 API)
1. TradingView/Trading API 상태 확인
2. 지원 마켓 조회
3. 암호화폐 잔고 조회
4. 신호 테스트 엔드포인트 확인
5. 지정가 매수/매도 신호 테스트
6. 시장가 매수/매도 신호 테스트

### API 마이그레이션 정보
- **레거시 엔드포인트**: `/ta-signal`
- **신규 엔드포인트**: `/api/tradingview/signal`
- **주요 변경사항**:
  - 간소화된 페이로드 구조
  - 직접적인 ticker/action/price/quantity 필드
  - timestamp 및 exchange 필드 추가
  - 중첩된 strategy/instrument/order 객체 제거
  - 향상된 에러 처리 및 응답 형식

## ⚠️ 주의사항

- **실제 거래 주의**: 테스트 스크립트는 실제 거래를 수행할 수 있습니다. 모의 계좌나 소액으로 테스트하세요.
- **API 키 설정**: 테스트 전에 `private/keys.json`에 올바른 API 키가 설정되어 있는지 확인하세요.
- **서버 실행**: 대부분의 테스트는 서버가 실행 중일 때만 동작합니다.
- **시장 시간**: 주식 거래 테스트는 장중에만 정상 동작할 수 있습니다.

## 🔧 트러블슈팅

### 일반적인 문제
- **403 Forbidden**: API 키 확인 필요
- **Connection Error**: 서버 실행 상태 확인
- **Timeout**: 네트워크 연결 상태 확인
- **Invalid Request**: JSON 포맷 및 필수 필드 확인

### 디버깅 팁
- 각 테스트 스크립트는 상세한 로그를 출력합니다
- `logs/` 폴더의 서버 로그를 확인하세요
- Discord 알림이 활성화되어 있다면 거래 결과를 확인할 수 있습니다
