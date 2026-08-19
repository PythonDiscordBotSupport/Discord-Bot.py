import asyncio
import discord
from discord.ext import commands, tasks
import config
from automation.division_information import update_division_stats
from automation.server_members import update_server_members
from automation.group_members import update_roblox_group_members
from automation.enlisted_members import update_enlisted_stats
from automation.officer_members import update_officer_stats
from automation.hicom_members import update_hicom_stats


class AutomationCore(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Общий цикл запускается каждые 6 минут
        self.automation_loop.start()

    def cog_unload(self):
        self.automation_loop.cancel()

    async def log_error(self, module_name: str, error: Exception):
        """Вспомогательный метод для отправки ошибок в канал errors из конфига"""
        error_msg = f"[AutomationCore] Error in {module_name}: {error}"
        print(error_msg)

        errors_channel_id = getattr(config, "errors", None)
        if errors_channel_id:
            try:
                channel = self.bot.get_channel(int(errors_channel_id))
                if channel:
                    embed = discord.Embed(
                        title="❌ Automation Error",
                        description=f"Ошибка в модуле **{module_name}**:\n`{error}`",
                        color=discord.Color.red()
                    )
                    embed.timestamp = discord.utils.utcnow()
                    await channel.send(embed=embed)
            except Exception as err:
                print(f"[AutomationCore] Failed to send error to Discord channel: {err}")

    @tasks.loop(minutes=6.0)
    async def automation_loop(self):
        # 1. Обновление дивизионов
        try:
            await update_division_stats(self.bot)
        except Exception as e:
            await self.log_error("division_information", e)

        # Ждем 1 минуту
        await asyncio.sleep(60)

        # 2. Обновление участников сервера
        try:
            await update_server_members(self.bot)
        except Exception as e:
            await self.log_error("server_members", e)

        # Ждем 1 минуту
        await asyncio.sleep(60)

        # 3. Обновление участников группы Roblox
        try:
            await update_roblox_group_members(self.bot)
        except Exception as e:
            await self.log_error("roblox_group_members", e)

        # Ждем 1 минуту
        await asyncio.sleep(60)

        # 4. Обновление Enlisted
        try:
            await update_enlisted_stats(self.bot)
        except Exception as e:
            await self.log_error("enlisted_members", e)

        # Ждем 1 минуту
        await asyncio.sleep(60)

        # 5. Обновление Officer
        try:
            await update_officer_stats(self.bot)
        except Exception as e:
            await self.log_error("officer_members", e)

        # Ждем 1 минуту
        await asyncio.sleep(60)

        # 6. Обновление HICOM
        try:
            await update_hicom_stats(self.bot)
        except Exception as e:
            await self.log_error("hicom_members", e)

    @automation_loop.before_loop
    async def before_automation_loop(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(AutomationCore(bot))
            
