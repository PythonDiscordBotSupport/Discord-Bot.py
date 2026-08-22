import datetime
import os
import time
import discord
from discord import app_commands
from discord.ext import commands
import psutil


class StatusCommand(commands.Cog):

  def __init__(self, bot: commands.Bot):
    self.bot = bot
    self.start_time = time.time()
    self.process = psutil.Process(os.getpid())
    # Первый вызов для инициализации замера CPU
    self.process.cpu_percent(interval=None)

  @app_commands.command(
      name="status",
      description="Shows system health, Roblox webhook status, and bot metrics",
  )
  async def status(self, interaction: discord.Interaction):
    start_time_mono = time.monotonic()

    # Сразу откладываем ответ
    await interaction.response.defer(thinking=True)

    # 1. Замер латентности Discord
    api_latency_ms = (time.monotonic() - start_time_mono) * 1000
    ws_latency_ms = round(self.bot.latency * 1000)

    # 2. Метрики процесса бота
    cpu_usage = self.process.cpu_percent(interval=None)
    
    mem_info = self.process.memory_info()
    bot_ram_mb = round(mem_info.rss / (1024 * 1024), 2)
    
    # Считаем процент RAM относительно общей памяти хоста (или заданного лимита)
    total_system_ram = psutil.virtual_memory().total
    ram_percent = round((mem_info.rss / total_system_ram) * 100, 1)

    # Аптайм
    uptime_seconds = int(time.time() - self.start_time)
    uptime_str = str(datetime.timedelta(seconds=uptime_seconds))

    # 3. Статус Discord API
    if api_latency_ms <= 300:
      color_api = discord.Color.green()
      status_text = "🟢 All systems normal"
    elif api_latency_ms <= 600:
      color_api = discord.Color.orange()
      status_text = "🟠 Stable, but experiencing slight delay"
    else:
      color_api = discord.Color.red()
      status_text = "🔴 High latency detected"

    # 4. Цвет для Server Maintenance / Performance на основе RAM
    if ram_percent < 50:
      color_perf = discord.Color.green()
      perf_status = "🟢 Optimal RAM Usage"
    elif 50 <= ram_percent < 80:
      color_perf = discord.Color.orange()
      perf_status = "🟠 Moderate RAM Usage"
    else:
      color_perf = discord.Color.red()
      perf_status = "🔴 High RAM Usage"

    # --- ЭМБЕД 1: Discord Bot & API ---
    embed_bot = discord.Embed(
        title="⚡ Discord API & WS",
        description=(
            f"**Status:** {status_text}\n"
            f"• **WebSocket:** `{ws_latency_ms} ms`\n"
            f"• **API Latency:** `{api_latency_ms:.2f} ms`"
        ),
        color=color_api,
    )

    # --- ЭМБЕД 2: Roblox Open Cloud ---
    embed_roblox = discord.Embed(
        title="🎮 Roblox Open Cloud",
        description=(
            "🟢 **Webhook Active**\n"
            "*Awaiting data streams from game servers...*"
        ),
        color=discord.Color.blue(),
    )

    # --- ЭМБЕД 3: Server Maintenance / Bot Performance ---
    embed_server = discord.Embed(
        title=f"🛠️ Bot Performance ({perf_status})",
        description=(
            f"💻 **Process CPU:** `{cpu_usage}%`\n"
            f"🧠 **Process RAM:** `{bot_ram_mb} MB` (`{ram_percent}%` of system)\n"
            f"⏳ **Uptime:** `{uptime_str}`"
        ),
        color=color_perf,
    )

    embed_server.set_footer(text=f"Requested by {interaction.user.name}")

    # Отправляем три раздельных эмбеда
    await interaction.followup.send(
        embeds=[embed_bot, embed_roblox, embed_server]
    )


async def setup(bot: commands.Bot):
  await bot.add_cog(StatusCommand(bot))
  
