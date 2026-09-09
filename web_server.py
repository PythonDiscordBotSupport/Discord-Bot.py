from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn
import threading

# Импортируем вашу ссылку из конфига
from config import restart_token

app = FastAPI()


@app.get("/", response_class=HTMLResponse)
async def root():
    # Генерируем HTML с большой красной кнопкой и ссылкой из конфига
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <title>Server Status</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                text-align: center;
                margin-top: 100px;
                background-color: #f4f4f9;
            }}
            h1 {{
                color: #333;
                margin-bottom: 30px;
            }}
            .restart-btn {{
                background-color: #ff4d4d;
                color: white;
                padding: 20px 40px;
                font-size: 20px;
                font-weight: bold;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                text-decoration: none;
                display: inline-block;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2);
                transition: background-color 0.2s;
            }}
            .restart-btn:hover {{
                background-color: #cc0000;
            }}
        </style>
    </head>
    <body>
        <h1>The server is running</h1>
        <a href="{restart_token}" class="restart-btn">RESTART</a>
    </body>
    </html>
    """
    return html_content


def run_server():
    uvicorn.run(app, host="0.0.0.0", port=10000, log_level="warning")


def keep_alive():
    """Запускает FastAPI сервер в отдельном потоке, чтобы он не блокировал бота"""
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
