'''
    웹소켓 기반의 실시간성이 보장되는 API들
    stock_data_manager와 공통부분은 병합될 가능성 있음. 매우 높음.
'''

from unittest import result
import pandas as pd
import os
from datetime import datetime, timedelta
from pykrx import stock
import yfinance as yf
import time
import re
