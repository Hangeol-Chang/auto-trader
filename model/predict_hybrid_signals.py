"""
DNN+LSTM 하이브리드 모델 예측 스크립트

하이브리드 신경망으로 학습된 모델을 사용하여 암호화폐 거래 신호 예측
"""

import os
import sys
import argparse
import json
import numpy as np
import pandas as pd
from datetime import datetime

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from model.crypto_rl_learner import CryptoReinforcementLearner
from module.crypto.crypto_data_manager import get_candle_data


def predict_with_hybrid_model(market='KRW-BTC', timestamp=None, candles=20, num_steps=5):
    """
    DNN+LSTM 하이브리드 모델로 거래 신호 예측
    
    Args:
        market (str): 암호화폐 마켓
        timestamp (str): 모델 타임스탬프 (예: 20250821_215117)
        candles (int): 예측할 캔들 수
        num_steps (int): LSTM 시계열 스텝 수
    """
    
    print("🧠 DNN+LSTM 하이브리드 모델 예측 시작")
    print(f"📊 마켓: {market}")
    print(f"⏱️  시계열 스텝: {num_steps}")
    print(f"🕯️  예측 캔들: {candles}")
    
    # 모델 파일 경로 구성
    model_dir = "model/crypto_rl_models"
    if timestamp:
        model_filename = f"value_network_{market.replace('-', '_')}_{timestamp}.weights.h5"
        summary_filename = f"training_summary_{market}_{timestamp}.json"
    else:
        # 최신 모델 찾기
        import glob
        model_files = glob.glob(os.path.join(model_dir, f"value_network_{market.replace('-', '_')}_*.weights.h5"))
        if not model_files:
            print(f"❌ {market} 모델을 찾을 수 없습니다.")
            return None
        
        model_filename = os.path.basename(sorted(model_files)[-1])
        timestamp = model_filename.split('_')[-1].replace('.weights.h5', '')
        summary_filename = f"training_summary_{market}_{timestamp}.json"
    
    model_path = os.path.join(model_dir, model_filename)
    summary_path = os.path.join(model_dir, summary_filename)
    
    if not os.path.exists(model_path):
        print(f"❌ 모델 파일을 찾을 수 없습니다: {model_path}")
        return None
    
    if not os.path.exists(summary_path):
        print(f"❌ 요약 파일을 찾을 수 없습니다: {summary_path}")
        return None
    
    # 요약 정보 로드
    with open(summary_path, 'r') as f:
        summary = json.load(f)
    
    print(f"📈 모델 정보:")
    print(f"   타임스탬프: {timestamp}")
    print(f"   최고 수익률: {(summary['max_portfolio_value']/1000000-1)*100:.2f}%")
    print(f"   최종 손익률: {summary['final_profitloss']:.4f}")
    print(f"   학습 에포크: {summary['num_epochs']}")
    
    try:
        # 하이브리드 학습기 초기화 (모델 로드용)
        learner = CryptoReinforcementLearner(
            market=market,
            interval='1m',
            net='dnn_lstm',  # 하이브리드 네트워크
            num_steps=num_steps,
            lr=0.0003,
            balance=1000000,
            reuse_models=False
        )
        
        # 데이터 로드
        learner.load_data()
        
        # 신경망 초기화
        learner.init_value_network()
        
        # 모델 가중치 로드
        learner.value_network.load_model(model_path)
        print("✅ 하이브리드 모델 로드 완료")
        
        # 최근 데이터로 예측
        predictions = []
        chart_data = learner.chart_data.tail(candles).copy()
        training_data = learner.training_data.tail(candles).copy()
        
        # 가격 정보를 위한 차트 데이터 인덱스 맞추기
        chart_data.reset_index(drop=True, inplace=True)
        training_data.reset_index(drop=True, inplace=True)
        
        print(f"\n🔮 {candles}개 캔들 예측 중...")
        
        for i in range(len(training_data)):
            # 현재 시점의 기술적 지표
            features = training_data.iloc[i].values
            
            # 에이전트 상태 (임시로 기본값 사용)
            agent_status = [0.0, 0.0, 0.0]  # [주식보유비율, 손익, 평균매수가대비등락률]
            
            # 전체 샘플 구성
            sample = np.concatenate([features, agent_status])
            
            # 하이브리드 네트워크 예측
            pred_value = learner.value_network.predict(sample)
            
            # 행동 결정 (가장 높은 가치를 가진 행동 선택)
            action = np.argmax(pred_value)
            confidence = pred_value[action]
            
            # 행동 이름 매핑
            action_names = ['매수', '매도', '관망']
            action_name = action_names[action]
            
            # 현재 가격 정보
            current_price = chart_data.iloc[i]['close']
            current_time = chart_data.iloc[i].get('candle_date_time_utc', f"Index_{i}")
            
            predictions.append({
                'index': i,
                'timestamp': current_time,
                'price': current_price,
                'action': action,
                'action_name': action_name,
                'confidence': float(confidence),
                'pred_values': pred_value.tolist()
            })
        
        # 결과 출력
        print("\n📊 예측 결과:")
        print("=" * 80)
        
        # 최신 신호
        latest = predictions[-1]
        print(f"\n🎯 현재 권장 행동: {latest['action_name']}")
        print(f"   신뢰도: {latest['confidence']:.3f}")
        print(f"   현재 가격: {latest['price']:,.0f}")
        
        # 행동 분포
        action_counts = pd.Series([p['action_name'] for p in predictions]).value_counts()
        print(f"\n📈 {candles}개 캔들 행동 분포:")
        for action, count in action_counts.items():
            percentage = count / len(predictions) * 100
            print(f"   {action}: {count}회 ({percentage:.1f}%)")
        
        # 신뢰도 통계
        confidences = [p['confidence'] for p in predictions]
        print(f"\n📊 신뢰도 통계:")
        print(f"   평균: {np.mean(confidences):.3f}")
        print(f"   최대: {np.max(confidences):.3f}")
        print(f"   최소: {np.min(confidences):.3f}")
        
        # CSV 파일로 저장
        df_predictions = pd.DataFrame(predictions)
        output_file = f"hybrid_predictions_{market}_{timestamp}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df_predictions.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n💾 예측 결과 저장: {output_file}")
        
        return predictions
        
    except Exception as e:
        print(f"❌ 예측 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    parser = argparse.ArgumentParser(description='DNN+LSTM 하이브리드 모델 암호화폐 거래 신호 예측')
    
    parser.add_argument('--market', type=str, default='KRW-BTC',
                        help='암호화폐 마켓 (기본값: KRW-BTC)')
    
    parser.add_argument('--timestamp', type=str, default=None,
                        help='모델 타임스탬프 (생략시 최신 모델 사용)')
    
    parser.add_argument('--candles', type=int, default=20,
                        help='예측할 캔들 수 (기본값: 20)')
    
    parser.add_argument('--num-steps', type=int, default=5,
                        help='LSTM 시계열 스텝 수 (기본값: 5)')
    
    args = parser.parse_args()
    
    # 하이브리드 모델 예측 실행
    predictions = predict_with_hybrid_model(
        market=args.market,
        timestamp=args.timestamp,
        candles=args.candles,
        num_steps=args.num_steps
    )
    
    if predictions:
        print("\n🎉 하이브리드 모델 예측이 성공적으로 완료되었습니다!")
    else:
        print("\n❌ 하이브리드 모델 예측이 실패했습니다.")


if __name__ == "__main__":
    main()
