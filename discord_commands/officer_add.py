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
        if response.status not in (200, 201):
          text = await response.text()
          print(f"⚠️ Не удалось отправить запрос доступа через RoVer: {text}")

  def _check_and_update_google_sheet(
      self, roblox_username: str, roblox_id: str, discord_id: str
  ) -> str:
    """
    Проверяет таблицу перед запросом или обновляет её.
    Возвращает статус: 'filled', 'updated' или 'added'.
    """
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

      cleaned_discord_id = str(discord_id).strip()
      
      # Ищем Discord ID в колонке C (индекс 3)
      existing_cell = None
      try:
        existing_cell = worksheet.find(cleaned_discord_id, in_column=3)
      except Exception:
        pass

      if existing_cell:
        row = existing_cell.row
        # Получаем значения ячеек колонки A (1) и B (2) в этой же строке
        val_a = worksheet.cell(row, 1).value
        val_b = worksheet.cell(row, 2).value

        # Если что-то пустое — обновляем
        if not val_a or not val_b:
          worksheet.update_cell(row, 1, roblox_username)
          worksheet.update_cell(row, 2, str(roblox_id))
          return "updated"
        else:
          return "filled"
      else:
        # Если такого Discord ID нет в таблице — добавляем новую строку
        worksheet.append_row([roblox_username, str(roblox_id), cleaned_discord_id])
        return "added"

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
    discord_id_str = str(user_id)

    try:
      # 1. Сначала запрашиваем данные у RoVer (чтобы знать актуальные Roblox данные)
      data = await self._fetch_rover_data(guild_id, user_id)

      # Если данные скрыты из-за приватности (вернулся 404 или пусто)
      if not data or not data.get("robloxId"):
        await interaction.followup.send(
            f"🔒 Privacy settings prevent viewing {member.mention}'s Roblox data. "
            f"An access request has been sent to their DMs, please wait...",
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
            f"❌ Failed to fetch Roblox account for {member.mention}. "
            "They might not be verified in RoVer or ignored the DM access request.",
            ephemeral=True,
        )
        return

      roblox_id = data.get("robloxId")
      roblox_username = data.get("cachedUsername", "Unknown")

      # 2. Проверяем таблицу и записываем/обновляем данные при необходимости (в отдельном потоке)
      sheet_status = await asyncio.to_thread(
          self._check_and_update_google_sheet,
          roblox_username,
          roblox_id,
          discord_id_str,
      )

      if sheet_status == "filled":
        await interaction.followup.send(
            f"ℹ️ User {member.mention} is already fully registered in the spreadsheet:\n"
            f"• **Roblox User:** `{roblox_username}`\n"
            f"• **Roblox ID:** `{roblox_id}`\n"
            f"• **Discord ID:** `{discord_id_str}`",
            ephemeral=True,
        )
      elif sheet_status == "updated":
        await interaction.followup.send(
            f"✅ Existing row for {member.mention} was updated with missing data:\n"
            f"• **Roblox User:** `{roblox_username}`\n"
            f"• **Roblox ID:** `{roblox_id}`\n"
            f"• **Discord ID:** `{discord_id_str}`",
            ephemeral=True,
        )
      else:
        await interaction.followup.send(
            f"✅ Successfully added {member.mention} to the spreadsheet:\n"
            f"• **Roblox User:** `{roblox_username}`\n"
            f"• **Roblox ID:** `{roblox_id}`\n"
            f"• **Discord ID:** `{discord_id_str}`",
            ephemeral=True,
        )

    except Exception as e:
      error_channel = self.bot.get_channel(errors)
      if error_channel:
        try:
          await error_channel.send(
              f"🚨 **Error in `/officer` command:**\n```python\n{str(e)}\n```"
          )
        except Exception:
          pass

      await interaction.followup.send(
          f"❌ An error occurred while executing the command: `{e}`", ephemeral=True
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
