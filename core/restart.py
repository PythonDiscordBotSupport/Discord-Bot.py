import asyncio
import aiohttp
from datetime import datetime, timezone
from discord.ext import commands
from config import restart_token


async def restart_loop():
    """Бесконечный цикл, который ждет точного времени (12:00 и 00:00 GMT) для рестарта."""
    while True:
        try:
            now = datetime.now(timezone.utc)
            
            # Определяем целевые часы: 00:00 и 12:00
            target_hours = [0, 12]
            
            # Ищем ближайший следующий час рестарта
            next_target = None
            for h in target_hours:
                candidate = now.replace(hour=h, minute=0, second=0, microsecond=0)
                if candidate > now:
                    next_target = candidate
                    break
            
            # Если сегодня больше нет целевых часов, берем первый час завтрашнего дня
            if not next_target:
                tomorrow = now.date() + asyncio.get_running_loop().time() # проще через datetime
                from datetime import timedelta
                tomorrow_date = now + timedelta(days=1)
                next_target = tomorrow_date.replace(hour=target_hours[0], minute=0, second=0, microsecond=0)
            
            # Считаем сколько секунд осталось ждать
            sleep_seconds = (next_target - now).total_seconds()
            await asyncio.sleep(sleep_seconds)
            
            # Выполняем POST-запрос на рестарт
            async with aiohttp.ClientSession() as session:
                async with session.post(restart_token) as response:
                    pass
                    
        except Exception:
            # Защита от падения цикла при проблемах с сетью, ждем минуту перед повтором
            await asyncio.sleep(60)


async def setup(bot: commands.Bot):
    # Запускаем фоновую задачу при инициализации модуля
    bot.loop.create_task(restart_loop())
