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

        let chartData = await res2.json();
        
        // 주가 데이터 파싱 및 초기 차트 그리기 (신호 없이)
        if (chartData.status === 'success' && chartData.result) {
            const stockData = JSON.parse(chartData.result);
            drawStockChart(stockData, ticker);
        }


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
                
                // 차트에 매매 신호 추가
                if (chartData.status === 'success' && chartData.result) {
                    const stockData = JSON.parse(chartData.result);
                    drawStockChart(stockData, ticker, tradingSignals);
                }
                
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

// 주가 차트 그리기 함수
function drawStockChart(stockData, ticker, tradingSignals = []) {
    try {
        
        if (!stockData || !Array.isArray(stockData) || stockData.length === 0) {
            document.getElementById('stock-chart').innerHTML = '<p>차트 데이터가 없습니다.</p>';
            return;
        }

        // 데이터 변환
        const dates = stockData.map(item => item.date);
        const opens = stockData.map(item => item.open);
        const highs = stockData.map(item => item.high);
        const lows = stockData.map(item => item.low);
        const closes = stockData.map(item => item.close);
        const volumes = stockData.map(item => item.volume);

        // MA 데이터 (있는 경우)
        const ma5 = stockData.map(item => item.MA5 || null);
        const ma20 = stockData.map(item => item.MA20 || null);
        const ma60 = stockData.map(item => item.MA60 || null);

        // 캔들스틱 차트 데이터
        const candlestick = {
            x: dates,
            open: opens,
            high: highs,
            low: lows,
            close: closes,
            type: 'candlestick',
            name: ticker,
            increasing: { line: { color: '#ff4444' } },
            decreasing: { line: { color: '#4444ff' } }
        };

        // 이동평균선 데이터
        const traces = [candlestick];

        if (ma5.some(v => v !== null)) {
            traces.push({
                x: dates,
                y: ma5,
                type: 'scatter',
                mode: 'lines',
                name: 'MA5',
                line: { color: '#ffaa00', width: 1 }
            });
        }

        if (ma20.some(v => v !== null)) {
            traces.push({
                x: dates,
                y: ma20,
                type: 'scatter',
                mode: 'lines',
                name: 'MA20',
                line: { color: '#00aa00', width: 2 }
            });
        }

        if (ma60.some(v => v !== null)) {
            traces.push({
                x: dates,
                y: ma60,
                type: 'scatter',
                mode: 'lines',
                name: 'MA60',
                line: { color: '#aa00aa', width: 2 }
            });
        }

        // 매매 신호 추가
        if (tradingSignals && tradingSignals.length > 0) {
            // 매수 신호 (초록색 삼각형)
            const buySignals = tradingSignals.filter(signal => signal.signal_type.value === 'BUY');
            if (buySignals.length > 0) {
                // YYYYMMDD 형태를 YYYY-MM-DD 형태로 변환
                const buyDates = buySignals.map(signal => {
                    const dateStr = signal.target_time;
                    return `${dateStr.slice(0,4)}-${dateStr.slice(4,6)}-${dateStr.slice(6,8)}`;
                });
                const buyPrices = buySignals.map(signal => signal.current_price);
                
                traces.push({
                    x: buyDates,
                    y: buyPrices,
                    type: 'scatter',
                    mode: 'markers',
                    name: '매수 신호',
                    marker: {
                        symbol: 'triangle-up',
                        size: 12,
                        color: '#00ff00',
                        line: { color: '#008800', width: 2 }
                    },
                    hovertemplate: '<b>매수 신호</b><br>' +
                                   '날짜: %{x}<br>' +
                                   '가격: %{y:,.0f}원<br>' +
                                   '<extra></extra>'
                });
            }

            // 매도 신호 (노란색 역삼각형)
            const sellSignals = tradingSignals.filter(signal => signal.signal_type.value === 'SELL');
            if (sellSignals.length > 0) {
                // YYYYMMDD 형태를 YYYY-MM-DD 형태로 변환
                const sellDates = sellSignals.map(signal => {
                    const dateStr = signal.target_time;
                    return `${dateStr.slice(0,4)}-${dateStr.slice(4,6)}-${dateStr.slice(6,8)}`;
                });
                const sellPrices = sellSignals.map(signal => signal.current_price);
                
                traces.push({
                    x: sellDates,
                    y: sellPrices,
                    type: 'scatter',
                    mode: 'markers',
                    name: '매도 신호',
                    marker: {
                        symbol: 'triangle-down',
                        size: 12,
                        color: '#ffff00',
                        line: { color: '#cc8800', width: 2 }
                    },
                    hovertemplate: '<b>매도 신호</b><br>' +
                                   '날짜: %{x}<br>' +
                                   '가격: %{y:,.0f}원<br>' +
                                   '<extra></extra>'
                });
            }
        }

        // 레이아웃 설정
        const layout = {
            title: `${ticker} 주가 차트`,
            xaxis: {
                title: '날짜',
                type: 'date',
                rangeslider: { visible: false }
            },
            yaxis: {
                title: '가격 (원)',
                autorange: true
            },
            plot_bgcolor: '#f8f9fa',
            paper_bgcolor: '#ffffff',
            font: { family: 'Arial, sans-serif' },
            margin: { l: 50, r: 50, t: 50, b: 50 },
            showlegend: true,
            legend: {
                x: 0,
                y: 1,
                bgcolor: 'rgba(255,255,255,0.8)',
                bordercolor: 'rgba(0,0,0,0.2)',
                borderwidth: 1
            }
        };

        // 차트 그리기
        Plotly.newPlot('stock-chart', traces, layout, {
            responsive: true,
            displayModeBar: true,
            modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d']
        });
        
    } catch (error) {
        console.error('Chart drawing error:', error);
        document.getElementById('stock-chart').innerHTML = `<p>차트 그리기 오류: ${error.message}</p>`;
    }
}