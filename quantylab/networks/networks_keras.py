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

# 다른 신경망이 상속받을 기본 Network class
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
        if model_path is not None and self.model is not None:
            self.model.save_weights(model_path, overwrite=True)

    def load_model(self, model_path):
        if model_path is not None:
            self.model.load_weights(model_path)


    # 그냥 네트워크 가져오는 함수
    @classmethod
    def get_shared_network(cls, net='dnn', num_steps=1, input_dim=0, output_dim=0):
        # output_dim은 pytorch에서 필요
        if net == 'dnn':
            return DNN.get_network_head(Input((input_dim,)))
        elif net == 'lstm':
            return LSTMNetwork.get_network_head(Input((num_steps, input_dim)))
        elif net == 'cnn':
            return CNN.get_network_head(Input((num_steps, input_dim)))
        elif net == 'dnn_lstm':
            return DNNLSTMNetwork.get_network_head(Input((num_steps, input_dim)))
    
# DNN 클래스
class DNN(Network):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        inp = None
        output = None
        if self.shared_network is None:
            inp = Input((self.input_dim,))
            output = self.get_network_head(inp).output
        else:
            inp = self.shared_network.input
            output = self.shared_network.output
        output = Dense(
            self.output_dim, activation=self.activation, 
            kernel_initializer='random_normal')(output)
        self.model = Model(inp, output)
        self.model.compile(
            optimizer=SGD(learning_rate=self.lr), loss=self.loss)

    # 실제 계산되는 구조
    '''
        DNN의 구조는 다음과 같음.
        Input -> Dense(256) -> BatchNormalization -> Dropout(0.1) ->
        Dense(128) -> BatchNormalization -> Dropout(0.1) ->
        Dense(64) -> BatchNormalization -> Dropout(0.1) ->
        Dense(32) -> BatchNormalization -> Dropout(0.1) ->
        Dense(output_dim, activation=activation) -> Output
        activation은 기본적으로 sigmoid로 설정되어 있음.
        loss는 기본적으로 mse로 설정되어 있음.
        lr은 기본적으로 0.001로 설정되어 있음.
        shared_network가 None이면 위의 구조를 사용하고,
        shared_network가 있다면 shared_network의 input과 output을 사용함.
        shared_network는 다른 네트워크와 공유하는 부분으로,
        예를 들어 LSTMNetwork나 CNN에서 사용될 수 있음.

        최적화 알고리즘은 SGD로 설정되어 있음. (확률적 경사 하강법)
    '''
    @staticmethod
    def get_network_head(inp):
        output = Dense(256, activation='sigmoid', 
            kernel_initializer='random_normal')(inp)
        output = BatchNormalization()(output)
        output = Dropout(0.1)(output)
        output = Dense(128, activation='sigmoid', 
            kernel_initializer='random_normal')(output)
        output = BatchNormalization()(output)
        output = Dropout(0.1)(output)
        output = Dense(64, activation='sigmoid', 
            kernel_initializer='random_normal')(output)
        output = BatchNormalization()(output)
        output = Dropout(0.1)(output)
        output = Dense(32, activation='sigmoid', 
            kernel_initializer='random_normal')(output)
        output = BatchNormalization()(output)
        output = Dropout(0.1)(output)
        return Model(inp, output)

    # 배치 학습 함수
    def train_on_batch(self, x, y):
        x = np.array(x).reshape((-1, self.input_dim))
        return super().train_on_batch(x, y)

    # 예측 함수
    def predict(self, sample):
        sample = np.array(sample).reshape((1, self.input_dim))
        return super().predict(sample)
    
 
# LSTM 클래스
'''
    DNN과 전체적으로 유사하지만 num_steps 변수를 가지고 있음.
    몇 개의 샘플을 묶어서 LSTM 신경망의 입력으로 사용할지 결정하는 것.
'''
class LSTMNetwork(Network):
    def __init__(self, *args, num_steps=1, **kwargs):
        super().__init__(*args, **kwargs)
        self.num_steps = num_steps
        inp = None
        output = None
        if self.shared_network is None:
            inp = Input((self.num_steps, self.input_dim))
            output = self.get_network_head(inp).output
        else:
            inp = self.shared_network.input
            output = self.shared_network.output
        output = Dense(
            self.output_dim, activation=self.activation, 
            kernel_initializer='random_normal')(output)
        self.model = Model(inp, output)
        self.model.compile(
            optimizer=SGD(learning_rate=self.lr), loss=self.loss)

    @staticmethod
    def get_network_head(inp):
        '''
            return_sequences=True는 LSTM이 시퀀스의 모든 타임스텝에 대해 출력을 반환하도록 함. -> num_steps를 유지하기 위함
        '''
        # cuDNN 사용을 위한 조건
        # https://www.tensorflow.org/api_docs/python/tf/keras/layers/LSTM
        output = LSTM(256, dropout=0.1, return_sequences=True,
                    kernel_initializer='random_normal')(inp)
        output = BatchNormalization()(output)
        output = LSTM(128, dropout=0.1, return_sequences=True,
                    kernel_initializer='random_normal')(output)
        output = BatchNormalization()(output)
        output = LSTM(64, dropout=0.1, return_sequences=True,
                    kernel_initializer='random_normal')(output)
        output = BatchNormalization()(output)
        output = LSTM(32, dropout=0.1, kernel_initializer='random_normal')(output)
        output = BatchNormalization()(output)
        return Model(inp, output)

    def train_on_batch(self, x, y):
        x = np.array(x).reshape((-1, self.num_steps, self.input_dim))
        return super().train_on_batch(x, y)

    def predict(self, sample):
        sample = np.array(sample).reshape((1, self.num_steps, self.input_dim))
        return super().predict(sample)


# CNN 클래스
'''
    LTSM과 마찬가지로 다차원 데이터를 다룰 수 있음.
    2차원 데이터를 다루기 위해 Conv1D 클래스 사용
'''
class CNN(Network):
    def __init__(self, *args, num_steps=1, **kwargs):
        super().__init__(*args, **kwargs)
        self.num_steps = num_steps
        inp = None
        output = None
        if self.shared_network is None:
            inp = Input((self.num_steps, self.input_dim, 1))
            output = self.get_network_head(inp).output
        else:
            inp = self.shared_network.input
            output = self.shared_network.output
        output = Dense(
            self.output_dim, activation=self.activation,
            kernel_initializer='random_normal')(output)
        self.model = Model(inp, output)
        self.model.compile(
            optimizer=SGD(learning_rate=self.lr), loss=self.loss)

    @staticmethod
    def get_network_head(inp):
        '''
            padding -> 입출력 크기를 똑같이 맞추기 위해 same으로 설정
        '''
        output = Conv1D(256, kernel_size=5,
            padding='same', activation='sigmoid',
            kernel_initializer='random_normal')(inp)
        output = BatchNormalization()(output)
        output = MaxPooling1D(pool_size=2, padding='same')(output)
        output = Dropout(0.1)(output)
        output = Conv1D(64, kernel_size=5,
            padding='same', activation='sigmoid',
            kernel_initializer='random_normal')(output)
        output = BatchNormalization()(output)
        output = MaxPooling1D(pool_size=2, padding='same')(output)
        output = Dropout(0.1)(output)
        output = Conv1D(32, kernel_size=5,
            padding='same', activation='sigmoid',
            kernel_initializer='random_normal')(output)
        output = BatchNormalization()(output)
        output = MaxPooling1D(pool_size=2, padding='same')(output)
        output = Dropout(0.1)(output)
        output = Flatten()(output)
        return Model(inp, output)

    def train_on_batch(self, x, y):
        x = np.array(x).reshape((-1, self.num_steps, self.input_dim, 1))
        return super().train_on_batch(x, y)

    def predict(self, sample):
        sample = np.array(sample).reshape(
            (-1, self.num_steps, self.input_dim, 1))
        return super().predict(sample)


# DNN+LSTM 하이브리드 클래스
class DNNLSTMNetwork(Network):
    """DNN과 LSTM을 결합한 하이브리드 신경망"""
    def __init__(self, *args, num_steps=1, **kwargs):
        super().__init__(*args, **kwargs)
        self.num_steps = num_steps
        inp = None
        output = None
        if self.shared_network is None:
            inp = Input((self.num_steps, self.input_dim))
            output = self.get_network_head(inp).output
        else:
            inp = self.shared_network.input
            output = self.shared_network.output
        output = Dense(
            self.output_dim, activation=self.activation, 
            kernel_initializer='random_normal')(output)
        self.model = Model(inp, output)
        self.model.compile(
            optimizer=SGD(learning_rate=self.lr), loss=self.loss)

    @staticmethod
    def get_network_head(inp):
        """
        DNN+LSTM 하이브리드 구조:
        Input -> DNN(256, 128) -> LSTM(64, 32) -> Output
        
        DNN 부분으로 특성을 추출한 후, 
        LSTM으로 시계열 패턴을 학습하는 구조
        """
        # 첫 번째 DNN 레이어들 (특성 추출)
        output = Dense(256, activation='sigmoid', 
            kernel_initializer='random_normal')(inp)
        output = BatchNormalization()(output)
        output = Dropout(0.1)(output)
        
        output = Dense(128, activation='sigmoid', 
            kernel_initializer='random_normal')(output)
        output = BatchNormalization()(output)
        output = Dropout(0.1)(output)
        
        # LSTM 레이어들 (시계열 패턴 학습)
        output = LSTM(64, return_sequences=True, 
            kernel_initializer='random_normal')(output)
        output = BatchNormalization()(output)
        output = Dropout(0.1)(output)
        
        output = LSTM(32, return_sequences=False, 
            kernel_initializer='random_normal')(output)
        output = BatchNormalization()(output)
        output = Dropout(0.1)(output)
        
        return Model(inp, output)

    def train_on_batch(self, x, y):
        x = np.array(x).reshape((-1, self.num_steps, self.input_dim))
        return super().train_on_batch(x, y)

    def predict(self, sample):
        # 입력 샘플의 차원에 따라 적절히 reshape
        sample = np.array(sample)
        
        if len(sample.shape) == 1:
            # 1D 샘플인 경우: (features,) -> (1, num_steps, features)
            # 같은 샘플을 num_steps만큼 반복하여 시계열 만들기
            sample = np.tile(sample, (self.num_steps, 1))
            sample = sample.reshape((1, self.num_steps, self.input_dim))
        elif len(sample.shape) == 2:
            if sample.shape[0] == self.num_steps:
                # 이미 시계열 형태인 경우: (num_steps, features) -> (1, num_steps, features)
                sample = sample.reshape((1, self.num_steps, self.input_dim))
            else:
                # 배치 형태인 경우: (batch, features) -> (batch, num_steps, features)
                batch_size = sample.shape[0]
                sample = np.tile(sample[:, np.newaxis, :], (1, self.num_steps, 1))
        elif len(sample.shape) == 3:
            # 이미 올바른 형태: (batch, num_steps, features)
            pass
        else:
            raise ValueError(f"Unsupported sample shape: {sample.shape}")
            
        return super().predict(sample)
