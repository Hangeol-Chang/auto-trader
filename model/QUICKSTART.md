# 🚀 빠른 시작 가이드 - DNN+LSTM 하이브리드 암호화폐 거래 AI

## ⚡ 30초 만에 시작하기

### 1. 모델 학습 (5-10분 소요)
```bash
python model/train_crypto_rl_hybrid.py --market KRW-BTC --epochs 50
```

### 2. 거래 신호 예측 (10초 소요)
```bash
python model/predict_hybrid_signals.py --market KRW-BTC --candles 10
```

### 3. 결과 확인
```
🎯 현재 권장 행동: 매수
   신뢰도: 45.2
   현재 가격: 158,316,000
```

---

## 📊 핵심 데이터 형태

### 입력 (15개 특성)
```python
# 기술적 지표 (12개)
['ma5', 'ma20', 'ma60', 'rsi', 'macd', 'macd_signal', 'macd_hist', 
 'bb_ratio', 'volume_ratio', 'price_change', 'price_change_5', 'price_change_20']

# 에이전트 상태 (3개)  
[보유비율, 손익률, 등락률]

# 시계열 형태 (LSTM용)
shape: (시간스텝, 15개특성) = (5, 15)
```

### 출력 (3개 행동)
```python
[매수가치, 매도가치, 관망가치] → 최고값 선택 → 거래신호
```

---

## 🎯 주요 명령어

| 목적 | 명령어 |
|------|--------|
| **기본 학습** | `python model/train_crypto_rl_hybrid.py --market KRW-BTC` |
| **고성능 학습** | `python model/train_crypto_rl_hybrid.py --market KRW-BTC --epochs 200 --balance 20000000` |
| **빠른 예측** | `python model/predict_hybrid_signals.py --market KRW-BTC` |
| **정밀 예측** | `python model/predict_hybrid_signals.py --market KRW-BTC --candles 30 --num-steps 10` |
| **이더리움** | `--market KRW-ETH` |
| **리플** | `--market KRW-XRP` |

---

## 📈 성능 벤치마크

| 모델 | 최고 수익률 | 학습 시간 | 메모리 사용량 |
|------|-------------|-----------|---------------|
| DNN | 619% | 2분 | 2GB |
| **DNN+LSTM** | **5,242%** | 18분 | 4GB |

---

## ❌ 자주 발생하는 문제

### 문제: `ModuleNotFoundError`
```bash
pip install tensorflow numpy pandas tqdm
```

### 문제: `메모리 부족`
```bash
python model/train_crypto_rl_hybrid.py --market KRW-BTC --epochs 20 --num-steps 3
```

### 문제: `모델 파일 없음`
```bash
ls model/crypto_rl_models/  # 파일 확인
python model/train_crypto_rl_hybrid.py --market KRW-BTC --epochs 10  # 재학습
```

---

## 🔗 상세 가이드

전체 문서: [`README_HYBRID_MODEL.md`](./README_HYBRID_MODEL.md)

---

**🎉 Happy Trading!** 🚀
