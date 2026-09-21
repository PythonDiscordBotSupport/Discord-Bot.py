import asyncio
import aiohttp
from datetime import datetime, timezone
from discord.ext import commands
from config import restart_token


class ConnectionWatchdog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        # Фиксируем время последнего пинга/события от Discord
        self.last_seen = datetime.now(timezone.utc)
        self.max_downtime = 600  # 10 минут
        self.watchdog_task = self.bot.loop.create_task(self.watchdog_loop())

    def cog_unload(self):
        self.watchdog_task.cancel()

    # Обновляем время при любых активных событиях от шлюза
    @commands.Cog.listener()
    async def on_socket_raw_receive(self, msg):
        self.last_seen = datetime.now(timezone.utc)

    @commands.Cog.listener()
    async def on_connect(self):
        self.last_seen = datetime.now(timezone.utc)
        print("🟢 Соединение с Discord подтверждено (Watchdog сброшен).")

    async def watchdog_loop(self):
        await self.bot.wait_until_ready()
        print("🛡️ Connection Watchdog успешно запущен.")

        while not self.bot.is_closed():
            await asyncio.sleep(60)  две минуты проверяем

            now = datetime.now(timezone.utc)
            downtime = (now - self.last_seen).total_seconds()

            print(f"⏱️ Время без активности шлюза Discord: {int(downtime)} сек.")

            # Если бот не получал от Discord вообще никаких пакетов дольше лимита
            if downtime >= self.max_downtime:
                print("🚨 Шлюз завис! Отправка запроса на рестарт Render...")
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(restart_token) as response:
                            if response.status == 200:
                                print("🚀 Запрос на рестарт успешно отправлен!")
                            else:
                                print(f"❌ Ошибка рестарта: статус {response.status}")
                except Exception as e:
                    print(f"❌ Исключение при запросе рестарта: {e}")

                await asyncio.sleep(120)  # Пауза, чтобы не спамить рестартами


async def setup(bot: commands.Bot):
    await bot.add_cog(ConnectionWatchdog(bot))
    
