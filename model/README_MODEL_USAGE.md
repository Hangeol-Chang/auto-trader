# Crypto RL 모델 사용 가이드

## 📁 모델 저장 위치

학습된 모델은 다음 위치에 저장됩니다:

```
model/crypto_rl_models/
├── value_network_KRW_BTC_20250821_211833.weights.h5     # 신경망 가중치
├── policy_network_KRW_BTC_20250821_211833.weights.h5    # 정책 네트워크 (선택사항)
└── training_summary_KRW-BTC_20250821_211833.json        # 학습 요약 정보
```

### 파일 구성:
- **`.weights.h5`**: TensorFlow/Keras 신경망 가중치 파일
- **`.json`**: 학습 과정과 성능 정보가 담긴 요약 파일

---

## 🚀 모델 사용 방법

### 1. 사용 가능한 모델 목록 확인

```bash
python model/predict_crypto_signals.py --list-models
```

출력 예시:
```
=== 사용 가능한 모델 목록 ===
1. KRW-BTC - 20250821_211815
   모델 파일: value_network_KRW_BTC_20250821_211815.weights.h5
   요약 파일: training_summary_KRW-BTC_20250821_211815.json

2. KRW-BTC - 20250821_211833
   모델 파일: value_network_KRW_BTC_20250821_211833.weights.h5
   요약 파일: training_summary_KRW-BTC_20250821_211833.json
```

### 2. 거래 신호 예측 실행

#### 기본 예측 (최신 모델 자동 선택)
```bash
python model/predict_crypto_signals.py --market KRW-BTC --candles 50
```

#### 특정 모델 선택
```bash
python model/predict_crypto_signals.py --market KRW-BTC --timestamp 20250821_211833 --candles 30
```

#### 매개변수 설명:
- `--market`: 예측할 암호화폐 마켓 (예: KRW-BTC, KRW-ETH)
- `--timestamp`: 사용할 모델의 타임스탬프 (생략시 최신 모델 사용)
- `--candles`: 예측할 캔들 수 (기본값: 50)

### 3. 예측 결과 해석

```
🎯 현재 권장 행동: 관망
   신뢰도: 17.681
   현재 가격: 158,316,000
```

- **행동**: 매수 / 매도 / 관망
- **신뢰도**: 모델의 예측 신뢰도 (높을수록 확신)
- **현재 가격**: 최신 시점의 암호화폐 가격

---

## 💡 프로그래밍으로 모델 사용

### Python 스크립트에서 모델 로드

```python
from model.crypto_rl_model_loader import CryptoRLModelLoader

# 모델 로드
loader = CryptoRLModelLoader(
    model_path="model/crypto_rl_models/value_network_KRW_BTC_20250821_211833.weights.h5",
    summary_path="model/crypto_rl_models/training_summary_KRW-BTC_20250821_211833.json"
)

# 최근 20개 캔들 예측
predictions = loader.predict_sequence('KRW-BTC', '1m', 20)

# 최신 신호 확인
latest_signal = predictions.iloc[-1]
print(f"권장 행동: {latest_signal['action_name']}")
print(f"신뢰도: {latest_signal['confidence']:.3f}")
```

### 모델 성능 정보 확인

```python
performance = loader.get_model_performance()
print(f"최고 수익률: {performance['max_profit']:.4f}")
print(f"평균 수익률: {performance['avg_profit']:.4f}")
```

---

## 📊 학습 정보 분석

### 학습 요약 파일 구조

```json
{
  "market": "KRW-BTC",
  "interval": "1d",
  "max_portfolio_value": 35981110.33,
  "final_portfolio_value": 5000000.0,
  "final_profitloss": 0.0,
  "num_epochs": 20,
  "epoch_summary": [
    {
      "epoch": 0,
      "epsilon": 0.9,
      "portfolio_value": 35134762.31,
      "profitloss": 6.0270,
      "num_buy": 13,
      "num_sell": 310,
      "num_hold": 676
    }
    // ... 더 많은 에포크 정보
  ]
}
```

### 주요 지표:
- **max_portfolio_value**: 학습 중 달성한 최고 포트폴리오 가치
- **profitloss**: 손익률 (1.0 = 100% 수익)
- **num_buy/sell/hold**: 각 행동의 실행 횟수

---

## ⚙️ 고급 사용법

### 1. 다른 암호화폐로 예측

```bash
# 이더리움 예측
python model/predict_crypto_signals.py --market KRW-ETH --candles 30

# 리플 예측
python model/predict_crypto_signals.py --market KRW-XRP --candles 20
```

### 2. 배치 예측 스크립트

```python
import pandas as pd
from model.crypto_rl_model_loader import list_available_models, CryptoRLModelLoader

# 모든 사용 가능한 모델로 예측
models = list_available_models()
results = []

for model in models:
    loader = CryptoRLModelLoader(model['model_path'], model['summary_path'])
    predictions = loader.predict_sequence(model['market'], '1m', 10)
    
    latest = predictions.iloc[-1]
    results.append({
        'market': model['market'],
        'timestamp': model['timestamp'],
        'action': latest['action_name'],
        'confidence': latest['confidence']
    })

# 결과를 DataFrame으로 정리
df_results = pd.DataFrame(results)
print(df_results)
```

### 3. 실시간 모니터링 스크립트

```python
import time
from datetime import datetime

def monitor_crypto_signals(market='KRW-BTC', interval_seconds=3600):
    """1시간마다 새로운 예측 실행"""
    
    # 최신 모델 로드
    models = list_available_models()
    market_models = [m for m in models if m['market'] == market]
    latest_model = market_models[-1]
    
    loader = CryptoRLModelLoader(latest_model['model_path'], latest_model['summary_path'])
    
    while True:
        try:
            predictions = loader.predict_sequence(market, '1m', 5)
            latest = predictions.iloc[-1]
            
            print(f"[{datetime.now()}] {market}: {latest['action_name']} "
                  f"(신뢰도: {latest['confidence']:.3f})")
            
            time.sleep(interval_seconds)
            
        except Exception as e:
            print(f"모니터링 오류: {e}")
            time.sleep(60)

# 실행
# monitor_crypto_signals('KRW-BTC', 3600)  # 1시간마다
```

---

## 🔧 트러블슈팅

### 1. 모델 로드 실패
```
✗ 모델 로드 실패: ...
```
**해결방법**: 
- 모델 파일 경로가 정확한지 확인
- `.weights.h5` 파일이 손상되지 않았는지 확인

### 2. 예측 결과가 모두 같음
```
관망: 20회 (100.0%)
```
**원인**: 
- 모델이 충분히 학습되지 않음
- 더 많은 에포크로 재학습 필요

### 3. 메모리 부족 오류
**해결방법**:
- `--candles` 수를 줄여서 실행
- 시스템 메모리 확인

---

## 📈 모델 성능 개선

### 1. 더 나은 모델 학습
```bash
# 더 많은 에포크와 큰 밸런스로 학습
python model/train_crypto_rl.py --market KRW-BTC --epochs 1000 --balance 50000000
```

### 2. 다른 신경망 아키텍처 시도
```bash
# LSTM 네트워크로 학습
python model/train_crypto_rl.py --market KRW-BTC --net lstm --epochs 500

# CNN 네트워크로 학습
python model/train_crypto_rl.py --market KRW-BTC --net cnn --epochs 500
```

### 3. 하이퍼파라미터 튜닝
```bash
# 학습률 조정
python model/train_crypto_rl.py --market KRW-BTC --lr 0.001 --epochs 800
```

---

이제 학습된 모델을 완전히 활용할 수 있습니다! 🚀
