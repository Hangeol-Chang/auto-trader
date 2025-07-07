

## 1.3 금융 데이터 분석
### 1.3.2 기술적 분석
#### OHLC open-high-low-close)
- 주식의 양봉 음봉. 맨날 보는 그거

#### 보조지표
##### 이동평균선(MA, moving average)
- 윈도우 동안 평균 주가의 시계열
- MA(t) = (sigma(x(t - w + i))) / w
    - w : 윈도우
    - x(t) : 차트상의 t번쨰 주가

##### 지수이동평균선(EMA, exponential moving average)
- 최근 가격에 가중치를 둔 이동평균선

##### 볼린저밴드(Bolinger band)
- 주가의 이동평군선을 중심으로 표준편차의 범위를 표시.
- S(t) = sqrt((sigma(x(t-w+i) - MA(t))) / (w - 1))
- UBB : 상한선
- LBB : 하한선

##### *이동평균 수렴 확산(MACD, moving average convergence divergence)
- 2개의 장단기 지수이동평균선으로 모멘텀을 추정하는 보조지표.
- EMA12를 단기선으로, EMA26을 장기선으로 사용
- MACD(t) = EMAs(t) - EMAl(t)
- MACD_signal(t) = EMAn(t) where x(t) = MACD(t)
- MCAD선이 시그널 선을 상향 돌파하면 매수, 하향 돌파하면 매도 사인으로 생각.

##### 상대강도지수 (relative strength index, RSI)
- 과매수, 침체 국면을 판단하는 보조지표
- RSI 70 이상이면 과열, 30 이하면 침체 구간으로 봄

#### 차트 패턴
- Three Line Strike
- Two Black Gapping
- Three Black Cows
- Evening Star
- Abandoned Baby


### 1.3.3 정서 분석
- 투자자들의 정서를 판단하기 위한 분석 방법


## 1.4 전통적인 퀀트 투자