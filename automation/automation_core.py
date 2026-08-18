import asyncio
from discord.ext import commands, tasks
from automation.division_information import update_division_stats
from automation.server_members import update_server_members
from automation.group_members import update_roblox_group_members


class AutomationCore(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Интервал цикла равен 4 минутам
        self.automation_loop.start()

    def cog_unload(self):
        self.automation_loop.cancel()

    @tasks.loop(minutes=4.0)
    async def automation_loop(self):
        # 1. Запуск обновления дивизионов
        await update_division_stats(self.bot)

        # 2. Ждем 1 минуту перед запуском участников сервера
        await asyncio.sleep(60)

        # 3. Запуск обновления участников сервера
        await update_server_members(self.bot)

        # 4. Ждем еще 1 минуту перед запуском участников группы роблокса
        await asyncio.sleep(60)

        # 5. Запуск обновления участников группы роблокса
        await update_roblox_group_members(self.bot)

        # После этого tasks.loop(minutes=4.0) подождет оставшееся время до нового цикла.

    @automation_loop.before_loop
    async def before_automation_loop(self):
        # Ждем полной готовности бота, чтобы кэш каналов загрузился
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(AutomationCore(bot))
async def setup(bot: commands.Bot):
    await bot.add_cog(AutomationCore(bot))
    
