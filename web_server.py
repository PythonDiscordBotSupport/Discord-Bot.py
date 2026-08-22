from flask import Flask, request
from threading import Thread
import time
import os

app = Flask('')

# Словарь для хранения времени последнего запроса от IP: { "127.0.0.1": 1718000000.0 }
request_limits = {}
TIME_WINDOW = 10  секунд

@app.route('/')
def home():
    client_ip = request.remote_addr
    current_time = time.time()
    
    # Проверяем, был ли уже запрос от этого IP и прошло ли меньше 10 секунд
    if client_ip in request_limits:
        elapsed_time = current_time - request_limits[client_ip]
        if elapsed_time < TIME_WINDOW:
            # Если прошло меньше 10 секунд — игнорируем и возвращаем ошибку
            return "Too Many Requests. Please wait.", 429

    # Обновляем время последнего запроса для этого IP
    request_limits[client_ip] = current_time
    
    return "Bot is running!", 200

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()
    
