"""
웹 인터페이스를 위한 Flask 서버 모듈
"""

from flask import Flask, render_template, jsonify, request
import os
import json
import logging
from datetime import datetime

from module import stock_data_manager

# Flask 앱 초기화
app = Flask(__name__, 
            template_folder='../web',
            static_folder='../web/static')

# 개발 환경 설정
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

logger = logging.getLogger(__name__)

@app.route('/')
def index():
    """메인 페이지"""
    return render_template('index.html')

@app.route('/api/stock/data')
def get_stock_data():
    """주식 데이터 API"""
    try:
        stock_code = request.args.get('stock_code', '005930')
        start_date = request.args.get('start_date', '20240101')
        end_date = request.args.get('end_date', '20241231')
        
        # 주식 데이터 가져오기
        data = stock_data_manager.get_processed_data_D(
            itm_no=stock_code,
            start_date=start_date,
            end_date=end_date
        )
        
        if data.empty:
            return jsonify({'error': '데이터를 찾을 수 없습니다.'}), 404
        
        # DataFrame을 JSON으로 변환
        result = {
            'stock_code': stock_code,
            'data_count': len(data),
            'data': data.to_dict('records'),
            'columns': data.columns.tolist()
        }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Stock data API error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/stock/tickers')
def get_tickers():
    """전체 티커 목록 API"""
    try:
        tickers = stock_data_manager.get_full_ticker(include_screening_data=False)
        
        if tickers.empty:
            return jsonify({'error': '티커 데이터를 찾을 수 없습니다.'}), 404
        
        # 상위 100개만 반환 (성능상 이유)
        result = {
            'total_count': len(tickers),
            'data': tickers.head(100).to_dict('records')
        }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Tickers API error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/system/status')
def get_system_status():
    """시스템 상태 API"""
    try:
        status = {
            'timestamp': datetime.now().isoformat(),
            'status': 'running',
            'data_directory': os.path.abspath('data'),
            'web_directory': os.path.abspath('web')
        }
        
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"System status API error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/backtest', methods=['POST'])
def run_backtest():
    """백테스트 실행 API"""
    print("Received backtest request")

    try:
        # JSON 데이터 받기
        data = request.get_json()
        print(f"Backtest data: {data}")
        ticker = data.get('ticker', '005930')
        start_date = data.get('start_date', '20240101')
        end_date = data.get('end_date', '20241231')
        
        logger.info(f"Starting backtest for {ticker} from {start_date} to {end_date}")
        
        # 실제 백테스트 로직 (여기서는 간단한 예시)
        stock_data = stock_data_manager.get_processed_data_D(
            itm_no=ticker,
            start_date=start_date,
            end_date=end_date
        )
        
        if stock_data.empty:
            return jsonify({'error': f'데이터를 찾을 수 없습니다: {ticker}'}), 404
        
        # 간단한 백테스트 결과 생성
        result = {
            'ticker': ticker,
            'start_date': start_date,
            'end_date': end_date,
            'total_days': len(stock_data),
            'start_price': float(stock_data.iloc[0]['close']) if len(stock_data) > 0 else 0,
            'end_price': float(stock_data.iloc[-1]['close']) if len(stock_data) > 0 else 0,
            'return_rate': 0,
            'max_drawdown': 0,
            'win_rate': 0,
            'status': 'completed'
        }
        
        # 수익률 계산
        if result['start_price'] > 0:
            result['return_rate'] = ((result['end_price'] - result['start_price']) / result['start_price']) * 100
        
        logger.info(f"Backtest completed: {result['return_rate']:.2f}% return")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Backtest API error: {e}")
        return jsonify({'error': str(e)}), 500

def run_server():
    """Flask 서버 실행"""
    try:
        # 웹 디렉토리가 없으면 생성
        web_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'web')
        if not os.path.exists(web_dir):
            os.makedirs(web_dir)
            
        logger.info("Starting Flask server...")
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
        
    except Exception as e:
        logger.error(f"Failed to start Flask server: {e}")
        raise