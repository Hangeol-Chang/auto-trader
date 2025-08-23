# 🚀 실시간 암호화폐 자동매매 시스템

하이브리드 DNN+LSTM 모델을 활용한 업비트 실시간 자동매매 시스템입니다.

## 📋 시스템 개요

- **모델**: DNN+LSTM 하이브리드 신경망
- **거래소**: 업비트 (Upbit)
- **데이터**: 실시간 웹소켓 1분봉 데이터
- **기술적 지표**: 15개 (MA, RSI, MACD, 볼린저 밴드, 스토캐스틱 등)
- **거래 방식**: 시장가 자동 매수/매도

## 🚀 빠른 시작

### 1. 환경 설정

업비트 API 키를 `private/keys.json`에 설정:
```json
{
  "COIN": [
    {
      "APP_KEY": "your_upbit_access_key",
      "APP_SECRET": "your_upbit_secret_key"
    }
  ]
}
```

### 2. 모델 학습 (선택사항)

기존 모델이 없거나 새로 학습하려면:
```bash
cd model
python train_crypto_rl_hybrid.py --market KRW-BTC --epochs 1000
```

### 3. 실시간 트레이딩 시작

```bash
python main.py
```

### 4. 대시보드 접속

브라우저에서 `http://localhost:5000/dashboard` 접속

## 📊 모니터링

### 웹 대시보드
- **URL**: http://localhost:5000/dashboard
- **기능**: 실시간 트레이딩 상태, 잔고, 예측 결과 모니터링

### API 엔드포인트

#### 트레이더 상태 조회
```bash
curl http://localhost:5000/api/monitoring/traders
```

#### 특정 트레이더 상세 정보
```bash
curl http://localhost:5000/api/monitoring/traders/0
```

#### 잔고 정보
```bash
curl http://localhost:5000/api/monitoring/traders/0/balance
```

## ⚙️ 설정 옵션

`main.py`에서 트레이더 설정 수정:

```python
USE_TRADERS = [
    lambda: trader.Live_Crypto_Trader(
        markets=['KRW-BTC', 'KRW-ETH', 'KRW-XRP', 'KRW-ADA'],  # 거래할 코인
        interval='1m',          # 분봉 간격
        num_steps=5,           # LSTM 시계열 스텝
        min_confidence=0.7,    # 최소 신뢰도 (0.7 = 70%)
        trading_amount=10000   # 매수 금액 (KRW)
    ),
]
```

### 주요 설정 항목

| 항목 | 설명 | 기본값 | 권장값 |
|------|------|--------|--------|
| `markets` | 거래할 코인 목록 | ['KRW-BTC', 'KRW-ETH'] | 3-5개 |
| `min_confidence` | 최소 거래 신뢰도 | 0.7 | 0.6-0.8 |
| `trading_amount` | 1회 거래 금액 (KRW) | 10000 | 5000-50000 |
| `num_steps` | LSTM 시계열 길이 | 5 | 3-10 |

## 🛡️ 리스크 관리

### 자동 안전장치
- **최소 주문 금액**: 5,000원
- **주문 쿨다운**: 1초 간격
- **신호 생성 간격**: 10초
- **신뢰도 필터**: 60% 이하 거래 제외

### 권장 설정
- **초기 자본**: 100,000원 이상
- **1회 거래 금액**: 총 자본의 5-10%
- **동시 거래 코인**: 3-5개
- **최소 신뢰도**: 70% 이상

## 📈 성능 지표

### 하이브리드 모델 성능 (백테스트)
- **DNN+LSTM**: 최대 5,242% 수익률
- **기존 DNN**: 최대 619% 수익률
- **성능 향상**: 약 8.5배

### 실시간 거래 특징
- **응답 속도**: 웹소켓 실시간 (< 100ms)
- **예측 주기**: 10초마다
- **데이터 처리**: 15개 기술적 지표 실시간 계산

## 🔧 문제 해결

### 일반적인 문제

#### 1. 모델 파일 없음
```
❌ [KRW-BTC] 모델 파일을 찾을 수 없음
```
**해결**: 모델 학습 실행
```bash
python model/train_crypto_rl_hybrid.py --market KRW-BTC
```

#### 2. API 키 오류
```
❌ 업비트 API 키 로드 실패
```
**해결**: `private/keys.json` 파일 확인

#### 3. 웹소켓 연결 실패
```
❌ 웹소켓 에러
```
**해결**: 인터넷 연결 및 업비트 서비스 상태 확인

#### 4. 잔고 부족
```
⚠️ [KRW-BTC] KRW 잔고 부족
```
**해결**: 업비트 계좌에 충분한 KRW 입금

### 로그 확인

실시간 로그 모니터링:
```bash
tail -f logs/server_$(date +%Y%m%d).log
```

## 📝 로그 해석

### 정상 동작 로그
```
2025-08-23 14:30:15 - Live_Crypto_Trader 시작
2025-08-23 14:30:16 - 업비트 웹소켓 연결 성공
2025-08-23 14:30:16 - 구독 시작: ['KRW-BTC', 'KRW-ETH']
2025-08-23 14:30:25 - [KRW-BTC] 예측: BUY (신뢰도: 0.850, 가격: 45,000,000원)
2025-08-23 14:30:26 - [KRW-BTC] 매수 주문 실행: 10,000원
2025-08-23 14:30:27 - [KRW-BTC] 매수 주문 성공: order_uuid_123
```

### 주의사항 로그
```
⚠️ [KRW-BTC] 낮은 신뢰도로 주문 스킵: 0.650
⚠️ [KRW-BTC] 주문 쿨다운 중
⚠️ [KRW-BTC] 최소 주문 금액 미달
```

## 🔄 고급 사용법

### 1. 실시간 설정 변경

API를 통해 실시간으로 설정 변경:
```bash
curl -X POST http://localhost:5000/api/monitoring/traders/0/control \
  -H "Content-Type: application/json" \
  -d '{
    "action": "update_config",
    "config": {
      "min_confidence": 0.8,
      "trading_amount": 20000
    }
  }'
```

### 2. 다중 트레이더 운영

`main.py`에서 여러 트레이더 설정:
```python
USE_TRADERS = [
    # 보수적 트레이더
    lambda: trader.Live_Crypto_Trader(
        markets=['KRW-BTC'],
        min_confidence=0.8,
        trading_amount=5000
    ),
    # 공격적 트레이더  
    lambda: trader.Live_Crypto_Trader(
        markets=['KRW-ETH', 'KRW-XRP'],
        min_confidence=0.6,
        trading_amount=15000
    ),
]
```

### 3. 백테스트와 실거래 비교

백테스트 실행:
```bash
python model/predict_hybrid_signals.py --market KRW-BTC --candles 100
```

## 📞 지원

### 개발자 가이드
- 모델 아키텍처: `ARCHITECTURE.md`
- API 문서: `http://localhost:5000/api/docs`
- 전체 가이드: `README_HYBRID_MODEL.md`

### 커뮤니티
- GitHub Issues
- Discord 채널
- 개발 문서 위키

---

⚠️ **면책 조항**: 이 시스템은 교육 및 연구 목적으로 제작되었습니다. 실제 거래 시 발생하는 손실에 대해서는 책임지지 않습니다. 항상 리스크 관리를 염두에 두고 소액으로 시작하세요.
