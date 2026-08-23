from fastapi import FastAPI
import uvicorn
import threading
import gc

app = FastAPI()

# Принудительно запускаем сборщик мусора чаще, 
# чтобы Python сразу сбрасывал неиспользуемую память (держая рам в лимите до 300мб)
gc.enable()


@app.get("/")
async def root():
    # Периодически подчищаем мусор в памяти после пиковых запросов
    gc.collect()
    return {"status": "alive", "message": "Bot web server is running smoothly!"}


def run_server():
    # Запуск в 1 поток (worker) с отключением лишнего вывода логов, 
    # чтобы не тратить CPU и память на буферизацию
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=10000, 
        log_level="warning",
        access_log=False  # Отключаем лог каждого запроса для экономии ресурсов
    )


def keep_alive():
    """Запускает FastAPI сервер в фоновом потоке"""
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
