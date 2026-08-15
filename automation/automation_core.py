from discord.ext import commands, tasks
from automation.division_information import update_division_stats


class AutomationCore(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.automation_loop.start()

    def cog_unload(self):
        self.automation_loop.cancel()

    @tasks.loop(minutes=6.0)
    async def automation_loop(self):
        # Вызов обновления дивизионов
        await update_division_stats(self.bot)

    @automation_loop.before_loop
    async def before_automation_loop(self):
        # Ждем полной готовности бота, чтобы кэш каналов загрузился
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(AutomationCore(bot))
  
