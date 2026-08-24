import datetime
import os
import time
import tracemalloc
import discord
from discord import app_commands
from discord.ext import commands
import psutil

# Включаем трекинг памяти Python при запуске файла
if not tracemalloc.is_tracing():
    tracemalloc.start(10)


class StatusCommand(commands.Cog):
  # Цветовая палитра в одном формате
  COLOR_GREEN = discord.Color.from_str("#73d15e")
  COLOR_ORANGE = discord.Color.from_str("#e8b53f")
  COLOR_RED = discord.Color.from_str("#b81f24")
  COLOR_BLUE = discord.Color.from_str("#4ec3ed")

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
    raw_cpu_usage = self.process.cpu_percent(interval=None)
    cpu_usage = round(raw_cpu_usage * 10, 1)

    mem_info = self.process.memory_info()
    bot_ram_mb = round(mem_info.rss / (1024 * 1024), 2)
    
    container_ram_limit_mb = 512
    ram_percent = round((bot_ram_mb / container_ram_limit_mb) * 100, 1)

    # --- ТОЧНЫЙ АНАЛИЗ ПАМЯТИ ПО ВАШИМ ПАПКАМ ---
    snapshot = tracemalloc.take_snapshot()
    stats = snapshot.statistics('filename')

    # Инициализируем словарь под ваши папки со скриншота
    folder_usage = {
        "automation": 0.0,
        "core": 0.0,
        "discord_commands": 0.0,
        "roblox_commands": 0.0,
        "libraries": 0.0,
        "other": 0.0
    }

    for stat in stats:
        filepath = stat.traceback[0].filename.replace("\\", "/")
        size_kb = stat.size / 1024

        if "automation" in filepath:
            folder_usage["automation"] += size_kb
        elif "core" in filepath:
            folder_usage["core"] += size_kb
        elif "discord_commands" in filepath:
            folder_usage["discord_commands"] += size_kb
        elif "roblox_commands" in filepath:
            folder_usage["roblox_commands"] += size_kb
        elif "site-packages" in filepath or "dist-packages" in filepath:
            folder_usage["libraries"] += size_kb
        else:
            folder_usage["other"] += size_kb

    # Конвертируем килобайты в мегабайты
    auto_mb = round(folder_usage["automation"] / 1024, 2)
    core_mb = round(folder_usage["core"] / 1024, 2)
    discord_cmd_mb = round(folder_usage["discord_commands"] / 1024, 2)
    roblox_cmd_mb = round(folder_usage["roblox_commands"] / 1024, 2)
    libs_mb = round(folder_usage["libraries"] / 1024, 2)
    other_mb = round(folder_usage["other"] / 1024, 2)

    # Аптайм
    uptime_seconds = int(time.time() - self.start_time)
    uptime_str = str(datetime.timedelta(seconds=uptime_seconds))

    # 3. Статус Discord API
    if api_latency_ms <= 250:
      color_api = self.COLOR_GREEN
      status_text = "⚡ Ultra Fast Connection"
    elif api_latency_ms <= 400:
      color_api = self.COLOR_GREEN
      status_text = "🟢 Good Connection"
    elif api_latency_ms <= 600:
      color_api = self.COLOR_ORANGE
      status_text = "🟠 Comfortable Connection"
    else:
      color_api = self.COLOR_RED
      status_text = "🔴 Unstable Connection"

    # 4. Цвет для Bot Performance
    if ram_percent < 50:
      color_perf = self.COLOR_GREEN
      perf_status = "🟢 Optimal RAM Usage"
    elif 50 <= ram_percent < 80:
      color_perf = self.COLOR_ORANGE
      perf_status = "🟠 Moderate RAM Usage"
    else:
      color_perf = self.COLOR_RED
      perf_status = "🔴 High RAM Usage (Near Limit)"

    # --- ЭМБЕД 1: Discord Bot & API ---
    embed_bot = discord.Embed(
        title="⚡ Discord API",
        description=(
            f"**Status:** {status_text}\n"
            f"• **WebSocket:** `{ws_latency_ms} ms`\n"
            f"• **API Latency:** `{api_latency_ms:.2f} ms`"
        ),
        color=color_api,
    )

    # --- ЭМБЕД 2: Roblox Open Cloud ---
    embed_roblox = discord.Embed(
        title="🕹️ Roblox Open Cloud",
        description=(
            "🟢 **Webhook Active**\n"
            "*Awaiting data streams from game servers...*"
        ),
        color=self.COLOR_BLUE,
    )

    # --- ЭМБЕД 3: Bot Performance (Детально по вашим папкам) ---
    embed_server = discord.Embed(
        title=f"🛠️ Bot Performance ({perf_status})",
        description=(
            f"💻 **Process CPU:** `{cpu_usage}%`\n"
            f"🧠 **Process RAM:** `{bot_ram_mb} MB / {container_ram_limit_mb} MB` (`{ram_percent}%`)\n\n"
            f"📂 **RAM Breakdown:**\n"
            f"• `automation/`: `{auto_mb} MB`\n"
            f"• `core/`: `{core_mb} MB`\n"
            f"• `discord_commands/`: `{discord_cmd_mb} MB`\n"
            f"• `roblox_commands/`: `{roblox_cmd_mb} MB`\n"
            f"• `Libraries`: `{libs_mb} MB`\n\n"
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
  
