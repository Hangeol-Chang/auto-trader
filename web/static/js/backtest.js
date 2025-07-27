async function executeBacktest() {
    const ticker = document.getElementById('ticker').value;
    const startDate = document.getElementById('start_date').value;
    const endDate = document.getElementById('end_date').value;
    const strategy = document.getElementById('strategy').value; // 선택된 전략
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
            body: JSON.stringify({ strategy: strategy })  // 기본 전략 설정
        });
        if (!res1.ok) {
            const errorData = await res1.json();
            throw new Error(errorData.error || '전략 설정 중 오류 발생');
        }
        // console.log('전략 설정 완료:', res1);

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
            console.log('차트 데이터:', stockData);
            drawStockChart(stockData, ticker);
        }

        const response = await fetch('/api/backtest/run', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                strategy: strategy,
                ticker: ticker,
                start_date: startDate,
                end_date: endDate
            })
        });

        let data = await response.json();
        data = data.result;
        // console.log(data)
        // data = JSON.parse(data.result);
        
        console.log('backtest trading result:', data);

        const balance = data.balance;
        const portfolioValue = data.portfolioValue;
        const trade_history = data.trade_history;

        if (response.ok) {
            if (trade_history && Array.isArray(trade_history) && trade_history.length > 0) {
                
                // BUY와 SELL 신호만 필터링 (HOLD 제외)
                const tradingSignals = trade_history.filter(item => 
                    item.signal_type === 'BUY' || item.signal_type === 'SELL'
                );
                
                // 차트에 매매 신호 추가
                if (tradingSignals.length > 0) {
                    updateStockChart(tradingSignals);
                }
                
                // 백테스트 결과 테이블 생성
                displayBacktestResults(tradingSignals, {
                    "balance": balance,
                    "portfolioValue": portfolioValue
                });
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

// 백테스트 결과 테이블 생성 함수
function displayBacktestResults(tradingSignals, { balance, portfolioValue }) {
    const resultDiv = document.getElementById('backtest-result');
    
    if (!tradingSignals || tradingSignals.length === 0) {
        resultDiv.innerHTML = '<p>매매 신호가 없습니다. (모든 신호가 HOLD입니다.)</p>';
        return;
    }

    // 통계 계산
    const buyCount = tradingSignals.filter(item => item.signal_type === 'BUY').length;
    const sellCount = tradingSignals.filter(item => item.signal_type === 'SELL').length;
    
    // 헤더와 통계 부분
    let htmlContent = `
        <div style="margin-bottom: 15px;">
            <h3>백테스트 결과 (매매 신호: ${tradingSignals.length}개)</h3>
            <div style="padding: 10px; background-color: #333333; border-radius: 5px; margin-bottom: 15px;">
                <h4 style="margin: 0 0 10px 0;">거래 요약</h4>
                <p style="margin: 0;">📈 매수 신호: ${buyCount}개 | 📉 매도 신호: ${sellCount}개</p>
                <br>
                <p style="margin: 0;">💰 최종 잔액: ${balance.toLocaleString()}원</p>
                <p style="margin: 0;">📊 포트폴리오 가치: ${portfolioValue.toLocaleString()}원</p>
            </div>
        </div>
    `;
    
    // 스크롤 가능한 테이블 컨테이너
    htmlContent += `
        <div style="border: 1px solid #666; border-radius: 5px; overflow: hidden;">
            <!-- 고정 헤더 -->
            <div style="background-color: #333333; border-bottom: 1px solid #666;">
                <table style="width: 100%; border-collapse: collapse; margin: 0;">
                    <tr>
                        <th style="padding: 12px; text-align: left; width: 20%; border-right: 1px solid #666; color: #ffffff;">날짜/시간</th>
                        <th style="padding: 12px; text-align: center; width: 15%; border-right: 1px solid #666; color: #ffffff;">신호</th>
                        <th style="padding: 12px; text-align: center; width: 15%; border-right: 1px solid #666; color: #ffffff;">종목</th>
                        <th style="padding: 12px; text-align: center; width: 20%; border-right: 1px solid #666; color: #ffffff;">포지션 크기</th>
                        <th style="padding: 12px; text-align: right; width: 30%; color: #ffffff;">가격</th>
                    </tr>
                </table>
            </div>
            
            <!-- 스크롤 가능한 내용 -->
            <div style="max-height: 400px; overflow-y: auto; background-color: #2a2a2a;">
                <table style="width: 100%; border-collapse: collapse; margin: 0;">
                    <tbody>
    `;
    
    // 테이블 로우 생성
    tradingSignals.forEach((item, index) => {
        const signalColor = item.signal_type === 'BUY' ? '#28a745' : '#dc3545';
        const signalIcon = item.signal_type === 'BUY' ? '📈' : '📉';
        const rowBgColor = index % 2 === 0 ? '#2a2a2a' : '#1a1a1a';
        
        htmlContent += `
            <tr style="background-color: ${rowBgColor}; border-bottom: 1px solid #444;">
                <td style="padding: 10px; width: 20%; border-right: 1px solid #444; color: #ffffff; font-size: 13px;">${item.target_time}</td>
                <td style="padding: 10px; text-align: center; width: 15%; border-right: 1px solid #444; color: ${signalColor}; font-weight: bold;">
                    ${signalIcon} ${item.signal_type}
                </td>
                <td style="padding: 10px; text-align: center; width: 15%; border-right: 1px solid #444; color: #ffffff; font-size: 13px;">${item.ticker}</td>
                <td style="padding: 10px; text-align: center; width: 20%; border-right: 1px solid #444; color: #ffffff; font-size: 13px;">${(item.position_size * 100).toFixed(1)}%</td>
                <td style="padding: 10px; text-align: right; width: 30%; color: #ffffff; font-size: 13px;">${item.current_price.toLocaleString()}원</td>
            </tr>
        `;
    });
    
    // 테이블 닫기
    htmlContent += `
                    </tbody>
                </table>
            </div>
        </div>
    `;
    
    resultDiv.innerHTML = htmlContent;
}

// 서브플롯 설정을 위한 헬퍼 함수들
// 
// 사용 예시:
// const plotConfig = createSubplotConfig();
//
// // 주가 차트 추가
// addSubplot(plotConfig, {
//     name: 'stock',
//     yDomain: [0.6, 1],
//     xAxisId: 'x',
//     yAxisId: 'y',
//     yAxisConfig: { title: { text: '가격' } },
//     traces: [candlestickTrace, ma5Trace],
//     shapes: [squeezeShapes]
// });
//
// // RSI 차트 추가
// addSubplot(plotConfig, {
//     name: 'rsi',
//     yDomain: [0.4, 0.55],
//     yAxisId: 'y3',
//     yAxisConfig: { title: { text: 'RSI' }, range: [0, 100] },
//     traces: [rsiTrace]
// });
//
// const layout = generateLayout(plotConfig, baseLayout, ticker, dateRange);
// Plotly.newPlot('chart', plotConfig.traces, layout);

function createSubplotConfig() {
    return {
        subplots: [],
        traces: [],
        shapes: [],
        annotations: []
    };
}

function addSubplot(config, {
    name,
    yDomain,
    xAxisId = null,
    yAxisId,
    xAxisConfig = {},
    yAxisConfig = {},
    traces = [],
    shapes = [],
    annotations = []
}) {
    // subplot 정보 저장
    const subplot = {
        name,
        yDomain,
        xAxisId: xAxisId || (config.subplots.length === 0 ? 'x' : `x${config.subplots.length + 1}`),
        yAxisId,
        traces: traces.length
    };
    
    config.subplots.push(subplot);
    
    // traces에 올바른 axis 정보 추가
    traces.forEach(trace => {
        trace.xaxis = subplot.xAxisId;
        trace.yaxis = subplot.yAxisId;
        config.traces.push(trace);
    });
    
    // shapes와 annotations 추가
    config.shapes.push(...shapes);
    config.annotations.push(...annotations);
    
    return subplot;
}

// 전역 변수: 현재 차트의 날짜 데이터 저장
let currentChartDates = [];

function generateLayout(config, baseLayout, ticker, dates) {
    const layout = { ...baseLayout };
    
    // 날짜 라벨 생성 (일정 간격으로)
    const dateLabels = [];
    const dateValues = [];
    const step = Math.max(1, Math.floor(dates.length / 10)); // 최대 10개 라벨

    currentChartDates = [];
    for (let i = 0; i < dates.length; i += 1) {
        // int 형태의 utc timestamp를 YYYY-MM-DD 형식으로 변환
        const date = new Date(dates[i]);
        const pad = (n) => String(n).padStart(2, '0');
        const formatted = `${pad(date.getFullYear() % 100)}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;

        currentChartDates.push(formatted);
        if( i % step === 0) {
            dateValues.push(i);
            dateLabels.push(formatted);
        }
    }
    
    // 각 subplot에 대한 axis 설정 생성
    config.subplots.forEach((subplot, index) => {
        const isFirst = index === 0;
        const isLast = index === config.subplots.length - 1;
        
        // x축 설정
        const xAxisKey = subplot.xAxisId === 'x' ? 'xaxis' : `xaxis${subplot.xAxisId.slice(1)}`;
        layout[xAxisKey] = {
            domain: [0, 1],
            anchor: subplot.yAxisId,
            type: 'linear',
            gridcolor: '#444444',
            tickfont: { color: '#ffffff' },
            linecolor: '#666666',
            showticklabels: isLast, // 마지막 subplot에만 x축 라벨 표시
            range: [0, dates.length - 1],
            matches: isFirst ? undefined : 'x',
            tickmode: 'array',
            tickvals: dateValues,
            ticktext: dateLabels
        };

        // 첫 번째 subplot에 rangeslider 추가
        if (isFirst && config.subplots.length > 1) {
            layout[xAxisKey].rangeslider = {
                visible: true,
                bgcolor: '#1e1e1e',
                bordercolor: '#666666',
                borderwidth: 1,
                thickness: 0.08
            };
        }
        
        // y축 설정
        const yAxisKey = subplot.yAxisId === 'y' ? 'yaxis' : `yaxis${subplot.yAxisId.slice(1)}`;
        layout[yAxisKey] = {
            domain: subplot.yDomain,
            anchor: subplot.xAxisId,
            gridcolor: '#444444',
            tickfont: { color: '#ffffff' },
            linecolor: '#666666',
            autorange: true
        };
    });
    
    // shapes와 annotations 추가
    layout.shapes = [...(layout.shapes || []), ...config.shapes];
    layout.annotations = [...(layout.annotations || []), ...config.annotations];
    
    return layout;
}

// 기본 주가 차트 + Squeeze Momentum 차트 그리기 함수 (서브플롯)
function drawStockChart(stockData, ticker) {
    try {
        if (!stockData || !Array.isArray(stockData) || stockData.length === 0) {
            document.getElementById('stock-chart').innerHTML = '<p>차트 데이터가 없습니다.</p>';
            return;
        }

        // 데이터 변환
        const dates = stockData.map(item => item.date);
        
        // 숫자 인덱스 생성 (0, 1, 2, ...)
        const xIndices = dates.map((_, index) => index);
        
        const opens = stockData.map(item => item.open);
        const highs = stockData.map(item => item.high);
        const lows = stockData.map(item => item.low);
        const closes = stockData.map(item => item.close);
        const volumes = stockData.map(item => item.volume);

        // MA 데이터 (있는 경우)
        const ma5 = stockData.map(item => item.MA5 || null);
        const ma20 = stockData.map(item => item.MA20 || null);
        const ma60 = stockData.map(item => item.MA60 || null);

        // Squeeze Momentum 관련 데이터
        const momentum = stockData.map(item => item.momentum || null);
        const squeezeOn = stockData.map(item => item.squeeze_on || false);
        const hasMomentumData = momentum.some(v => v !== null);

        // subplot 설정 시작
        const plotConfig = createSubplotConfig();

        // === 1. 주가 차트 subplot 추가 ===
        const stockTraces = [];
        
        // 캔들스틱 차트
        const candlestick = {
            x: xIndices,
            open: opens,
            high: highs,
            low: lows,
            close: closes,
            type: 'candlestick',
            name: ticker,
            increasing: { line: { color: '#00ff88' } },
            decreasing: { line: { color: '#ff4444' } }
        };
        stockTraces.push(candlestick);

        // 이동평균선 추가
        if (ma5.some(v => v !== null)) {
            stockTraces.push({
                x: xIndices,
                y: ma5,
                type: 'scatter',
                mode: 'lines',
                name: 'MA5',
                line: { color: '#ffdd44', width: 1 }
            });
        }

        if (ma20.some(v => v !== null)) {
            stockTraces.push({
                x: xIndices,
                y: ma20,
                type: 'scatter',
                mode: 'lines',
                name: 'MA20',
                line: { color: '#44ddff', width: 2 }
            });
        }

        if (ma60.some(v => v !== null)) {
            stockTraces.push({
                x: xIndices,
                y: ma60,
                type: 'scatter',
                mode: 'lines',
                name: 'MA60',
                line: { color: '#ff88dd', width: 2 }
            });
        }

        // Squeeze shapes for stock chart
        const stockShapes = [];
        
        // 주가 차트 subplot 추가
        addSubplot(plotConfig, {
            name: 'stock',
            yDomain: hasMomentumData ? [0.35, 1] : [0.15, 1],
            xAxisId: 'x',
            yAxisId: 'y',
            yAxisConfig: {
                title: {
                    text: '가격 (원)',
                    font: { color: '#ffffff' }
                }
            },
            traces: stockTraces,
            shapes: stockShapes
        });

        // === 2. Momentum 차트 subplot 추가 (데이터가 있는 경우) ===
        if (hasMomentumData) {
            const momentumTraces = [];
            const momentumShapes = [];
            
            // Momentum 히스토그램
            const momentumColors = momentum.map(val => {
                if (val === null || val === undefined) return 'rgba(128,128,128,0.5)';
                return val > 0 ? '#00ff88' : '#ff4444';
            });
            
            momentumTraces.push({
                x: xIndices,
                y: momentum,
                type: 'bar',
                name: 'Momentum',
                marker: { color: momentumColors },
                opacity: 0.8
            });

            // 0선 추가
            momentumTraces.push({
                x: xIndices,
                y: new Array(dates.length).fill(0),
                type: 'scatter',
                mode: 'lines',
                name: 'Zero Line',
                line: { color: '#666666', width: 1, dash: 'dash' },
                showlegend: false
            });

            // Squeeze 신호들 수집 및 표시
            const squeezeOnIndices = [];
            const squeezeOnValues = [];
            const squeezeStartIndices = [];
            const squeezeStartValues = [];
            const squeezeEndIndices = [];
            const squeezeEndValues = [];
            
            // squeeze_on 신호 수집
            squeezeOn.forEach((isOn, index) => {
                if (isOn) {
                    squeezeOnIndices.push(index);
                    squeezeOnValues.push(0); // 0선에 표시
                }
            });
            
            // squeeze_start와 squeeze_end 신호 수집
            let prevSqueezeState = false;
            squeezeOn.forEach((isOn, index) => {
                if (isOn && !prevSqueezeState) {
                    // squeeze 시작
                    squeezeStartIndices.push(index);
                    squeezeStartValues.push(0);
                } else if (!isOn && prevSqueezeState) {
                    // squeeze 종료 (이전 인덱스에서)
                    if (index > 0) {
                        squeezeEndIndices.push(index - 1);
                        squeezeEndValues.push(0);
                    }
                }
                prevSqueezeState = isOn;
            });
            
            // Squeeze On 신호 표시 (흰색 십자)
            if (squeezeOnIndices.length > 0) {
                momentumTraces.push({
                    x: squeezeOnIndices,
                    y: squeezeOnValues,
                    type: 'scatter',
                    mode: 'markers',
                    name: 'Squeeze On',
                    marker: {
                        symbol: 'cross',
                        size: 10,
                        color: '#ffffff',
                        line: { width: 2, color: '#ffffff' }
                    },
                    hovertemplate: '<b>Squeeze On</b><br>' +
                                   '날짜: %{text}<br>' +
                                   '<extra></extra>',
                    text: squeezeOnIndices.map(i => dates[i]),
                    showlegend: true
                });
            }
            
            // Squeeze Start 신호 표시 (진한 회색 십자)
            if (squeezeStartIndices.length > 0) {
                momentumTraces.push({
                    x: squeezeStartIndices,
                    y: squeezeStartValues,
                    type: 'scatter',
                    mode: 'markers',
                    name: 'Squeeze Start',
                    marker: {
                        symbol: 'cross',
                        size: 12,
                        color: '#666666',
                        line: { width: 3, color: '#666666' }
                    },
                    hovertemplate: '<b>Squeeze Start</b><br>' +
                                   '날짜: %{text}<br>' +
                                   '<extra></extra>',
                    text: squeezeStartIndices.map(i => dates[i]),
                    showlegend: true
                });
            }
            
            // Squeeze End 신호 표시 (연한 회색 십자)
            if (squeezeEndIndices.length > 0) {
                momentumTraces.push({
                    x: squeezeEndIndices,
                    y: squeezeEndValues,
                    type: 'scatter',
                    mode: 'markers',
                    name: 'Squeeze End',
                    marker: {
                        symbol: 'cross',
                        size: 12,
                        color: '#999999',
                        line: { width: 3, color: '#999999' }
                    },
                    hovertemplate: '<b>Squeeze End</b><br>' +
                                   '날짜: %{text}<br>' +
                                   '<extra></extra>',
                    text: squeezeEndIndices.map(i => dates[i]),
                    showlegend: true
                });
            }

            // Squeeze 구간 처리
            let squeezeStart = null;
            for (let i = 0; i < squeezeOn.length; i++) {
                if (squeezeOn[i] && squeezeStart === null) {
                    squeezeStart = i;
                } else if (!squeezeOn[i] && squeezeStart !== null) {
                    // 주가 차트용 squeeze 구간
                    stockShapes.push({
                        type: 'rect',
                        xref: 'x',
                        yref: 'y domain',
                        x0: squeezeStart,
                        y0: 0,
                        x1: i-1,
                        y1: 1,
                        fillcolor: 'rgba(255, 255, 0, 0.1)',
                        line: { width: 0 },
                        layer: 'below'
                    });
                    
                    // Momentum 차트용 squeeze 구간
                    momentumShapes.push({
                        type: 'rect',
                        xref: 'x2',
                        yref: 'y2 domain',
                        x0: squeezeStart,
                        y0: 0,
                        x1: i-1,
                        y1: 1,
                        fillcolor: 'rgba(255, 255, 0, 0.1)',
                        line: { width: 0 },
                        layer: 'below'
                    });
                    squeezeStart = null;
                }
            }
            
            // 마지막 squeeze가 끝나지 않은 경우
            if (squeezeStart !== null) {
                stockShapes.push({
                    type: 'rect',
                    xref: 'x',
                    yref: 'y domain',
                    x0: squeezeStart,
                    y0: 0,
                    x1: dates.length - 1,
                    y1: 1,
                    fillcolor: 'rgba(255, 255, 0, 0.1)',
                    line: { width: 0 },
                    layer: 'below'
                });
                
                momentumShapes.push({
                    type: 'rect',
                    xref: 'x2',
                    yref: 'y2 domain',
                    x0: squeezeStart,
                    y0: 0,
                    x1: dates.length - 1,
                    y1: 1,
                    fillcolor: 'rgba(255, 255, 0, 0.1)',
                    line: { width: 0 },
                    layer: 'below'
                });
            }

            // Momentum 차트 subplot 추가
            addSubplot(plotConfig, {
                name: 'momentum',
                yDomain: [0, 0.3],
                xAxisId: 'x2',
                yAxisId: 'y2',
                xAxisConfig: {
                    title: {
                        text: '날짜',
                        font: { color: '#ffffff' }
                    }
                },
                yAxisConfig: {
                    title: {
                        text: 'Momentum',
                        font: { color: '#ffffff' }
                    },
                    zeroline: true,
                    zerolinecolor: '#666666',
                    zerolinewidth: 2
                },
                traces: momentumTraces,
                shapes: momentumShapes
            });
        }

        // 기본 레이아웃 설정
        const baseLayout = {
            title: {
                text: `${ticker} 주가 분석`,
                font: { color: '#ffffff' }
            },
            plot_bgcolor: '#1e1e1e',
            paper_bgcolor: '#000000',
            font: { 
                family: 'Arial, sans-serif',
                color: '#ffffff'
            },
            margin: { l: 50, r: 50, t: 100, b: 50 },
            height: 700,
            showlegend: true,
            legend: {
                x: 0,
                y: 1,
                bgcolor: 'rgba(0,0,0,0.8)',
                bordercolor: 'rgba(255,255,255,0.3)',
                borderwidth: 1,
                font: { color: '#ffffff' }
            }
        };

        // 최종 레이아웃 생성
        const layout = generateLayout(plotConfig, baseLayout, ticker, dates);

        // 차트 그리기
        Plotly.newPlot('stock-chart', plotConfig.traces, layout, {
            responsive: true,
            displayModeBar: true,
            modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d']
        });
        
    } catch (error) {
        console.error('Chart drawing error:', error);
        document.getElementById('stock-chart').innerHTML = `<p>차트 그리기 오류: ${error.message}</p>`;
    }
}

// 새 subplot을 추가하는 헬퍼 함수
function addNewSubplot(chartId, subplotConfig) {
    const currentChart = document.getElementById(chartId);
    if (!currentChart || !currentChart.data) return;
    
    // 기존 layout과 traces 가져오기
    const currentLayout = currentChart.layout;
    const currentTraces = currentChart.data;
    
    // 새로운 subplot에 따른 layout 업데이트
    const newLayout = { ...currentLayout };
    
    // subplot 설정에 따라 새로운 axis 추가
    const xAxisKey = subplotConfig.xAxisId === 'x' ? 'xaxis' : `xaxis${subplotConfig.xAxisId.slice(1)}`;
    const yAxisKey = subplotConfig.yAxisId === 'y' ? 'yaxis' : `yaxis${subplotConfig.yAxisId.slice(1)}`;
    
    newLayout[xAxisKey] = {
        domain: [0, 1],
        anchor: subplotConfig.yAxisId,
        type: 'linear',
        gridcolor: '#444444',
        tickfont: { color: '#ffffff' },
        linecolor: '#666666',
        showticklabels: true,
        matches: 'x', // 첫 번째 x축과 동기화
        ...subplotConfig.xAxisConfig
    };
    
    newLayout[yAxisKey] = {
        domain: subplotConfig.yDomain,
        anchor: subplotConfig.xAxisId,
        gridcolor: '#444444',
        tickfont: { color: '#ffffff' },
        linecolor: '#666666',
        autorange: true,
        ...subplotConfig.yAxisConfig
    };
    
    // 새로운 traces 추가
    const newTraces = subplotConfig.traces.map(trace => ({
        ...trace,
        xaxis: subplotConfig.xAxisId,
        yaxis: subplotConfig.yAxisId
    }));
    
    // 차트 업데이트
    Plotly.addTraces(chartId, newTraces);
    Plotly.relayout(chartId, newLayout);
    
    return { newTraces, newLayout };
}

// 차트에 추가 데이터 업데이트 함수 (신호, 지표 등)
function updateStockChart(tradingSignals = []) {
    try {
        // console.log('updateStockChart 호출됨, 매매 신호:', tradingSignals);
        
        if (!tradingSignals || !Array.isArray(tradingSignals) || tradingSignals.length === 0) {
            console.log('매매 신호 데이터가 없습니다.');
            return;
        }

        const tracesToAdd = [];
        const currentLayout = document.getElementById('stock-chart').layout;

        // 날짜를 인덱스로 변환하는 헬퍼 함수
        function dateToIndex(dateStr) {
            // dateStr 형식: "YYYYMMDD"를 YY-MM-DD 형식으로 변환하여 찾기
            const year = dateStr.slice(2, 4); // "24"
            const month = dateStr.slice(4, 6); // "02"
            const day = dateStr.slice(6, 8); // "02"
            const formatted = `${year}-${month}-${day}`;

            const index = currentChartDates.findIndex(d => d === formatted);
            return index !== -1 ? index : null;
        }

        // 매매 신호 추가
        // console.log('매매 신호 처리 중:', tradingSignals);
        // console.log('현재 차트 날짜:', currentChartDates);
        
        // 매수 신호
        const buySignals = tradingSignals.filter(signal => signal.signal_type === 'BUY');
        if (buySignals.length > 0) {
            const buyIndices = [];
            const buyPrices = [];
            const buyDates = [];
            
            buySignals.forEach(signal => {
                const index = dateToIndex(signal.target_time);
                if (index !== null) {
                    buyIndices.push(index);
                    buyPrices.push(signal.current_price);
                    buyDates.push(`${signal.target_time.slice(0,4)}-${signal.target_time.slice(4,6)}-${signal.target_time.slice(6,8)}`);
                }
            });
            
            // console.log('매수 신호 인덱스:', buyIndices);
            // console.log('매수 신호 가격:', buyPrices);
            
            if (buyIndices.length > 0) {
                // 주가 차트에 매수 신호 추가
                tracesToAdd.push({
                    x: buyIndices,
                    y: buyPrices,
                    type: 'scatter',
                    mode: 'markers',
                    name: '매수 신호',
                    marker: {
                        symbol: 'triangle-up',
                        size: 12,
                        color: '#00ff44',
                        line: { width: 1, color: '#FFFFFF' }
                    },
                    hovertemplate: '<b>매수 신호</b><br>' +
                                   '날짜: %{text}<br>' +
                                   '가격: %{y:,.0f}원<br>' +
                                   '<extra></extra>',
                    text: buyDates,
                    xaxis: 'x',
                    yaxis: 'y'
                });

                // Momentum 차트가 있으면 거기에도 신호 추가
                if (currentLayout && currentLayout.yaxis2) {
                    tracesToAdd.push({
                        x: buyIndices,
                        y: new Array(buyIndices.length).fill(0.05),  // 0선 약간 위
                        type: 'scatter',
                        mode: 'markers',
                        name: '매수 (M)',
                        marker: {
                            symbol: 'triangle-up',
                            size: 8,
                            color: '#00ff44',
                            line: { width: 1, color: '#ffffff' }
                        },
                        showlegend: false,
                        hovertemplate: '<b>매수 신호</b><br>' +
                                       '날짜: %{text}<br>' +
                                       '<extra></extra>',
                        text: buyDates,
                        xaxis: 'x2',
                        yaxis: 'y2'
                    });
                }
            }
        }

        // 매도 신호
        const sellSignals = tradingSignals.filter(signal => signal.signal_type === 'SELL');
        if (sellSignals.length > 0) {
            const sellIndices = [];
            const sellPrices = [];
            const sellDates = [];
            
            sellSignals.forEach(signal => {
                const index = dateToIndex(signal.target_time);
                if (index !== null) {
                    sellIndices.push(index);
                    sellPrices.push(signal.current_price);
                    sellDates.push(`${signal.target_time.slice(0,4)}-${signal.target_time.slice(4,6)}-${signal.target_time.slice(6,8)}`);
                }
            });
            // console.log('매도 신호 인덱스:', sellIndices);
            // console.log('매도 신호 가격:', sellPrices);
            
            if (sellIndices.length > 0) {
                // 주가 차트에 매도 신호 추가
                tracesToAdd.push({
                    x: sellIndices,
                    y: sellPrices,
                    type: 'scatter',
                    mode: 'markers',
                    name: '매도 신호',
                    marker: {
                        symbol: 'triangle-down',
                        size: 12,
                        color: '#ff6600',
                        line: { width: 1, color: '#FFFFFF' }
                    },
                    hovertemplate: '<b>매도 신호</b><br>' +
                                   '날짜: %{text}<br>' +
                                   '가격: %{y:,.0f}원<br>' +
                                   '<extra></extra>',
                    text: sellDates,
                    xaxis: 'x',
                    yaxis: 'y'
                });

                // Momentum 차트가 있으면 거기에도 신호 추가
                if (currentLayout && currentLayout.yaxis2) {
                    tracesToAdd.push({
                        x: sellIndices,
                        y: new Array(sellIndices.length).fill(-0.05),  // 0선 약간 아래
                        type: 'scatter',
                        mode: 'markers',
                        name: '매도 (M)',
                        marker: {
                            symbol: 'triangle-down',
                            size: 8,
                            color: '#ff6600',
                            line: { width: 1, color: '#ffffff' }
                        },
                        showlegend: false,
                        hovertemplate: '<b>매도 신호</b><br>' +
                                       '날짜: %{text}<br>' +
                                       '<extra></extra>',
                        text: sellDates,
                        xaxis: 'x2',
                        yaxis: 'y2'
                    });
                }
            }
        }

        // 모든 traces를 한번에 추가
        if (tracesToAdd.length > 0) {
            console.log('추가할 traces:', tracesToAdd);
            Plotly.addTraces('stock-chart', tracesToAdd);
        } else {
            console.log('추가할 traces가 없습니다.');
        }
        
    } catch (error) {
        console.error('Chart update error:', error);
    }
}