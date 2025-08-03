# Auto Trader

## App Structure
### main.py
- 멀티프로세싱으로 필요한 모듈들을 실행.
    - 플라스크 서버,
    - 트레이더 앱.

### CORE
web, trader 간의 관계
- 백테스트시 trader는 거래를 수행한 뒤, 날짜 토큰 등 key 데이터를 web쪽에 return
- web은 token을 이용해서 백테스트 결과를 불러옴.

- live 테스트시 열심히 쓰레드가 돌면서 live.db에 거래 상황을 저장
- web에 접속 시 검색 기능을 통해 db에서 데이터를 긁어옴.
- web에 띄워지는 데이터는 무조건 db 기반이어야 함. 직접 데이터를 전달하면 안됨.

#### visualizer.py
- 웹을 띄우기 위한 코드

#### trader.py
- 실제 거래 관련된 로직을 처리하는 모듈
- visualizer에서 받은 웹 명령은 대부분 이쪽으로 전달되어 처리됨(백테스트 등)


### DATA
#### state_{YYYYMMDD}.json
- 거래 현황을 추적하기 위한 모듈.

### STRATEGY
- 사용될 전략들을 보관해두는 곳.

### MODULE
- 잡탕.
- core, strategy 이외에 필요한 온갖 기능을 다 가지고 있는 폴더.

#### stock_data_manager.py
- 일봉 등 차트 불러오는 모듈.
- 이미 있는 데이터 검사 등 나름 효율적으로 처리되고 있다고 생각함.

#### column_mapper.py
- api마다 부르는 이름이 달라서 통일을 위해 만든 모듈

#### token_manager.py
- 그냥 KIS app key, token 관리해주는 모듈
- 안전한지는 잘 모르겠음
- 중요해야 하는데 별로 중요하게 관리되고 있지 않음

#### kis_fetcher.py
- 그냥 KIS api 호출해주는 모듈.
- 별로 중요한 모듈 아님. 딱히 건드릴 일 없음.