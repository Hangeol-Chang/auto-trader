finviz -> stock screener
investing -> https://kr.investing.com/stock-screener


## 퀀트 투자
### 사용할 요소
- 볼린저 밴드
- squeeze momentum indicator
- dual momentum

### 백테스트
- 백테스트에도 사용할 수 있고, 실제 거래에도 사용할 수 있는 좋은 구조는 무엇인가.
- trader -> backtest인지 real인지 구분할 것.
- trader는 여러 개 뜰 수 있는 모델이어야 함.
- trader는 초기화될 때 backtest인지 real 인지 결정됨.

#### backtest인 경우
- 한 번 쓰레드가 돌고 결과를 리턴한 뒤 trader는 꺼짐.

#### real인 경우
- 계속 돌면서 판정 진행.

#### 추가로 필요한 모듈들
- stock_orderer : 살지 팔지 결정하고, 백테스트/실전 유형에 맞게 데이터 저장.
- model : 데이터를 보고 살지 말지 결정하는