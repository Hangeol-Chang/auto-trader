async function executeBacktest() {
    const ticker = document.getElementById('ticker').value;
    const startDate = document.getElementById('start_date').value;
    const endDate = document.getElementById('end_date').value;
    const btn = document.getElementById('backtest-btn');
    const resultDiv = document.getElementById('backtest-result');
    
    // 입력값 검증
    if (!ticker || !startDate || !endDate) {
        alert('모든 필드를 입력해주세요.');
        return;
    }
    
    // 버튼 비활성화 및 로딩 표시
    btn.disabled = true;
    btn.textContent = 'Processing...';
    resultDiv.innerHTML = '<p>백테스트 실행 중...</p>';
    
    try {
        const res1 = await fetch('/api/backtest/set_strategy', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ strategy: 'MACD' })  // 기본 전략 설정
        });
        if (!res1.ok) {
            const errorData = await res1.json();
            throw new Error(errorData.error || '전략 설정 중 오류 발생');
        }
        console.log('전략 설정 완료:', res1);

        const res2 = await fetch('/api/backtest/set_data', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                ticker: ticker,
                start_date: startDate,
                end_date: endDate
            })
        });
        if (!res2.ok) {
            const errorData = await res2.json();
            throw new Error(errorData.error || '데이터 설정 중 오류 발생');
        }

        console.log('백테스트 데이터 설정 완료:', ticker, startDate, endDate);
        console.log(res2);

        const response = await fetch('/api/backtest/run', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                ticker: ticker,
                start_date: startDate,
                end_date: endDate
            })
        });

        let data = await response.json();
        data = JSON.parse(data.result);
        
        if (response.ok) {
            if (data && Array.isArray(data) && data.length > 0) {
                // BUY와 SELL 신호만 필터링 (HOLD 제외)
                const tradingSignals = data.filter(item => 
                    item.signal_type.value === 'BUY' || item.signal_type.value === 'SELL'
                );
                
                if (tradingSignals.length > 0) {
                    let tableHtml = `
                        <h3>백테스트 결과 (매매 신호: ${tradingSignals.length}개)</h3>
                        <table border="1" style="width: 100%; border-collapse: collapse;">
                            <tr style="background-color: #333333;">
                                <th>날짜/시간</th>
                                <th>신호</th>
                                <th>종목</th>
                                <th>포지션 크기</th>
                                <th>가격</th>
                            </tr>
                    `;
                    
                    tradingSignals.forEach(item => {
                        const signalColor = item.signal_type.value === 'BUY' ? '#28a745' : '#dc3545';
                        const signalIcon = item.signal_type.value === 'BUY' ? '📈' : '📉';
                        
                        tableHtml += `
                            <tr>
                                <td>${item.target_time}</td>
                                <td style="color: ${signalColor}; font-weight: bold;">
                                    ${signalIcon} ${item.signal_type.value}
                                </td>
                                <td>${item.ticker}</td>
                                <td>${(item.position_size * 100).toFixed(1)}%</td>
                                <td>${item.current_price.toLocaleString()}원</td>
                            </tr>
                        `;
                    });
                    
                    tableHtml += '</table>';
                    
                    // 간단한 통계 추가
                    const buyCount = tradingSignals.filter(item => item.signal_type.value === 'BUY').length;
                    const sellCount = tradingSignals.filter(item => item.signal_type.value === 'SELL').length;
                    
                    tableHtml += `
                        <div style="margin-top: 15px; padding: 10px; background-color: #333333; border-radius: 5px;">
                            <h4>거래 요약</h4>
                            <p>📈 매수 신호: ${buyCount}개 | 📉 매도 신호: ${sellCount}개</p>
                        </div>
                    `;
                    
                    resultDiv.innerHTML = tableHtml;
                } else {
                    resultDiv.innerHTML = '<p>매매 신호가 없습니다. (모든 신호가 HOLD입니다.)</p>';
                }
            } else {
                resultDiv.innerHTML = '<p>백테스트 결과가 없습니다.</p>';
            }
        } else {
            // 오류 결과 표시
            resultDiv.innerHTML = `
                <div style="background: #f8d7da; padding: 15px; border-radius: 5px; color: #721c24;">
                    <h3>오류</h3>
                    <p>${data.error || '알 수 없는 오류가 발생했습니다.'}</p>
                </div>
            `;
        }
        
    } catch (error) {
        resultDiv.innerHTML = `
            <div style="background: #f8d7da; padding: 15px; border-radius: 5px; color: #721c24;">
                <h3>네트워크 오류</h3>
                <p>서버와 연결할 수 없습니다: ${error.message}</p>
            </div>
        `;
    } finally {
        // 버튼 활성화
        btn.disabled = false;
        btn.textContent = 'Backtest Execute';
    }
}