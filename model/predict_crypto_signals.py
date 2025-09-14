"""
Crypto RL Prediction Script

저장된 모델을 사용하여 암호화폐 거래 신호를 생성하는 스크립트
"""

import os
import sys
import argparse
from datetime import datetime

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from model.crypto_rl_model_loader import CryptoRLModelLoader, list_available_models


def predict_crypto_signals(market: str = 'KRW-BTC', model_timestamp: str = None, 
                          candles: int = 50):
    """
    저장된 모델을 사용하여 암호화폐 거래 신호 예측
    
    Args:
        market: 예측할 마켓 (예: KRW-BTC)
        model_timestamp: 사용할 모델의 타임스탬프 (None이면 최신 모델)
        candles: 예측할 캔들 수
    """
    
    print(f"=== Crypto 거래 신호 예측 ===")
    print(f"마켓: {market}")
    print(f"캔들 수: {candles}")
    
    # 사용 가능한 모델 확인
    models = list_available_models()
    if not models:
        print("저장된 모델이 없습니다. 먼저 모델을 학습시켜주세요.")
        return
    
    # 모델 선택
    selected_model = None
    if model_timestamp:
        # 특정 타임스탬프 모델 찾기
        for model in models:
            if model['timestamp'] == model_timestamp and model['market'] == market:
                selected_model = model
                break
        
        if not selected_model:
            print(f"타임스탬프 {model_timestamp}인 {market} 모델을 찾을 수 없습니다.")
            return
    else:
        # 해당 마켓의 최신 모델 찾기
        market_models = [m for m in models if m['market'] == market]
        if not market_models:
            print(f"{market} 마켓의 모델이 없습니다.")
            print("사용 가능한 마켓:")
            unique_markets = list(set(m['market'] for m in models))
            for um in unique_markets:
                print(f"  - {um}")
            return
        
        selected_model = market_models[-1]  # 최신 모델
    
    print(f"사용할 모델: {selected_model['market']} - {selected_model['timestamp']}")
    
    try:
        # 모델 로드
        loader = CryptoRLModelLoader(
            selected_model['model_path'],
            selected_model['summary_path']
        )
        
        # 모델 성능 정보
        performance = loader.get_model_performance()
        print(f"\n모델 성능 정보:")
        print(f"  학습 에포크: {performance['total_epochs']}")
        print(f"  최고 수익률: {performance['max_profit']:.4f} ({performance['max_profit']*100:.2f}%)")
        print(f"  평균 수익률: {performance['avg_profit']:.4f} ({performance['avg_profit']*100:.2f}%)")
        print(f"  최종 수익률: {performance['final_profit']:.4f} ({performance['final_profit']*100:.2f}%)")
        
        # 예측 수행
        print(f"\n최근 {candles}개 캔들에 대한 거래 신호 예측 중...")
        predictions = loader.predict_sequence(market, '1m', candles)
        
        if predictions.empty:
            print("예측 결과가 없습니다.")
            return
        
        # 예측 결과 분석
        action_counts = predictions['action_name'].value_counts()
        print(f"\n예측 결과 요약:")
        for action, count in action_counts.items():
            percentage = (count / len(predictions)) * 100
            print(f"  {action}: {count}회 ({percentage:.1f}%)")
        
        # 최근 10개 신호 출력
        print(f"\n최근 10개 거래 신호:")
        recent_predictions = predictions.tail(10)
        
        for _, row in recent_predictions.iterrows():
            datetime_str = str(row['datetime'])
            if len(datetime_str) == 12:  # YYYYMMDDHHMM
                formatted_date = f"{datetime_str[:4]}-{datetime_str[4:6]}-{datetime_str[6:8]} {datetime_str[8:10]}:{datetime_str[10:12]}"
            else:
                formatted_date = str(row['datetime'])
                
            print(f"  {formatted_date}: {row['action_name']} "
                  f"(가격: {row['close_price']:,.0f}, 신뢰도: {row['confidence']:.3f})")
        
        # 현재 권장 행동
        latest_signal = predictions.iloc[-1]
        print(f"\n🎯 현재 권장 행동: {latest_signal['action_name']}")
        print(f"   신뢰도: {latest_signal['confidence']:.3f}")
        print(f"   현재 가격: {latest_signal['close_price']:,.0f}")
        
        # 결과를 파일로 저장 (선택사항)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        module_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_file = os.path.join(module_root, 'model', f"predictions_{market.replace('-', '_')}_{timestamp}.csv")
        predictions.to_csv(output_file, index=False)
        print(f"\n예측 결과가 저장되었습니다: {output_file}")
        
        return predictions
        
    except Exception as e:
        print(f"예측 실패: {e}")
        import traceback
        traceback.print_exc()
        return None


def show_available_models():
    """사용 가능한 모델 목록 출력"""
    models = list_available_models()
    
    if not models:
        print("저장된 모델이 없습니다.")
        return
    
    print("=== 사용 가능한 모델 목록 ===")
    for i, model in enumerate(models, 1):
        print(f"{i}. {model['market']} - {model['timestamp']}")
        print(f"   모델 파일: {os.path.basename(model['model_path'])}")
        print(f"   요약 파일: {os.path.basename(model['summary_path'])}")
        print()


def main():
    parser = argparse.ArgumentParser(description='Crypto RL 모델을 사용한 거래 신호 예측')
    parser.add_argument('--market', default='KRW-BTC', help='예측할 마켓 (예: KRW-BTC)')
    parser.add_argument('--timestamp', help='사용할 모델 타임스탬프 (예: 20250821_211833)')
    parser.add_argument('--candles', type=int, default=50, help='예측할 캔들 수')
    parser.add_argument('--list-models', action='store_true', help='사용 가능한 모델 목록 출력')
    
    args = parser.parse_args()
    
    if args.list_models:
        show_available_models()
        return
    
    # 예측 수행
    predictions = predict_crypto_signals(
        market=args.market,
        model_timestamp=args.timestamp,
        candles=args.candles
    )
    
    if predictions is not None:
        print(f"\n✅ 예측 완료! 총 {len(predictions)}개 신호 생성")
    else:
        print("\n❌ 예측 실패")


if __name__ == "__main__":
    main()
