// 서버 상태 확인
async function checkServerStatus() {
    try {
        const response = await fetch('/health');
        const data = await response.json();
        
        if (data.status === 'up') {
            document.getElementById('server-status').textContent = '온라인';
            document.getElementById('server-version').textContent = data.version;
        } else {
            document.getElementById('server-status').textContent = '오프라인';
            document.querySelector('.status-indicator').className = 'status-indicator status-offline';
        }
    } catch (error) {
        console.error('서버 상태 확인 실패:', error);
        document.getElementById('server-status').textContent = '연결 실패';
        document.querySelector('.status-indicator').className = 'status-indicator status-offline';
    }
}

// API 테스트 함수들
async function testDiscordAPI() {
    try {
        const response = await fetch('/api/discord/health');
        const data = await response.json();
        alert(`Discord API 상태: ${data.status}\n서비스: ${data.service}\n버전: ${data.version}`);
    } catch (error) {
        alert('Discord API 테스트 실패: ' + error.message);
    }
}

async function testTradingViewAPI() {
    try {
        const response = await fetch('/api/tradingview/health');
        const data = await response.json();
        alert(`TradingView API 상태: ${data.status}\n서비스: ${data.service}\n버전: ${data.version}`);
    } catch (error) {
        alert('TradingView API 테스트 실패: ' + error.message);
    }
}

async function testTradingAPI() {
    try {
        const response = await fetch('/api/trading/health');
        const data = await response.json();
        alert(`Trading API 상태: ${data.status}\n서비스: ${data.service}\n버전: ${data.version}`);
    } catch (error) {
        alert('Trading API 테스트 실패: ' + error.message);
    }
}

async function testStockAPI() {
    try {
        // 주식 API 상태 확인 (삼성전자 현재가 조회)
        const response = await fetch('/api/trading/stock-price/005930');
        if (response.ok) {
            const data = await response.json();
            alert(`Stock API 연결 성공!\n삼성전자 현재가: ${data.price}원\n변동률: ${data.change_rate}%`);
        } else {
            alert('Stock API 테스트 실패: 응답 코드 ' + response.status);
        }
    } catch (error) {
        alert('Stock API 테스트 실패: ' + error.message);
    }
}

// 페이지 로드 시 서버 상태 확인
window.addEventListener('load', function() {
    checkServerStatus();
    
    // 추가 초기화 작업
    console.log('Auto Trading Server Dashboard 로드 완료');
    console.log('API 엔드포인트:');
    console.log('- Discord: /api/discord/*');
    console.log('- TradingView: /api/tradingview/*');
    console.log('- Trading: /api/trading/*');
    console.log('- Stock Trading: /api/trading/stock-*');
});

// 30초마다 서버 상태 업데이트
setInterval(checkServerStatus, 30000);

// 빠른 테스트를 위한 추가 함수들
async function quickBalanceCheck() {
    try {
        const [cryptoResponse, stockResponse] = await Promise.all([
            fetch('/api/trading/balance'),
            fetch('/api/trading/stock-balance')
        ]);
        
        const cryptoData = cryptoResponse.ok ? await cryptoResponse.json() : null;
        const stockData = stockResponse.ok ? await stockResponse.json() : null;
        
        let message = '💰 계정 잔고 요약\n\n';
        
        if (cryptoData) {
            message += '📈 암호화폐:\n';
            if (cryptoData.balances && cryptoData.balances.length > 0) {
                cryptoData.balances.slice(0, 3).forEach(balance => {
                    message += `  ${balance.currency}: ${balance.balance}\n`;
                });
            } else {
                message += '  데이터 없음\n';
            }
        }
        
        if (stockData) {
            message += '\n🏢 주식:\n';
            if (stockData.stocks && stockData.stocks.length > 0) {
                stockData.stocks.slice(0, 3).forEach(stock => {
                    message += `  ${stock.name}: ${stock.quantity}주\n`;
                });
            } else {
                message += '  보유 주식 없음\n';
            }
        }
        
        alert(message);
    } catch (error) {
        alert('잔고 조회 실패: ' + error.message);
    }
}

// 키보드 단축키 지원
document.addEventListener('keydown', function(event) {
    // Ctrl + Shift + T: 전체 API 테스트
    if (event.ctrlKey && event.shiftKey && event.key === 'T') {
        event.preventDefault();
        Promise.all([
            testDiscordAPI(),
            testTradingViewAPI(), 
            testTradingAPI(),
            testStockAPI()
        ]);
    }
    
    // Ctrl + Shift + B: 빠른 잔고 확인
    if (event.ctrlKey && event.shiftKey && event.key === 'B') {
        event.preventDefault();
        quickBalanceCheck();
    }
});
