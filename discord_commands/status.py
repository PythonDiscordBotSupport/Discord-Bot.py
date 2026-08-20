import random
import time
import asyncio
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

    # Сразу откладываем ответ
    await interaction.response.defer(thinking=True)

    # Вычисляем реальное прошедшее время API
    elapsed_ms = (time.monotonic() - start_time) * 1000

    # Если ответ прошел быстрее 2.5 секунд (2500 мс), 
    # имитируем честную задержку в пределах этого диапазона для красоты,
    # либо фиксируем быструю работу. 
    # (Здесь сделано так, чтобы время было динамичным от реального до 2500мс, 
    # но если вы хотите строго реальное — просто уберите asyncio.sleep)
    if elapsed_ms < 2500:
        # Случайная или фиксированная имитация «думающего» процесса до 2.5 сек
        # Можете заменить на random.uniform(500, 2500) для реалистичного плавающего пинга
        simulated_delay = random.uniform(0.5, 2.0) # в секундах
        await asyncio.sleep(simulated_delay)
    
    # Финальный пересчет времени с учетом задержки
    api_latency_ms = (time.monotonic() - start_time) * 1000

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

    # Создаем эмбед
    embed = discord.Embed(
        title="🤖 Bot Status", description=status_text, color=color
    )
    embed.add_field(
        name="WebSocket Ping", value=f"`{ws_latency_ms} ms`", inline=True
    )
    embed.add_field(
        name="API Latency", value=f"`{api_latency_ms:.2f} ms`", inline=True
    )

    embed.set_footer(text=f"Requested by {interaction.user.name}")

    # Отправляем готовый результат
    await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
  await bot.add_cog(StatusCommand(bot))
  
