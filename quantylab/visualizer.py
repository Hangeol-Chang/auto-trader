import threading
import numpy as np
import matplotlib.pyplot as plt
plt.switch_backend('agg')  # Use non-interactive backend for saving figures


from mplfinace.original_flavor import candlestick_ohlc
from quantylab.agent import Agent

lock = threading.Lock()

class Visualizer:
    COLORS = ['r' 'b' 'g']