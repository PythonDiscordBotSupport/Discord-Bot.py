import asyncio
from datetime import datetime, timezone
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from google.oauth2.service_account import Credentials
import gspread

# Импорты из вашего конфига (config.py)
from config import (
    errors,  # ID канала для логирования ошибок
    human_resources,  # ID роли HR / Officer
    rover_token,  # Ваш API-токен RoVer (начинается с rvr2)
)

# ID вашей Google Таблицы
SPREADSHEET_ID = "18v7NrP7-ipz6fBQ84yqvfrsIdfOao0EzUDrRQdokUX4"
ROVER_API_BASE = "https://registry.rover.link/api"


class OfficerStaffCog(commands.Cog):

  def __init__(self, bot: commands.Bot):
    self.bot = bot

  async def _fetch_rover_data(self, guild_id: int, user_id: int) -> dict:
    """Вспомогательный метод для получения данных пользователя из RoVer API."""
    url = f"{ROVER_API_BASE}/guilds/{guild_id}/discord-to-roblox/{user_id}"
    headers = {
        "Authorization": f"Bearer {rover_token}",
        "Accept": "application/json",
    }

    async with aiohttp.ClientSession() as session:
      async with session.get(url, headers=headers) as response:
        if response.status == 200:
          return await response.json()
        elif response.status == 404:
          return None  # Пользователь не найден или скрыт из-за приватности
        else:
          text = await response.text()
          raise Exception(
              f"RoVer API Error [{response.status}]: {text}"
          )

  async def _send_access_request(self, guild_id: int, user_id: int):
    """Отправляет запрос на доступ (DM) пользователю через RoVer API."""
    url = f"{ROVER_API_BASE}/guilds/{guild_id}/access-requests/{user_id}"
    headers = {
        "Authorization": f"Bearer {rover_token}",
        "Content-Type": "application/json",
    }
    
    async with aiohttp.ClientSession() as session:
      async with session.put(url, headers=headers, json={}) as response:
        # 201 Created или 200 OK означают успешную отправку или наличие статуса
        if response.status not in (200, 201):
          text = await response.text()
          print(f"⚠️ Не удалось отправить запрос доступа через RoVer: {text}")

  def _update_google_sheet_row(
      self, roblox_username: str, roblox_id: str, discord_id: str
  ):
    """Синхронно записывает данные в первую свободную строку таблицы (Колонки A, B, C)."""
    try:
      scopes = [
          "https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive",
      ]
      creds = Credentials.from_service_account_file(
          "/etc/secrets/service_account", scopes=scopes
      )
      gc = gspread.authorize(creds)

      sh = gc.open_by_key(SPREADSHEET_ID)
      worksheet = sh.sheet1

      # Находим первую свободную строку по колонке C (Discord ID) или A
      # Либо просто добавляем в конец таблицы через append_row
      cleaned_discord_id = str(discord_id).strip()
      
      # Проверим, вдруг этот дискорд ID уже есть в таблице (колонка C - 3)
      existing_cell = None
      try:
        existing_cell = worksheet.find(cleaned_discord_id, in_column=3)
      except Exception:
        pass

      if existing_cell:
        row = existing_cell.row
        worksheet.update_cell(row, 1, roblox_username)  # Колонка A
        worksheet.update_cell(row, 2, str(roblox_id))   # Колонка B
        print(f"🔄 Обновлена существующая строка {row} для Discord ID {cleaned_discord_id}")
      else:
        # Ищем первую пустую строку или добавляем в конец
        worksheet.append_row([roblox_username, str(roblox_id), cleaned_discord_id])
        print(f"✅ Добавлена новая запись в таблицу для Discord ID {cleaned_discord_id}")

    except Exception as e:
      error_type = type(e).__name__
      error_msg = str(e) or repr(e)
      print(f"🚨 Ошибка Google Таблиц [{error_type}]: {error_msg}")
      raise e

  @app_commands.command(
      name="officer",
      description="Officer management commands",
  )
  @app_commands.describe(member="The member to add/verify")
  async def officer(self, interaction: discord.Interaction, member: discord.Member):
    # Проверка прав: использовать может только роль Human Resources / Officer
    role = interaction.guild.get_role(human_resources)
    if not role or role not in interaction.user.roles:
      await interaction.response.send_message(
          "❌ You do not have permission to use this command.", ephemeral=True
      )
      return

    await interaction.response.defer(ephemeral=True)

    guild_id = interaction.guild.id
    user_id = member.id

    try:
      # 1. Первая попытка получить данные из RoVer
      data = await self._fetch_rover_data(guild_id, user_id)

      # Если данные скрыты из-за приватности (вернулся 404 или пусто)
      if not data or not data.get("robloxId"):
        await interaction.followup.send(
            f"🔒 Данные пользователя {member.mention} скрыты настройками приватности RoVer. "
            f"Отправлен запрос на разрешение доступа в ЛС, ожидайте...",
            ephemeral=True,
        )

        # Отправляем запрос на доступ через RoVer API
        await self._send_access_request(guild_id, user_id)

        # Ждем 1 минуту (60 секунд)
        await asyncio.sleep(60)

        # Повторная проверка после ожидания
        data = await self._fetch_rover_data(guild_id, user_id)

      # Если после повторной проверки данные всё еще недоступны
      if not data or not data.get("robloxId"):
        await interaction.followup.send(
            f"❌ Не удалось получить Roblox-аккаунт пользователя {member.mention}. "
            "Возможно, он не верифицирован в RoVer или проигнорировал запрос доступа в ЛС.",
            ephemeral=True,
        )
        return

      roblox_id = data.get("robloxId")
      # В ответе эндпоинта поле называется cachedUsername
      roblox_username = data.get("cachedUsername", "Unknown")
      discord_id_str = str(user_id)

      # 2. Запись в Google Таблицу (выполняем синхронно в отдельном потоке, чтобы не морозить бота)
      await asyncio.to_thread(
          self._update_google_sheet_row,
          roblox_username,
          roblox_id,
          discord_id_str,
      )

      await interaction.followup.send(
          f"✅ Успешно! Пользователь {member.mention} привязан:\n"
          f"• **Roblox User:** `{roblox_username}`\n"
          f"• **Roblox ID:** `{roblox_id}`\n"
          f"• **Discord ID:** `{discord_id_str}`",
          ephemeral=True,
      )

    except Exception as e:
      # Логируем ошибку в канал ошибок, если он настроен
      error_channel = self.bot.get_channel(errors)
      if error_channel:
        try:
          await error_channel.send(
              f"🚨 **Error in `/officer add` command:**\n```python\n{str(e)}\n```"
          )
        except Exception:
          pass

      await interaction.followup.send(
          f"❌ Произошла ошибка при выполнении команды: `{e}`", ephemeral=True
      )

  @officer.error
  async def officer_error(
      self, interaction: discord.Interaction, error: app_commands.AppCommandError
  ):
    error_channel = self.bot.get_channel(errors)
    if error_channel:
      error_embed = discord.Embed(
          title="⚠️ Command Error",
          description=(
              f"**Command:** `/officer`\n**User:** {interaction.user}"
              f" (`{interaction.user.id}`)\n**Error:** ```python\n{error}\n```"
          ),
          color=discord.Color.red(),
      )
      await error_channel.send(embed=error_embed)
    raise error


async def setup(bot: commands.Bot):
  await bot.add_cog(OfficerStaffCog(bot))
