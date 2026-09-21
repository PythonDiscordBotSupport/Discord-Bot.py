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
          return None  # Пользователь не найден или скрыт из-за приватности
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
      self, roblox_username: str, roblox_id: str, discord_id: str
  ) -> str:
    """Проверяет таблицу перед записью и обновляет её при необходимости."""
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
        val_a = worksheet.cell(row, 1).value
        val_b = worksheet.cell(row, 2).value

        # Если имя или ID не заполнены — дозаполняем
        if not val_a or not val_b:
          worksheet.update_cell(row, 1, roblox_username)
          worksheet.update_cell(row, 2, str(roblox_id))
          return "updated"
        else:
          return "filled"
      else:
        # Добавляем новую запись: A = Username, B = Roblox ID, C = Discord ID
        worksheet.append_row(
            [roblox_username, str(roblox_id), cleaned_discord_id]
        )
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
  async def officer(
      self, interaction: discord.Interaction, member: discord.Member
  ):
    # Проверка прав: доступно только роли Human Resources / Officer
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
      # 1. Первый GET-запрос к RoVer
      data = await self._fetch_rover_data(guild_id, user_id)

      # Если данные скрыты из-за приватности (вернулся 404)
      if not data or not data.get("robloxId"):
        await interaction.followup.send(
            f"🔒 Privacy settings prevent viewing {member.mention}'s Roblox"
            " data. An access request has been sent to their DMs, please"
            " wait 1 minute...",
            ephemeral=True,
        )

        # Отправляем PUT-запрос для высылки DM пользователю
        await self._send_access_request(guild_id, user_id)

        # Ожидаем ровно одну минуту
        await asyncio.sleep(60)

        # Повторный GET-запрос после ожидания
        data = await self._fetch_rover_data(guild_id, user_id)

      # 2. Если данные так и не получены (отказ или игнорирование DM)
      if not data or not data.get("robloxId"):
        # Логируем отказ в канал progression красным эмбедом с пингом HR
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

          # Пингуем роль HR в сообщении
          await prog_channel.send(
              content=f"<@&{human_resources}>", embed=fail_embed
          )

        await interaction.followup.send(
            f"❌ {member.mention} refused or failed to provide account access."
            " Incident logged to the progression channel.",
            ephemeral=True,
        )
        return

      # 3. Данные получены успешно
      roblox_id = data.get("robloxId")
      roblox_username = data.get("cachedUsername", "Unknown")

      # Записываем / обновляем в таблице
      sheet_status = await asyncio.to_thread(
          self._check_and_update_google_sheet,
          roblox_username,
          roblox_id,
          discord_id_str,
      )

      # Отправляем зеленый лог-эмбед в progression канал
      if prog_channel:
        success_embed = discord.Embed(
            title="Officers information",
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

        await prog_channel.send(embed=success_embed)

      # Ответ в ЛС/интеракцию вызвавшему команду офицеру
      await interaction.followup.send(
          f"✅ Successfully processed {member.mention} (Status: `{sheet_status}`). "
          "Officers information has been logged to the progression channel.",
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
          f"❌ An error occurred while executing the command: `{e}`",
          ephemeral=True,
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
    
