import asyncio
import aiohttp
from discord.ext import commands
from config import restart_token


class ConnectionWatchdog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.disconnect_time = None
        self.max_downtime = 600  # 10 минут в секундах
        self.watchdog_task = self.bot.loop.create_type_safely(
            self.watchdog_loop()
        )  # или стандартный create_task
        self.watchdog_task = self.bot.loop.create_task(self.watchdog_loop())

    def cog_unload(self):
        self.watchdog_task.cancel()

    @commands.Cog.listener()
    async def on_disconnect(self):
        # Срабатывает мгновенно при потере связи с Discord
        if self.disconnect_time is None:
            loop = asyncio.get_running_loop()
            self.disconnect_time = loop.time()
            print("⚠️ Соединение с Discord потеряно! Запущен отсчет времени...")

    @commands.Cog.listener()
    async def on_connect(self):
        # Срабатывает при успешном восстановлении связи
        if self.disconnect_time is not None:
            print("🟢 Соединение восстановлено! Таймер сброшен.")
            self.disconnect_time = None

    async def watchdog_loop(self):
        await self.bot.wait_until_ready()
        print("🛡️ Connection Watchdog успешно запущен.")

        while not self.bot.is_closed():
            await asyncio.sleep(30)  # Проверяем статус каждые 30 секунд

            # Если disconnect_time не задан, значит, всё в порядке
            if self.disconnect_time is None:
                continue

            # Вычисляем время простоя
            loop = asyncio.get_running_loop()
            current_time = loop.time()
            elapsed_downtime = current_time - self.disconnect_time

            print(
                f"⏱️ Бот оффлайн уже {int(elapsed_downtime)} сек. (Лимит: {self.max_downtime} сек.)"
            )

            # Если лимит исчерпан
            if elapsed_downtime >= self.max_downtime:
                print(
                    "🚨 Лимит простоя исчерпан! Отправка запроса на перезапуск Render..."
                )
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(restart_token) as response:
                            if response.status == 200:
                                print(
                                    "🚀 Запрос на перезапуск успешно отправлен!"
                                )
                            else:
                                print(
                                    f"❌ Ошибка при запросе рестарта. Статус: {response.status}"
                                )
                except Exception as e:
                    print(f"❌ Исключение при отправке запроса: {e}")

                # Защита от спама запросами (ждем 2 минуты перед повторной попыткой, если рестарт завис)
                await asyncio.sleep(120)


async def setup(bot: commands.Bot):
    await bot.add_cog(ConnectionWatchdog(bot))
    
