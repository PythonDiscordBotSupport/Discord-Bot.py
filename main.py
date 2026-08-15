from core.connection import start_bot
from web_server import keep_alive  # Импортируем из вашего web_server.py

if __name__ == "__main__":
    print("[System] Starting Flask web server...")
    keep_alive()
    
    print("[System] Starting Discord bot...")
    start_bot()
