"""
Crypto Environment

crypto 데이터를 위한 Environment 클래스
quantylab의 Environment 클래스를 기반으로 crypto 데이터에 특화
"""

class CryptoEnvironment:
    PRICE_IDX = 'close'  # 종가 컬럼명 (crypto 데이터에서는 'close' 사용)
    
    def __init__(self, chart_data=None):
        self.chart_data = chart_data
        self.observation = None
        self.idx = -1

    def reset(self):
        """차트 데이터의 처음으로 돌아가게 함"""
        self.observation = None
        self.idx = -1

    def observe(self):
        """다음 관측치를 반환"""    
        if len(self.chart_data) > self.idx + 1:
            self.idx += 1
            self.observation = self.chart_data.iloc[self.idx]
            return self.observation
        return None

    def get_price(self):
        """현재 가격을 반환"""
        if self.observation is not None:
            return self.observation[self.PRICE_IDX]
        return None
    
    def get_current_step(self):
        """현재 스텝을 반환"""
        return self.idx
    
    def is_done(self):
        """환경이 종료되었는지 확인"""
        return self.idx >= len(self.chart_data) - 1
