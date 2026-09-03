import asyncio
import aiohttp
from datetime import datetime, timezone, timedelta
from discord.ext import commands
from config import restart_token


async def restart_loop():
    """Бесконечный цикл рестарта в 12:00 и 00:00 GMT."""
    while True:
        try:
            now = datetime.now(timezone.utc)
            target_hours = [0, 12]
            
            next_target = None
            for h in target_hours:
                candidate = now.replace(hour=h, minute=0, second=0, microsecond=0)
                if candidate > now:
                    next_target = candidate
                    break
            
            if not next_target:
                tomorrow_date = now + timedelta(days=1)
                next_target = tomorrow_date.replace(hour=target_hours[0], minute=0, second=0, microsecond=0)
            
            sleep_seconds = (next_target - now).total_seconds()
            await asyncio.sleep(sleep_seconds)
            
            # Отправляем POST-запрос на рестарт
            async with aiohttp.ClientSession() as session:
                async with session.post(restart_token) as response:
                    pass
                    
        except Exception:
            await asyncio.sleep(60)


async def setup(bot: commands.Bot):
    # Автоматически запускаем цикл, когда бот подгружает этот модуль
    bot.loop.create_task(restart_loop())
    
