from fastapi import FastAPI
import uvicorn
import threading

app = FastAPI()


@app.get("/")
async def root():
    return {"status": "alive", "message": "Bot web server is running smoothly!"}


def run_server():
    # Запускаем uvicorn без логов или с минимальными, чтобы не засорять консоль
    uvicorn.run(app, host="0.0.0.0", port=10000, log_level="warning")


def keep_alive():
    """Запускает FastAPI сервер в отдельном потоке, чтобы он не блокировал бота"""
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
