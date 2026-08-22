from flask import Flask, request
from threading import Thread
import time
import os

app = Flask('')

request_limits = {}
TIME_WINDOW = 10  # секунд

@app.route('/')
def home():
    client_ip = request.remote_addr
    current_time = time.time()
    
    if client_ip in request_limits:
        elapsed_time = current_time - request_limits[client_ip]
        if elapsed_time < TIME_WINDOW:
            # 🛡️ СИМУЛЯЦИЯ «ЧЕРНОЙ ДЫРЫ»:
            # Мы не шлем быстрый ответ 429. Мы заставляем поток "уснуть".
            # Спамер будет висеть на этом запросе до таймаута (в его же скрипте вылетит asyncio.TimeoutError),
            # а ваш сервер не будет тратить процессор на генерацию текстов.
            time.sleep(3) 
            return "", 444 # Обрыв соединения

    request_limits[client_ip] = current_time
    return "Bot is running!", 200

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()
    
