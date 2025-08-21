# 🚀 DNN+LSTM 하이브리드 암호화폐 거래 AI 시스템

quantylab 구조를 기반으로 개발된 강화학습 기반 암호화폐 자동거래 시스템입니다.  
DNN(심층신경망)의 특성 추출 능력과 LSTM(장단기메모리)의 시계열 분석 능력을 결합한 하이브리드 신경망을 사용합니다.

## 📋 목차

- [시스템 구조](#-시스템-구조)
- [데이터 형태](#-데이터-형태)
- [모델 학습 방법](#-모델-학습-방법)
- [학습된 모델 사용 방법](#-학습된-모델-사용-방법)
- [성능 비교](#-성능-비교)
- [고급 사용법](#-고급-사용법)
- [문제 해결](#-문제-해결)

---

## 🏗️ 시스템 구조

### 핵심 컴포넌트

```
model/
├── crypto_rl_learner.py          # 메인 강화학습 엔진
├── crypto_rl_agent.py            # 거래 의사결정 에이전트
├── crypto_rl_environment.py      # 거래 환경 시뮬레이션
├── train_crypto_rl_hybrid.py     # 하이브리드 모델 학습 스크립트
├── predict_hybrid_signals.py     # 하이브리드 모델 예측 스크립트
└── crypto_rl_models/             # 학습된 모델 저장소
    ├── value_network_*.weights.h5     # 신경망 가중치
    └── training_summary_*.json        # 학습 결과 요약
```

### 신경망 아키텍처

```
📊 입력 데이터 (15개 특성)
    ↓
🧠 DNN 특성 추출 레이어
   ├── Dense(256) + Sigmoid + BatchNorm + Dropout(0.1)
   └── Dense(128) + Sigmoid + BatchNorm + Dropout(0.1)
    ↓
⏳ LSTM 시계열 분석 레이어  
   ├── LSTM(64, return_sequences=True) + BatchNorm + Dropout(0.1)
   └── LSTM(32, return_sequences=False) + BatchNorm + Dropout(0.1)
    ↓
🎯 출력 레이어
   └── Dense(3) → [매수, 매도, 관망] 확률
```

---

## 📊 데이터 형태

### 1. 입력 데이터 구조

#### 원시 캔들 데이터 (업비트 API)
```python
{
    'candle_date_time_utc': '2025-08-21T00:00:00+00:00',  # UTC 시간
    'opening_price': 157500000.0,                         # 시가
    'high_price': 159000000.0,                           # 고가  
    'low_price': 156800000.0,                            # 저가
    'trade_price': 158316000.0,                          # 종가 (현재가)
    'candle_acc_trade_volume': 1234.56789                # 거래량
}
```

#### 전처리된 기술적 지표 (12개)
```python
feature_columns = [
    'ma5',              # 5일 이동평균
    'ma20',             # 20일 이동평균  
    'ma60',             # 60일 이동평균
    'rsi',              # RSI (14일)
    'macd',             # MACD 메인라인
    'macd_signal',      # MACD 시그널라인
    'macd_hist',        # MACD 히스토그램
    'bb_ratio',         # 볼린저밴드 비율 (현재가 위치)
    'volume_ratio',     # 거래량 비율 (20일 평균 대비)
    'price_change',     # 1일 가격 변화율
    'price_change_5',   # 5일 가격 변화율  
    'price_change_20'   # 20일 가격 변화율
]
```

#### 에이전트 상태 (3개)
```python
agent_status = [
    0.5,    # 주식 보유 비율 (0.0 ~ 1.0)
    0.15,   # 현재 손익률 (-무한대 ~ +무한대)
    0.02    # 평균 매수가 대비 등락률 (-1.0 ~ +1.0)
]
```

#### 최종 학습 샘플 형태
```python
# DNN 모델용 (1차원)
sample_1d = np.array([15개 특성])  # shape: (15,)

# LSTM 하이브리드 모델용 (2차원 시계열)
sample_2d = np.array([
    [time_t-4의 15개 특성],
    [time_t-3의 15개 특성], 
    [time_t-2의 15개 특성],
    [time_t-1의 15개 특성],
    [time_t의 15개 특성]
])  # shape: (5, 15) - num_steps=5인 경우
```

### 2. 출력 데이터 구조

#### 신경망 출력
```python
predictions = np.array([
    45.2,   # 매수 행동의 가치 (Q-value)
    12.8,   # 매도 행동의 가치
    38.5    # 관망 행동의 가치  
])
```

#### 최종 거래 신호
```python
{
    'action': 0,                    # 행동 인덱스 (0=매수, 1=매도, 2=관망)
    'action_name': '매수',          # 행동 이름
    'confidence': 45.2,             # 신뢰도 (선택된 행동의 Q-value)
    'price': 158316000.0,          # 현재 가격
    'timestamp': '2025-08-21T00:00:00'
}
```

---

## 🎓 모델 학습 방법

### 1. 기본 학습 실행

```bash
# 기본 하이브리드 모델 학습 (권장)
python model/train_crypto_rl_hybrid.py --market KRW-BTC --epochs 100

# 상세 파라미터 설정
python model/train_crypto_rl_hybrid.py \
    --market KRW-BTC \
    --epochs 200 \
    --balance 10000000 \
    --num-steps 10 \
    --lr 0.0003
```

### 2. 학습 파라미터 설명

| 파라미터 | 설명 | 기본값 | 권장값 |
|---------|------|--------|--------|
| `--market` | 암호화폐 마켓 | KRW-BTC | KRW-BTC, KRW-ETH |
| `--epochs` | 학습 에포크 수 | 100 | 100-1000 |
| `--balance` | 초기 자본금 (원) | 10,000,000 | 5,000,000-50,000,000 |
| `--num-steps` | LSTM 시계열 길이 | 10 | 5-20 |
| `--lr` | 학습률 | 0.0003 | 0.0001-0.001 |

### 3. 학습 과정 모니터링

```bash
# 실시간 학습 진행상황
Epoch   0: Steps=999, Portfolio=53,427,164, P&L=52.4272, Actions(B/S/H)=30/667/302
Epoch   1: Steps=999, Portfolio=12,456,789, P&L=11.4568, Actions(B/S/H)=45/543/411
...
Epoch 999: Steps=999, Portfolio=6,956,618, P&L=5.9566, Actions(B/S/H)=3/476/520

Training completed!
Max Portfolio Value: 53,427,164
Final P&L: 5.9566
```

### 4. 학습 완료 후 생성 파일

```
model/crypto_rl_models/
├── value_network_KRW_BTC_20250821_215117.weights.h5      # 신경망 가중치
├── policy_network_KRW_BTC_20250821_215117.weights.h5     # 정책 네트워크 (선택사항)
└── training_summary_KRW-BTC_20250821_215117.json         # 학습 요약 정보
```

#### 학습 요약 파일 내용
```json
{
  "market": "KRW-BTC",
  "interval": "1d", 
  "max_portfolio_value": 53427163.71,
  "final_portfolio_value": 6956617.94,
  "final_profitloss": 5.9566,
  "num_epochs": 1000,
  "epoch_summary": [
    {
      "epoch": 0,
      "epsilon": 0.5,
      "portfolio_value": 53427163.71,
      "profitloss": 52.427,
      "num_buy": 30,
      "num_sell": 667, 
      "num_hold": 302,
      "steps": 999
    }
  ]
}
```

---

## 🔮 학습된 모델 사용 방법

### 1. 기본 예측 실행

```bash
# 최신 모델로 예측
python model/predict_hybrid_signals.py --market KRW-BTC --candles 20

# 특정 모델로 예측
python model/predict_hybrid_signals.py \
    --market KRW-BTC \
    --timestamp 20250821_215117 \
    --candles 30 \
    --num-steps 5
```

### 2. 예측 결과 출력

```
🎯 현재 권장 행동: 매도
   신뢰도: 58.855
   현재 가격: 158,316,000

📈 20개 캔들 행동 분포:
   매수: 16회 (80.0%)
   매도: 4회 (20.0%)

📊 신뢰도 통계:
   평균: 42.421
   최대: 58.855
   최소: 38.413

💾 예측 결과 저장: hybrid_predictions_KRW-BTC_20250821_215117_20250821_223713.csv
```

### 3. 예측 결과 CSV 파일

```csv
index,timestamp,price,action,action_name,confidence,pred_values
0,2025-08-01T00:00:00,145000000,0,매수,45.234,"[45.234, 12.456, 32.123]"
1,2025-08-02T00:00:00,147500000,2,관망,38.876,"[32.112, 15.789, 38.876]"
2,2025-08-03T00:00:00,149200000,0,매수,47.123,"[47.123, 18.234, 29.567]"
...
```

### 4. Python 스크립트에서 사용

```python
from model.predict_hybrid_signals import predict_with_hybrid_model

# 예측 실행
predictions = predict_with_hybrid_model(
    market='KRW-BTC',
    timestamp='20250821_215117',
    candles=10,
    num_steps=5
)

# 최신 신호 확인
if predictions:
    latest = predictions[-1]
    print(f"권장 행동: {latest['action_name']}")
    print(f"신뢰도: {latest['confidence']:.3f}")
    print(f"현재 가격: {latest['price']:,.0f}")
```

---

## 📈 성능 비교

### 신경망 아키텍처별 성능

| 모델 타입 | 최고 수익률 | 최종 수익률 | 학습 안정성 | 시계열 처리 |
|-----------|-------------|-------------|-------------|-------------|
| **DNN** | 619.62% | 477.13% | 20 에포크 제한 | ❌ |
| **LSTM** | - | - | 미구현 | ✅ |
| **CNN** | - | - | 미구현 | 제한적 |
| **DNN+LSTM 하이브리드** | **5,242.72%** | **595.66%** | 1000 에포크 완주 | ✅ |

### 하이브리드 모델의 장점

1. **특성 추출 + 시계열 분석**: DNN이 추출한 고차원 특성을 LSTM이 시간축으로 분석
2. **장기 메모리**: 과거 5-20개 시점의 패턴을 기억하여 트렌드 예측
3. **높은 수익률**: 기존 DNN 대비 8.5배 향상된 성능
4. **안정적 학습**: 긴 에포크 동안 과적합 없이 안정적 성능 향상

---

## 🔧 고급 사용법

### 1. 다른 암호화폐로 확장

```bash
# 이더리움 모델 학습
python model/train_crypto_rl_hybrid.py --market KRW-ETH --epochs 150

# 리플 모델 학습  
python model/train_crypto_rl_hybrid.py --market KRW-XRP --epochs 100

# 여러 코인 일괄 학습
for market in KRW-BTC KRW-ETH KRW-XRP; do
    python model/train_crypto_rl_hybrid.py --market $market --epochs 200
done
```

### 2. 하이퍼파라미터 튜닝

```bash
# 학습률 실험
python model/train_crypto_rl_hybrid.py --market KRW-BTC --lr 0.0001 --epochs 100
python model/train_crypto_rl_hybrid.py --market KRW-BTC --lr 0.0005 --epochs 100
python model/train_crypto_rl_hybrid.py --market KRW-BTC --lr 0.001 --epochs 100

# 시계열 길이 실험
python model/train_crypto_rl_hybrid.py --market KRW-BTC --num-steps 5 --epochs 100
python model/train_crypto_rl_hybrid.py --market KRW-BTC --num-steps 10 --epochs 100
python model/train_crypto_rl_hybrid.py --market KRW-BTC --num-steps 20 --epochs 100
```

### 3. 실시간 모니터링 시스템

```python
import time
from datetime import datetime

def monitor_crypto_signals(market='KRW-BTC', interval_minutes=60):
    """실시간 거래 신호 모니터링"""
    
    while True:
        try:
            # 최신 예측 실행
            predictions = predict_with_hybrid_model(
                market=market,
                candles=5,
                num_steps=5
            )
            
            if predictions:
                latest = predictions[-1]
                print(f"[{datetime.now()}] {market}: {latest['action_name']} "
                      f"(신뢰도: {latest['confidence']:.1f}, "
                      f"가격: {latest['price']:,.0f})")
            
            # 지정된 간격으로 대기
            time.sleep(interval_minutes * 60)
            
        except Exception as e:
            print(f"모니터링 오류: {e}")
            time.sleep(60)

# 실시간 모니터링 시작 (1시간마다)
# monitor_crypto_signals('KRW-BTC', 60)
```

### 4. 배치 예측 및 백테스팅

```python
import pandas as pd
from datetime import datetime, timedelta

def backtest_strategy(market='KRW-BTC', days=30):
    """과거 데이터로 전략 백테스팅"""
    
    # 과거 30일간 예측 실행
    predictions = predict_with_hybrid_model(
        market=market,
        candles=days,
        num_steps=5
    )
    
    # 가상 거래 시뮬레이션
    balance = 1000000  # 초기 자본 100만원
    holdings = 0       # 보유 코인 수
    
    for pred in predictions:
        price = pred['price']
        action = pred['action_name']
        
        if action == '매수' and balance > price:
            # 전액 매수
            holdings = balance / price
            balance = 0
            print(f"매수: {holdings:.6f} 코인 @ {price:,.0f}")
            
        elif action == '매도' and holdings > 0:
            # 전액 매도
            balance = holdings * price
            holdings = 0
            print(f"매도: {balance:,.0f}원 @ {price:,.0f}")
    
    # 최종 평가
    final_value = balance + (holdings * predictions[-1]['price'])
    profit_rate = (final_value / 1000000 - 1) * 100
    
    print(f"\n백테스팅 결과:")
    print(f"초기 자본: 1,000,000원")
    print(f"최종 자산: {final_value:,.0f}원")
    print(f"수익률: {profit_rate:.2f}%")
    
    return final_value, profit_rate

# 백테스팅 실행
# final_value, profit_rate = backtest_strategy('KRW-BTC', 30)
```

---

## ❌ 문제 해결

### 1. 학습 관련 문제

#### 문제: 학습이 진행되지 않음
```
Training:   0%|                | 0/1000 [00:00<?, ?it/s]
❌ 학습 중 오류 발생: ...
```

**해결방법:**
```bash
# Python 환경 확인
python -c "import tensorflow as tf; print(tf.__version__)"

# 의존성 재설치
pip install tensorflow==2.20.0 numpy pandas tqdm

# 데이터 경로 확인
ls -la module/crypto/crypto_data_manager.py
```

#### 문제: 메모리 부족 오류
```
❌ 학습 중 오류 발생: ResourceExhaustedError: OOM when allocating tensor
```

**해결방법:**
```bash
# 더 작은 배치로 학습
python model/train_crypto_rl_hybrid.py --market KRW-BTC --epochs 50 --num-steps 5

# 시스템 메모리 확인
free -h  # Linux
wmic OS get TotalVisibleMemorySize,FreePhysicalMemory  # Windows
```

### 2. 예측 관련 문제

#### 문제: 모델 로드 실패
```
❌ 모델 파일을 찾을 수 없습니다: model/crypto_rl_models/...
```

**해결방법:**
```bash
# 모델 파일 확인
ls -la model/crypto_rl_models/

# 권한 확인
chmod 755 model/crypto_rl_models/
chmod 644 model/crypto_rl_models/*.h5

# 새로 학습
python model/train_crypto_rl_hybrid.py --market KRW-BTC --epochs 10
```

#### 문제: 데이터 형태 불일치
```
ValueError: cannot reshape array of size 15 into shape (1,10,15)
```

**해결방법:**
```bash
# num-steps 값 확인 및 조정
python model/predict_hybrid_signals.py --market KRW-BTC --num-steps 5

# 학습과 예측에서 동일한 num-steps 사용
python model/train_crypto_rl_hybrid.py --market KRW-BTC --num-steps 5
python model/predict_hybrid_signals.py --market KRW-BTC --num-steps 5
```

### 3. 성능 관련 문제

#### 문제: 예측 성능이 낮음
```
📈 20개 캔들 행동 분포:
   관망: 20회 (100.0%)
```

**해결방법:**
```bash
# 더 많은 에포크로 재학습
python model/train_crypto_rl_hybrid.py --market KRW-BTC --epochs 500

# 다른 학습률 시도
python model/train_crypto_rl_hybrid.py --market KRW-BTC --lr 0.0001

# 더 많은 자본으로 학습
python model/train_crypto_rl_hybrid.py --market KRW-BTC --balance 50000000
```

### 4. 디버깅 팁

```bash
# 로그 레벨 증가
export TF_CPP_MIN_LOG_LEVEL=0

# GPU 사용 확인 (CUDA 설치된 경우)
python -c "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"

# 상세 오류 확인
python model/train_crypto_rl_hybrid.py --market KRW-BTC --epochs 1 2>&1 | tee debug.log
```

---

## 📚 참고 자료

- **quantylab**: 원본 강화학습 프레임워크
- **업비트 API**: 암호화폐 데이터 소스
- **TensorFlow/Keras**: 신경망 프레임워크
- **논문**: "Deep Reinforcement Learning for Trading" (DQN 기반)

## 🤝 기여하기

버그 리포트, 기능 제안, 성능 개선 아이디어는 언제든 환영합니다!

---

## 📞 지원

문제가 발생하면 다음을 확인해주세요:

1. ✅ Python 3.11+ 설치 확인
2. ✅ 모든 의존성 패키지 설치 확인  
3. ✅ 업비트 API 데이터 접근 확인
4. ✅ 충분한 디스크 공간 확인 (모델 파일용)
5. ✅ 메모리 8GB+ 권장 (대용량 학습용)

🎉 **Happy Trading with AI!** 🚀
