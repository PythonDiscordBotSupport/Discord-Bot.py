from flask import Flask, request
from threading import Thread
import time
import os

app = Flask('')

# Словарь: IP -> до какого времени (timestamp) этот IP заблокирован
ip_block_until = {}
BAN_DURATION = 3  # Секунды бана за попытку спама
TIME_WINDOW = 10  # Окно для проверки частоты
request_limits = {}

@app.route('/')
def home():
    client_ip = request.remote_addr
    current_time = time.time()
    
    # 1. Проверяем, в бане ли уже этот IP
    if client_ip in ip_block_until:
        if current_time < ip_block_until[client_ip]:
            # IP всё ещё в черном списке — мгновенно обрываем соединение без ожидания!
            return "", 444
        else:
            # Время бана истекло, удаляем из черного списка
            del ip_block_until[client_ip]

    # 2. Проверяем частоту запросов
    if client_ip in request_limits:
        elapsed_time = current_time - request_limits[client_ip]
        if elapsed_time < TIME_WINDOW:
            # Спам! Ставим IP в бан на 3 секунды, но СРАЗУ же возвращаем отказ, без time.sleep()
            ip_block_until[client_ip] = current_time + BAN_DURATION
            return "", 444

    # Запоминаем время последнего легитимного запроса
    request_limits[client_ip] = current_time
    return "Bot is running!", 200

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()
    
