# Discord Bot Integration Guide

이 문서는 auto-trader 서버와 Discord 봇을 연동하는 방법을 설명합니다.

## 1. Discord Bot 설정

### 1.1 Discord Developer Portal에서 봇 생성
1. https://discord.com/developers/applications 접속
2. "New Application" 클릭
3. 애플리케이션 이름 입력 (예: "Auto Trader Bot")
4. "Bot" 탭으로 이동
5. "Add Bot" 클릭
6. 토큰 복사 (나중에 사용)

### 1.2 봇 권한 설정
- "MESSAGE CONTENT INTENT" 활성화
- 필요한 권한:
  - Send Messages
  - Read Message History
  - Use Slash Commands

## 2. 서버 API 엔드포인트

### 2.1 Discord API 엔드포인트
- **Base URL**: `/api/discord`
- **Health Check**: `GET /api/discord/health`
- **Commands List**: `GET /api/discord/commands`
- **Webhook**: `POST /api/discord/webhook`
- **Notification**: `POST /api/discord/notification`
- **User Permissions**: `GET /api/discord/users/{user_id}/permissions`

### 2.2 사용 예시

#### 디스코드에서 잔고 조회
```json
POST /api/discord/webhook
{
    "user_id": "123456789",
    "channel_id": "987654321",
    "command": "balance",
    "parameters": {},
    "timestamp": "2025-08-15T10:30:00Z"
}
```

#### 매수 주문
```json
POST /api/discord/webhook
{
    "user_id": "123456789",
    "channel_id": "987654321", 
    "command": "buy",
    "parameters": {
        "ticker": "BTC",
        "amount": "100000"
    },
    "timestamp": "2025-08-15T10:30:00Z"
}
```

#### 알림 전송
```json
POST /api/discord/notification
{
    "channel_id": "987654321",
    "message": "BTC 매수 주문이 체결되었습니다.",
    "type": "success"
}
```

## 3. Discord 봇 구현 예시

### 3.1 필요한 라이브러리 설치
```bash
pip install discord.py requests
```

### 3.2 기본 봇 코드
```python
import discord
from discord.ext import commands
import requests
import json

# 봇 토큰 (환경변수나 설정파일에서 가져오는 것을 권장)
BOT_TOKEN = 'YOUR_BOT_TOKEN_HERE'
SERVER_URL = 'http://localhost:5000'

# 봇 인스턴스 생성
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} has logged in to Discord!')

@bot.command(name='balance')
async def balance(ctx):
    """잔고 조회"""
    payload = {
        "user_id": str(ctx.author.id),
        "channel_id": str(ctx.channel.id),
        "command": "balance",
        "parameters": {}
    }
    
    try:
        response = requests.post(f'{SERVER_URL}/api/discord/webhook', json=payload)
        result = response.json()
        
        if result['status'] == 'ok':
            data = result['response']['data']
            embed = discord.Embed(title="잔고 조회", color=0x00ff00)
            embed.add_field(name="총 자산", value=data['total_krw'], inline=False)
            embed.add_field(name="사용 가능한 KRW", value=data['available_krw'], inline=False)
            
            for crypto, value in data['crypto_holdings'].items():
                embed.add_field(name=crypto, value=value, inline=True)
                
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"❌ 오류: {result['response']['message']}")
            
    except Exception as e:
        await ctx.send(f"❌ 서버 연결 오류: {str(e)}")

@bot.command(name='buy')
async def buy(ctx, ticker: str, amount: str):
    """매수 주문"""
    payload = {
        "user_id": str(ctx.author.id),
        "channel_id": str(ctx.channel.id),
        "command": "buy",
        "parameters": {
            "ticker": ticker.upper(),
            "amount": amount
        }
    }
    
    try:
        response = requests.post(f'{SERVER_URL}/api/discord/webhook', json=payload)
        result = response.json()
        
        if result['status'] == 'ok':
            if result['response']['type'] == 'success':
                await ctx.send(f"✅ {result['response']['message']}")
            else:
                await ctx.send(f"❌ {result['response']['message']}")
        else:
            await ctx.send(f"❌ 서버 오류: {result['message']}")
            
    except Exception as e:
        await ctx.send(f"❌ 서버 연결 오류: {str(e)}")

@bot.command(name='sell')
async def sell(ctx, ticker: str, amount: str = None):
    """매도 주문"""
    payload = {
        "user_id": str(ctx.author.id),
        "channel_id": str(ctx.channel.id),
        "command": "sell",
        "parameters": {
            "ticker": ticker.upper()
        }
    }
    
    if amount:
        payload["parameters"]["amount"] = amount
    
    try:
        response = requests.post(f'{SERVER_URL}/api/discord/webhook', json=payload)
        result = response.json()
        
        if result['status'] == 'ok':
            if result['response']['type'] == 'success':
                await ctx.send(f"✅ {result['response']['message']}")
            else:
                await ctx.send(f"❌ {result['response']['message']}")
        else:
            await ctx.send(f"❌ 서버 오류: {result['message']}")
            
    except Exception as e:
        await ctx.send(f"❌ 서버 연결 오류: {str(e)}")

@bot.command(name='status')
async def status(ctx):
    """시스템 상태 조회"""
    payload = {
        "user_id": str(ctx.author.id),
        "channel_id": str(ctx.channel.id),
        "command": "status",
        "parameters": {}
    }
    
    try:
        response = requests.post(f'{SERVER_URL}/api/discord/webhook', json=payload)
        result = response.json()
        
        if result['status'] == 'ok':
            data = result['response']['data']
            embed = discord.Embed(title="시스템 상태", color=0x0099ff)
            embed.add_field(name="서버 상태", value=data['server_status'], inline=True)
            embed.add_field(name="API 상태", value=data['api_status'], inline=True)
            embed.add_field(name="업타임", value=data['uptime'], inline=True)
            embed.add_field(name="마지막 신호", value=data['last_signal'], inline=False)
            embed.add_field(name="활성 전략", value=", ".join(data['active_strategies']), inline=False)
            
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"❌ 오류: {result['response']['message']}")
            
    except Exception as e:
        await ctx.send(f"❌ 서버 연결 오류: {str(e)}")

# 봇 실행
if __name__ == '__main__':
    bot.run(BOT_TOKEN)
```

## 4. 사용 가능한 명령어

### 4.1 기본 명령어
- `!balance` - 현재 잔고 조회
- `!buy <ticker> <amount>` - 매수 주문 (예: `!buy BTC 100000`)
- `!sell <ticker> [amount]` - 매도 주문 (예: `!sell BTC` 또는 `!sell BTC 0.01`)
- `!status` - 거래 시스템 상태 조회

### 4.2 추가 구현 가능한 명령어
- `!positions` - 현재 포지션 조회
- `!markets` - 지원 가능한 마켓 조회
- `!chart <ticker>` - 차트 분석 정보
- `!signals` - 최근 매매 신호 조회
- `!performance` - 포트폴리오 성과 분석

## 5. 보안 고려사항

### 5.1 사용자 권한 관리
- Discord 사용자 ID별 권한 설정 필요
- 거래 실행 권한과 조회 권한 분리
- 관리자 권한 설정

### 5.2 환경변수 설정
```bash
# .env 파일
DISCORD_BOT_TOKEN=your_bot_token_here
TRADING_SERVER_URL=http://localhost:5000
ALLOWED_USERS=123456789,987654321
ADMIN_USERS=123456789
```

### 5.3 API 인증
- API 키 또는 JWT 토큰 사용 고려
- Rate limiting 적용
- IP 화이트리스트 설정

## 6. 배포 및 운영

### 6.1 서버 실행
```bash
# Flask 서버 실행
python main.py

# Discord 봇 실행 (별도 터미널)
python discord_bot.py
```

### 6.2 Docker를 사용한 배포
```dockerfile
# Dockerfile 예시
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["python", "main.py"]
```

### 6.3 모니터링
- 로그 파일 확인: `logs/` 디렉토리
- 서버 상태 확인: `GET /health`
- Discord 봇 상태 확인: `GET /api/discord/health`
