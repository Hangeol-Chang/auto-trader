finviz -> stock screener
investing -> https://kr.investing.com/stock-screener


## 퀀트 투자
### 사용할 요소
- 볼린저 밴드
- squeeze momentum indicator
- dual momentum

### 백테스트와 라이브 실행의 해상도 문제에 대해
- 어쩔 수 없음.
- 라이브 테스트에서는, 백테스트의 결과를 이용해서 기준값들을 정해놓고, 라이브에서 이 기준값들을 이용하는 형태로 활용.

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