#!/bin/bash

trap "kill 0" EXIT

echo "☕️ Запуск сервера кофейни..."
source .venv/bin/activate

python server.py &

streamlit run dashboard.py &

ngrok http --url=cornstalk-unifier-levers.ngrok-free.dev 8000