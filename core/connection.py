from datetime import datetime
import os
import discord
from discord.ext import commands
from config import bot_token, errors, notifications

# 1. Включаем ВСЕ интенты (включая привилегированные)
intents = discord.Intents.all()

bot = commands.Bot(command_prefix="!", intents=intents)

loaded_modules = []
failed_modules = []
is_first_ready = True  # Флаг для предотвращения спама при переподключениях


async def load_extensions():
    folders = ["discord_commands", "roblox_commands", "automation"]

    # Загружаем модули из стандартных папок
    for folder in folders:
        if os.path.exists(folder):
            for filename in os.listdir(folder):
                if filename.endswith(".py") and not filename.startswith("_"):
                    module_name = f"{folder}.{filename[:-3]}"
                    try:
                        await bot.load_extension(module_name)
                        loaded_modules.append(module_name)
                        print(f"Loaded module: {module_name}")
                    except Exception as e:
                        failed_modules.append((module_name, str(e)))
                        print(f"Failed to load {module_name}: {e}")

    # Точечно загружаем системный модуль рестарта из core
    try:
        await bot.load_extension("core.restart")
        loaded_modules.append("core.restart")
        print("Loaded module: core.restart")
    except Exception as e:
        failed_modules.append(("core.restart", str(e)))
        print(f"Failed to load core.restart: {e}")

@bot.event
async def setup_hook():
    await load_extensions()
    
    # Синхронизируем слеш-команды с Discord
    try:
        synced = await bot.tree.sync()
        print(f"Successfully synced {len(synced)} command(s).")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
        
