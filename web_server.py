from flask import Flask, request
from threading import Thread
import time
import os

app = Flask('')

# Словарь для хранения времени последнего запроса от IP
request_limits = {}
TIME_WINDOW = 10  # секунд

@app.route('/')
def home():
    client_ip = request.remote_addr
    current_time = time.time()
    
    if client_ip in request_limits:
        elapsed_time = current_time - request_limits[client_ip]
        if elapsed_time < TIME_WINDOW:
            # ТУПО ИГНОРИРУЕМ: заставляем поток "спать" и ничего не возвращаем
            # Или возвращаем пустой ответ с обрывом (например, код 444, который Nginx/Flask воспринимает как сброс)
            time.sleep(1) # Защита от моментального заспама процессора
            return "", 444

    # Обновляем время последнего запроса
    request_limits[client_ip] = current_time
    
    return "Bot is running!", 200

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()
    
