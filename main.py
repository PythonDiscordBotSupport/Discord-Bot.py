from core.connection import start_bot
from web_server import keep_alive  # Импортируем нашу функцию

if __name__ == "__main__":
    print("[System] Starting FastAPI web server...")
    keep_alive()
    
    print("[System] Starting Discord bot...")
    start_bot()
    
