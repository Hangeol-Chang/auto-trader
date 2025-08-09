#!/usr/bin/env python3
"""
Pine Script 스타일 전략 테스트
로컬에서 Pine Script와 유사한 전략을 실행하고 테스트하는 예제
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from strategy.pine_style_strategy import ExamplePineStrategy, PineScriptMACD
from module import stock_data_manager

def create_sample_data(days=100):
    """샘플 주가 데이터 생성 (테스트용)"""
    dates = pd.date_range(start='2024-01-01', periods=days, freq='D')
    
    # 랜덤 워크로 주가 데이터 생성
    np.random.seed(42)
    price = 10000
    prices = []
    
    for _ in range(days):
        change = np.random.normal(0, 0.02)  # 평균 0%, 표준편차 2% 변동
        price = price * (1 + change)
        prices.append(price)
    
    # OHLCV 데이터 생성
    data = []
    for i, price in enumerate(prices):
        high = price * (1 + abs(np.random.normal(0, 0.01)))
        low = price * (1 - abs(np.random.normal(0, 0.01)))
        open_price = prices[i-1] if i > 0 else price
        volume = np.random.randint(100000, 1000000)
        
        data.append({
            'Date': dates[i].strftime('%Y%m%d'),
            'Open': open_price,
            'High': high,
            'Low': low,
            'Close': price,
            'Volume': volume
        })
    
    return pd.DataFrame(data)

def test_pine_strategy_with_sample_data():
    """샘플 데이터로 Pine Script 스타일 전략 테스트"""
    print("=== Pine Script 스타일 전략 테스트 (샘플 데이터) ===")
    
    # 샘플 데이터 생성
    data = create_sample_data(100)
    print(f"샘플 데이터 생성 완료: {len(data)}일")
    print(f"가격 범위: {data['Close'].min():.0f} ~ {data['Close'].max():.0f}")
    
    # Pine Script 스타일 전략들 테스트
    strategies = [
        ("RSI + MA 전략", ExamplePineStrategy()),
        ("MACD 전략", PineScriptMACD())
    ]
    
    for strategy_name, strategy in strategies:
        print(f"\n--- {strategy_name} 테스트 ---")
        
        signals = []
        for i in range(50, len(data)):  # 충분한 데이터가 있는 시점부터 시작
            subset_data = data.iloc[:i+1].copy()
            target_time = data.iloc[i]['Date']
            
            signal = strategy.run("TEST", target_time, subset_data)
            
            if signal.signal_type.value != 'HOLD':
                signals.append({
                    'date': target_time,
                    'signal': signal.signal_type.value,
                    'price': signal.current_price,
                    'confidence': signal.confidence
                })
        
        print(f"총 신호 개수: {len(signals)}")
        buy_signals = [s for s in signals if s['signal'] == 'BUY']
        sell_signals = [s for s in signals if s['signal'] == 'SELL']
        print(f"매수 신호: {len(buy_signals)}개")
        print(f"매도 신호: {len(sell_signals)}개")
        
        if signals:
            print("최근 신호 5개:")
            for signal in signals[-5:]:
                print(f"  {signal['date']}: {signal['signal']} @ {signal['price']:.0f} (신뢰도: {signal['confidence']:.2f})")

def test_pine_strategy_with_real_data():
    """실제 주가 데이터로 Pine Script 스타일 전략 테스트"""
    print("\n=== Pine Script 스타일 전략 테스트 (실제 데이터) ===")
    
    ticker = "005930"  # 삼성전자
    start_date = "20240101"
    end_date = "20240630"
    
    try:
        # 실제 주가 데이터 로드
        data = stock_data_manager.load_stock_data_from_db(ticker, start_date, end_date)
        
        if data is None or data.empty:
            print(f"데이터가 없습니다. 데이터를 다운로드합니다...")
            stock_data_manager.download_and_save_stock_data(ticker, start_date, end_date)
            data = stock_data_manager.load_stock_data_from_db(ticker, start_date, end_date)
        
        if data is None or data.empty:
            print("데이터를 가져올 수 없습니다.")
            return
        
        print(f"데이터 로드 완료: {ticker} ({len(data)}일)")
        print(f"기간: {start_date} ~ {end_date}")
        print(f"가격 범위: {data['Close'].min():.0f} ~ {data['Close'].max():.0f}")
        
        # Pine Script 스타일 전략 실행
        strategy = ExamplePineStrategy()
        
        signals = []
        for i in range(50, len(data)):  # 충분한 데이터가 있는 시점부터
            subset_data = data.iloc[:i+1].copy()
            target_time = data.iloc[i]['Date']
            
            signal = strategy.run(ticker, target_time, subset_data)
            
            if signal.signal_type.value != 'HOLD':
                signals.append({
                    'date': target_time,
                    'signal': signal.signal_type.value,
                    'price': signal.current_price,
                    'confidence': signal.confidence
                })
        
        print(f"\n전략 결과:")
        print(f"총 신호 개수: {len(signals)}")
        buy_signals = [s for s in signals if s['signal'] == 'BUY']
        sell_signals = [s for s in signals if s['signal'] == 'SELL']
        print(f"매수 신호: {len(buy_signals)}개")
        print(f"매도 신호: {len(sell_signals)}개")
        
        if signals:
            print("\n최근 신호 10개:")
            for signal in signals[-10:]:
                print(f"  {signal['date']}: {signal['signal']} @ {signal['price']:,}원 (신뢰도: {signal['confidence']:.2f})")
        
    except Exception as e:
        print(f"오류 발생: {e}")

def show_pine_script_comparison():
    """Pine Script와 Python 구현 비교"""
    print("\n=== Pine Script vs Python 구현 비교 ===")
    
    pine_script_example = '''
// Pine Script 원본 (TradingView)
//@version=5
strategy("RSI + MA Strategy", overlay=true)

// 매개변수
rsi_length = input.int(14, title="RSI Length")
rsi_oversold = input.int(30, title="RSI Oversold")
rsi_overbought = input.int(70, title="RSI Overbought")
ma_length = input.int(50, title="MA Length")

// 지표 계산
rsi = ta.rsi(close, rsi_length)
ma = ta.sma(close, ma_length)

// 조건
long_condition = rsi < rsi_oversold and close > ma
short_condition = rsi > rsi_overbought and close < ma

// 전략 실행
if long_condition
    strategy.entry("Long", strategy.long)
if short_condition
    strategy.entry("Short", strategy.short)
'''
    
    python_implementation = '''
# Python 구현 (이 프로젝트)
class ExamplePineStrategy(PineStyleStrategy):
    def __init__(self):
        super().__init__()
        self.rsi_length = 14
        self.rsi_oversold = 30
        self.rsi_overbought = 70
        self.ma_length = 50
    
    def run(self, ticker, target_time, data):
        close = data['Close']
        
        # 지표 계산
        rsi = self.ta_rsi(close, self.rsi_length)
        ma = self.ta_sma(close, self.ma_length)
        
        current_rsi = rsi.iloc[-1]
        current_price = close.iloc[-1]
        current_ma = ma.iloc[-1]
        
        # 조건
        long_condition = (current_rsi < self.rsi_oversold) and (current_price > current_ma)
        short_condition = (current_rsi > self.rsi_overbought) and (current_price < current_ma)
        
        # 신호 생성
        if long_condition:
            return TradingSignal(signal_type=SignalType.BUY, ...)
        elif short_condition:
            return TradingSignal(signal_type=SignalType.SELL, ...)
'''
    
    print("Pine Script 원본:")
    print(pine_script_example)
    print("\nPython 구현:")
    print(python_implementation)
    
    print("\n장점:")
    print("✅ Pine Script와 거의 동일한 로직")
    print("✅ 로컬에서 실행 가능")
    print("✅ 백테스팅 가능")
    print("✅ 실시간 거래 연동 가능")
    print("✅ 더 복잡한 로직 구현 가능")

if __name__ == "__main__":
    print("Pine Script 로컬 실행 테스트")
    print("=" * 50)
    
    # 비교 예제 보기
    show_pine_script_comparison()
    
    # 샘플 데이터로 테스트
    test_pine_strategy_with_sample_data()
    
    # 실제 데이터로 테스트 (선택사항)
    user_input = input("\n실제 주가 데이터로도 테스트하시겠습니까? (y/n): ")
    if user_input.lower() == 'y':
        test_pine_strategy_with_real_data()
    
    print("\n테스트 완료!")
    print("\n사용법:")
    print("1. strategy/pine_style_strategy.py에서 새로운 전략 클래스 생성")
    print("2. Pine Script의 ta.* 함수들을 Python으로 구현")
    print("3. 백테스팅 또는 실시간 거래에 활용")
