#!/bin/bash
cd /home/pi/workspace/auto-trader
source venv/bin/activate

# ngrok 백그라운드 실행 (로그를 ngrok.log로 저장)
ngrok http --url=joey-joint-redbird.ngrok-free.app 443 > ngrok.log 2>&1 &

python3 main.py
