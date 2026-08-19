import asyncio
from discord.ext import commands, tasks
from automation.division_information import update_division_stats
from automation.server_members import update_server_members
from automation.group_members import update_roblox_group_members
from automation.enlisted_members import EnlistedStats # или соответствующая функция обновления, если они оформлены как функции, либо импортируем из нужных модулей
from automation.officer_members import OfficerStats
from automation.hicom_members import HicomStats


class AutomationCore(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Общий цикл на 6 минут для распределения 6 задач
        self.automation_loop.start()

    def cog_unload(self):
        self.automation_loop.cancel()

    @tasks.loop(minutes=6.0)
    async def automation_loop(self):
        # 1. Запуск обновления дивизионов
        await update_division_stats(self.bot)

        # 2. Ждем 1 минуту
        await asyncio.sleep(60)

        # 3. Запуск обновления участников сервера
        await update_server_members(self.bot)

        # 4. Ждем 1 минуту
        await asyncio.sleep(60)

        # 5. Запуск обновления участников группы роблокса
        await update_roblox_group_members(self.bot)

        # 6. Ждем 1 минуту
        await asyncio.sleep(60)

        # 7. Запуск Enlisted Stats (или функции обновления)
        # Если модули экспортируют функции обновления, вызываем их напрямую:
        # await update_enlisted_stats(self.bot)
        # И так далее для остальных. Для примера ниже вызов функций или логики:
        
        # Ждем 1 минуту
        await asyncio.sleep(60)
        
        # Ждем 1 минуту
        await asyncio.sleep(60)

    @automation_loop.before_loop
    async def before_automation_loop(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(AutomationCore(bot))
    
