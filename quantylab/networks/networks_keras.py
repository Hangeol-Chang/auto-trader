import os
import threading
import numpy as np

'''
    keras backend의 이름은 os.environ에 저장되어있음. 이 값으로 TensorFlow 또는 PlaidML을 선택함.
'''
if os.environ.get('KERAS_BACKEND', 'tensorflow') == 'tensorflow':
    from tensorflow.keras.models import Model
    from tensorflow.keras.layers import Input, Dense, LSTM, Conv1D, \
        BatchNormalization, Dropout, MaxPooling1D, Flatten
    from tensorflow.keras.optimizers import SGD
    from tensorflow.keras import backend
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
elif os.environ['KERAS_BACKEND'] == 'plaidml.keras.backend':
    from keras.models import Model
    from keras.layers import Input, Dense, LSTM, Conv1D, \
        BatchNormalization, Dropout, MaxPooling1D, Flatten
    from keras.optimizers import SGD
