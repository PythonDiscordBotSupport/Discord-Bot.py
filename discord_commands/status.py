import time
import discord
from discord import app_commands
from discord.ext import commands
import psutil
import datetime


class StatusCommand(commands.Cog):

  def __init__(self, bot: commands.Bot):
    self.bot = bot
    # Запоминаем время запуска бота для расчета аптайма
    self.start_time = time.time()

  @app_commands.command(
      name="status",
      description=(
          "Shows system health, Roblox webhook status, and bot metrics"
      ),
  )
  async def status(self, interaction: discord.Interaction):
    start_time = time.monotonic()

    # Сразу откладываем ответ, так как сбор данных может занять долю секунды
    await interaction.response.defer(thinking=True)

    # 1. Замер латентности
    api_latency_ms = (time.monotonic() - start_time) * 1000
    ws_latency_ms = round(self.bot.latency * 1000)

    # 2. Сбор системных метрик через psutil (для Server Maintenance)
    cpu_usage = psutil.cpu_percent(interval=None)
    
    # Память хоста
    mem = psutil.virtual_memory()
    ram_total_mb = round(mem.total / (1024 * 1024))
    ram_used_mb = round(mem.used / (1024 * 1024))
    ram_percent = mem.percent

    # Диск хоста
    disk = psutil.disk_usage('/')
    disk_total_gb = round(disk.total / (1024 * 1024 * 1024), 1)
    disk_free_gb = round(disk.free / (1024 * 1024 * 1024), 1)
    disk_percent = disk.percent

    # Аптайм (время работы бота)
    uptime_seconds = int(time.time() - self.start_time)
    uptime_str = str(datetime.timedelta(seconds=uptime_seconds))

    # 3. Определяем статус по API латентности
    if api_latency_ms <= 300:
      color = discord.Color.green()
      status_text = "🟢 All systems normal"
    elif api_latency_ms <= 600:
      color = discord.Color.orange()
      status_text = "🟠 Stable, but experiencing slight delay"
    else:
      color = discord.Color.red()
      status_text = "🔴 High latency detected"

    # Создаем эмбед
    embed = discord.Embed(
        title="🤖 Bot & Server Status", description=status_text, color=color
    )

    # Поле: Discord Bot / API
    embed.add_field(
        name="⚡ Discord API & WS",
        value=f"WebSocket: `{ws_latency_ms} ms`\nAPI: `{api_latency_ms:.2f} ms`",
        inline=False,
    )

    # Поле: Roblox Open Cloud (заглушка под вебхук, как вы просили)
    embed.add_field(
        name="🎮 Roblox Open Cloud",
        value="🟢 Webhook Active\n*(Awaiting data streams)*",
        inline=False,
    )

    # Поле: Server Maintenance (реальные метрики хоста)
    embed.add_field(
        name="🛠️ Server Maintenance",
        value=(
            f"💻 **CPU Usage:** `{cpu_usage}%`\n"
            f"🧠 **RAM:** `{ram_used_mb} MB / {ram_total_mb} MB` (`{ram_percent}%`)\n"
            f"💾 **Disk Free:** `{disk_free_gb} GB / {disk_total_gb} GB` (`{disk_percent}%` used)\n"
            f"⏳ **Uptime:** `{uptime_str}`"
        ),
        inline=False,
    )

    embed.set_footer(text=f"Requested by {interaction.user.name}")

    # Отправляем готовый результат
    await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
  await bot.add_cog(StatusCommand(bot))
  
