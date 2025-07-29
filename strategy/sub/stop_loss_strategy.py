from strategy.sub.sub_strategy import Sub_Strategy

class StopLoss_strategy(Sub_Strategy):
    def __init__(self, dataFrame=None):
        self.dataFrame = dataFrame

    def set_data(self, dataFrame):
        self.dataFrame = dataFrame

    def get_data(self):
        if self.dataFrame is None:
            raise ValueError("Data not set")
        return self.dataFrame