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
# 임포트 끝

class Network:
    lock = threading.Lock()

    def __init__(self, input_dim=0, output_dim=0, lr=0.001,
                 shared_network=None, activation='sigmoid', loss='mse'):
        
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.lr = lr
        self.shared_network = shared_network
        self.activation = activation
        self.loss = loss
        self.model = None

    def predict(self, sample):
        with self.lock:
            pred = self.model.predict_on_batch(sample).flatten()
            return pred

    def train_on_batch(self, x, y):
        loss = 0.
        with self.lock:
            history = self.model.fit(x, y, epochs=1, verbose=False)
            loss += np.sum(history.history['loss'])
        return loss
    
    def save_model(self, model_path):
        with model_path is not None and self.model is not None:
            self.model.save_weights(model_path, overwrite=True)

    def load_model(self, model_path):
        if model_path is not None:
            self.model.load_weights(model_path)