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
    progression,  # ID канала для логов прогрессии/офицеров
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
          return None  # Пользователь не найден или скрыт
        else:
          text = await response.text()
          raise Exception(f"RoVer API Error [{response.status}]: {text}")

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
      self, roblox_username: str, roblox_id: str, discord_id: str, department: str
  ) -> str:
    """Проверяет таблицу: ищет существующий Discord ID, либо первую пустую строку сверху вниз.

    Заполняет колонки от A до G (A-B: Roblox, C: Discord, G: Department).
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

      # 1. Ищем, вдруг этот Discord ID уже есть в таблице (колонка C)
      existing_cell = None
      try:
        existing_cell = worksheet.find(cleaned_discord_id, in_column=3)
      except Exception:
        pass

      if existing_cell:
        row = existing_cell.row
        val_a = worksheet.cell(row, 1).value
        val_b = worksheet.cell(row, 2).value

        # Обновляем базовые данные и департамент (колонка G)
        worksheet.update_cell(row, 1, roblox_username)
        worksheet.update_cell(row, 2, str(roblox_id))
        worksheet.update_cell(row, 7, department)  # Столбец G
        return "updated"

      # 2. Поиск первой пустой строки в столбце А сверху вниз
      col_values = worksheet.col_values(1)
      target_row = len(col_values) + 1

      for index, val in enumerate(col_values):
        if not val or not str(val).strip():
          target_row = index + 1
          break

      # Записываем данные: A (Username), B (Roblox ID), C (Discord ID), G (Department)
      # Для безопасности и корректности диапазонов обновим ячейки точечно или пакетом
      worksheet.update_cell(target_row, 1, roblox_username)
      worksheet.update_cell(target_row, 2, str(roblox_id))
      worksheet.update_cell(target_row, 3, cleaned_discord_id)
      worksheet.update_cell(target_row, 7, department)  # Столбец G

      return f"added (row {target_row})"

    except Exception as e:
      error_type = type(e).__name__
      error_msg = str(e) or repr(e)
      print(f"🚨 Ошибка Google Таблиц [{error_type}]: {error_msg}")
      raise e

  def _clear_google_sheet_row(self, discord_id: str) -> tuple[bool, str, str]:
    """Ищет Discord ID в колонке C, очищает данные с A по J (колонка D ставит FALSE),

    возвращает (found, roblox_username, roblox_id).
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
      existing_cell = None
      try:
        existing_cell = worksheet.find(cleaned_discord_id, in_column=3)
      except Exception:
        pass

      if not existing_cell:
        return False, "Unknown", "Unknown"

      row = existing_cell.row
      roblox_username = worksheet.cell(row, 1).value or "Unknown"
      roblox_id = worksheet.cell(row, 2).value or "Unknown"

      # Формируем список значений для очистки (A по J)
      # Колонка D (индекс 3 в 0-based) должна содержать FALSE
      row_data = ["", "", "", False, "", "", "", "", "", ""]
      worksheet.update(f"A{row}:J{row}", [row_data])

      return True, roblox_username, roblox_id

    except Exception as e:
      error_type = type(e).__name__
      error_msg = str(e) or repr(e)
      print(f"🚨 Ошибка Google Таблиц при удалении [{error_type}]: {error_msg}")
      raise e

  # Создаем групповую команду /officer
  officer_group = app_commands.Group(
      name="officer", description="Officer management commands"
  )

  @officer_group.command(
      name="add", description="Register and verify an officer"
  )
  @app_commands.describe(
      member="The member to add/verify",
      department="Select the department",
      reason="Reason for adding",
  )
  @app_commands.choices(
      department=[
          app_commands.Choice(name="SIS", value="SIS"),
          app_commands.Choice(name="FO", value="FO"),
          app_commands.Choice(name="RAS", value="RAS"),
          app_commands.Choice(name="CMD", value="CMD"),
      ]
  )
  async def officer_add(
      self,
      interaction: discord.Interaction,
      member: discord.Member,
      department: app_commands.Choice[str],
      reason: str,
  ):
    # Проверка прав HR / Officer
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
    prog_channel = self.bot.get_channel(progression)

    try:
      # 1. Получение данных из RoVer API
      data = await self._fetch_rover_data(guild_id, user_id)

      if not data or not data.get("robloxId"):
        await interaction.followup.send(
            f"🔒 Privacy settings prevent viewing {member.mention}'s Roblox"
            " data. An access request has been sent to their DMs, please"
            " wait 1 minute...",
            ephemeral=True,
        )
        await self._send_access_request(guild_id, user_id)
        await asyncio.sleep(60)
        data = await self._fetch_rover_data(guild_id, user_id)

      if not data or not data.get("robloxId"):
        if prog_channel:
          fail_embed = discord.Embed(
              title="❌ Officer Verification Refused",
              description=(
                  f"{member.mention} (`{discord_id_str}`) refused or failed"
                  " to provide read permissions for their Roblox account."
              ),
              color=discord.Color.red(),
              timestamp=datetime.now(timezone.utc),
          )
          fail_embed.add_field(
              name="Discord Mention", value=member.mention, inline=True
          )
          fail_embed.add_field(
              name="Discord ID", value=f"`{discord_id_str}`", inline=True
          )
          fail_embed.add_field(
              name="Human Resources",
              value=interaction.user.mention,
              inline=False,
          )
          await prog_channel.send(
              content=f"<@&{human_resources}>", embed=fail_embed
          )

        await interaction.followup.send(
            f"❌ {member.mention} refused or failed to provide account access.",
            ephemeral=True,
        )
        return

      roblox_id = data.get("robloxId")
      roblox_username = data.get("cachedUsername", "Unknown")

      # Запись в Google Таблицу
      sheet_status = await asyncio.to_thread(
          self._check_and_update_google_sheet,
          roblox_username,
          roblox_id,
          discord_id_str,
          department.value,
      )

      # Отправка лога в progression канал
      if prog_channel:
        success_embed = discord.Embed(
            title="Officer Registration",
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc),
        )
        success_embed.add_field(
            name="Roblox Username", value=f"`{roblox_username}`", inline=True
        )
        success_embed.add_field(
            name="Roblox ID", value=f"`{roblox_id}`", inline=True
        )
        success_embed.add_field(
            name="Discord Mention", value=member.mention, inline=True
        )
        success_embed.add_field(
            name="Discord ID", value=f"`{discord_id_str}`", inline=True
        )
        success_embed.add_field(
            name="Human Resources",
            value=interaction.user.mention,
            inline=False,
        )
        success_embed.add_field(name="Reason", value=reason, inline=False)

        await prog_channel.send(embed=success_embed)

      await interaction.followup.send(
          f"✅ Successfully processed {member.mention} (Status: `{sheet_status}`). "
          "Information has been logged.",
          ephemeral=True,
      )

    except Exception as e:
      error_channel = self.bot.get_channel(errors)
      if error_channel:
        try:
          await error_channel.send(
              f"🚨 **Error in `/officer add` command:**\n```python\n{str(e)}\n```"
          )
        except Exception:
          pass
      await interaction.followup.send(
          f"❌ An error occurred while executing the command: `{e}`",
          ephemeral=True,
      )

  @officer_group.command(
      name="remove", description="Remove and clear an officer's data"
  )
  @app_commands.describe(
      member="The member to remove", reason="Reason for removal"
  )
  async def officer_remove(
      self, interaction: discord.Interaction, member: discord.Member, reason: str
  ):
    # Проверка прав HR / Officer
    role = interaction.guild.get_role(human_resources)
    if not role or role not in interaction.user.roles:
      await interaction.response.send_message(
          "❌ You do not have permission to use this command.", ephemeral=True
      )
      return

    await interaction.response.defer(ephemeral=True)

    discord_id_str = str(member.id)
    prog_channel = self.bot.get_channel(progression)

    try:
      # Очищаем строку в таблице (A-J, колонка D = FALSE)
      found, roblox_username, roblox_id = await asyncio.to_thread(
          self._clear_google_sheet_row, discord_id_str
      )

      if not found:
        await interaction.followup.send(
            f"⚠️ Could not find a record associated with {member.mention}"
            " (`{discord_id_str}`) in the spreadsheet.",
            ephemeral=True,
        )
        return

      # Отправляем лог в progression канал
      if prog_channel:
        remove_embed = discord.Embed(
            title="Officer Removal",
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc),
        )
        remove_embed.add_field(
            name="Roblox Username", value=f"`{roblox_username}`", inline=True
        )
        remove_embed.add_field(
            name="Roblox ID", value=f"`{roblox_id}`", inline=True
        )
        remove_embed.add_field(
            name="Discord Mention", value=member.mention, inline=True
        )
        remove_embed.add_field(
            name="Discord ID", value=f"`{discord_id_str}`", inline=True
        )
        remove_embed.add_field(
            name="Human Resources",
            value=interaction.user.mention,
            inline=False,
        )
        remove_embed.add_field(name="Reason", value=reason, inline=False)

        await prog_channel.send(embed=remove_embed)

      await interaction.followup.send(
          f"✅ Successfully removed {member.mention}'s data from the spreadsheet"
          " and logged the action.",
          ephemeral=True,
      )

    except Exception as e:
      error_channel = self.bot.get_channel(errors)
      if error_channel:
        try:
          await error_channel.send(
              f"🚨 **Error in `/officer remove` command:**\n```python\n{str(e)}\n```"
          )
        except Exception:
          pass
      await interaction.followup.send(
          f"❌ An error occurred while executing the command: `{e}`",
          ephemeral=True,
      )

  @officer_group.error
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
    
