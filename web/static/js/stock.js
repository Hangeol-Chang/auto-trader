
tickers = {};

async function getFullTicker() {
    try {
        const response = await fetch('/api/stock/tickers');
        if (!response.ok) throw new Error('Network response was not ok');
        const data = await response.json();

        data.data.map(row => {
            tickers[row.ticker] = {
                market: row.market,
                name: row.name,
                ticker: row.ticker,
            }
        })

    } catch (error) {
        console.error('Error fetching full ticker list:', error);
    }
}

async function findTicker() {
    const tickerInput = document.getElementById('ticker-input').value.trim();
    const searchType = document.getElementById('ticker-searchType').value;

    if( !tickers || Object.keys(tickers).length === 0) {
        await getFullTicker();
    }

    let result = [];
    if (searchType === 'ticker') {
        result.push(tickers[tickerInput]);

    } else if (searchType === 'name') {
        result.push(...Object.values(tickers).filter(ticker => ticker.name.includes(tickerInput)));
    }

    console.log('Search result:', result);
    // id="ticker-result"에 결과를 표시
    const resultDiv = document.getElementById('ticker-result');
    if (result.length > 0) {
        resultDiv.innerHTML = result.map(ticker => `<p>Found: ${ticker.name} || ${ticker.market} | ${ticker.ticker}</p>`).join('');
    } else {
        resultDiv.innerHTML = `<p>No results found for "${tickerInput}"</p>`;
    }
}