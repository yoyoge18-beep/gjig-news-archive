#!/bin/bash
cd "$(dirname "$0")"
echo "======================================"
echo "  대학 기사 아카이브 서버 시작 중..."
echo "======================================"
python3 app.py &
sleep 2
open http://localhost:5001
echo ""
echo "브라우저가 열렸습니다."
echo "종료하려면 이 창을 닫으세요."
wait
