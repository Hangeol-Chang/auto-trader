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

// 페이지 로드 시 서버 상태 확인
window.addEventListener('load', checkServerStatus);

// 30초마다 서버 상태 업데이트
setInterval(checkServerStatus, 30000);
