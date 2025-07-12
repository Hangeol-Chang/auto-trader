
# class Environment
'''
에이전트가 투자할 종목의 차트 데이터를 관리.

- chart_data: 주식 종목의 차트 데이터
- observation: 현재 관측치
- idx: 차트 데이터에서 현재 위치
'''

class Environment:
    PRICE_IDX = 4 # 종가의 위치
    
    def __init__(self, chart_data = None):
        self.chart_data = chart_data
        self.observation = None
        self.idx = -1

    # 차트 데이터의 처음으로 돌아가게 함.
    def reset(self):
        self.observation = None
        self.idx = -1
    
    def observe(self):
        if len(self.chart_data) > self.idx + 1:
            self.idx += 1
            self.observation = self.chart_data.iloc[self.idx]
            return self.observation
        return None
    
    def get_price(self):
        if self.observation is not None:
            return self.observation[self.PRICE_IDX]
        return None