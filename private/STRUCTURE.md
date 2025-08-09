## keys.json
```json
{
    "PROD": [
        {
            "CANO": 00000000,
            "APP_KEY": "---",
            "APP_SECRET": "---",
            "URL_BASE": "https://openapi.koreainvestment.com:9443"
        },
        {
            "CANO": 00000000,
            "APP_KEY": "---",
            "APP_SECRET": "---",
            "URL_BASE": "https://openapi.koreainvestment.com:9443"
        }
    ],
    "VPS": [
        {
            "CANO": 00000000,
            "APP_KEY": "---",
            "APP_SECRET": "---",
            "URL_BASE" : "https://openapivts.koreainvestment.com:29443"
        }
    ]
}
```

### token.json
```json
{
    "PROD": {
        "0" : {
            "APP_TOKEN": "",
            "TOKEN_EXPIRE_TIME": 0,
            "WS_APPROVAL_KEY" : 0,
            "WS_TOKEN_EXPIRE_TIME" : 0
        },
        "1" : {
            "APP_TOKEN": "",
            "TOKEN_EXPIRE_TIME": 0,
            "WS_APPROVAL_KEY" : 0,
            "WS_TOKEN_EXPIRE_TIME" : 0
        }
    },
    "VPS": {
        "0" : {
            "APP_TOKEN": "",
            "TOKEN_EXPIRE_TIME" : 0,
            "WS_APPROVAL_KEY" : 0,
            "WS_TOKEN_EXPIRE_TIME" : 0
        }
    }
}
```

### state_{}.json
```json
{
    "balance": 10000000,
    "portfolioValue": 10000000,
    "positions": {},
    "trade_history": [],
    "last_update": "2025-07-22T19:50:49.409572",
    "status": "stopped"
}
```