import time
import discord
from discord import app_commands
from discord.ext import commands


class StatusCommand(commands.Cog):

  def __init__(self, bot: commands.Bot):
    self.bot = bot

  @app_commands.command(
      name="status", description="Shows the current bot latency and WebSocket ping"
  )
  async def status(self, interaction: discord.Interaction):
    start_time = time.monotonic()

    # WebSocket ping в миллисекундах
    ws_latency_ms = round(self.bot.latency * 1000)

    # Определяем цвет и текстовый статус на основе вебсокета
    if ws_latency_ms <= 400:
      color = discord.Color.green()
      status_text = "🟢 All systems normal"
    elif ws_latency_ms <= 600:
      color = discord.Color.orange()
      status_text = "🟠 Stable, but experiencing slight delay"
    else:
      color = discord.Color.red()
      status_text = "🔴 High latency detected"

    # Откладываем ответ для честного замерения API Latency
    await interaction.response.defer(thinking=True)

    api_latency_ms = round((time.monotonic() - start_time) * 1000)

    # Создаем эмбед
    embed = discord.Embed(
        title="🤖 Bot Status", description=status_text, color=color
    )
    embed.add_field(
        name="WebSocket Ping", value=f"`{ws_latency_ms} ms`", inline=True
    )
    embed.add_field(
        name="API Latency", value=f"`{api_latency_ms} ms`", inline=True
    )

    embed.set_footer(text=f"Requested by {interaction.user.name}")

    # Отправляем готовый результат
    await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
  await bot.add_cog(StatusCommand(bot))
  
