from datetime import datetime, timezone
import discord
from discord import app_commands
from discord.ext import commands
from google.oauth2.service_account import Credentials
import gspread

# Импорты из вашего конфига (config.py)
from config import (
    errors,  # ID канала для логирования ошибок
    human_resources,  # ID роли HR
    progression,  # ID канала для логов прогрессии (экспы)
)

# ID вашей Google Таблицы
SPREADSHEET_ID = "18v7NrP7-ipz6fBQ84yqvfrsIdfOao0EzUDrRQdokUX4"


class XPCog(commands.Cog):

  def __init__(self, bot: commands.Bot):
    self.bot = bot

  # Создаем группу команд /xp
  xp_group = app_commands.Group(name="xp", description="Manage member experience (XP)")

  @xp_group.command(
      name="add",
      description="Add XP to a member and update the Google Sheet",
  )
  @app_commands.describe(
      member="The member who receives XP",
      amount="Amount of XP to add",
      reason="Reason for granting XP",
  )
  async def xp_add(
      self,
      interaction: discord.Interaction,
      member: discord.Member,
      amount: int,
      reason: str,
  ):
    # Проверка роли HR
    role = interaction.guild.get_role(human_resources)
    if not role or role not in interaction.user.roles:
      await interaction.response.send_message(
          "❌ You do not have permission to use this command.", ephemeral=True
      )
      return

    # Откладываем ответ, чтобы избежать тайм-аута при запросе к Google Таблицам
    await interaction.response.defer(ephemeral=True)

    user_id_str = str(member.id).strip()

    try:
      # Подключение к Google Таблицам через Credentials
      scopes = [
          "https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"
      ]
      creds = Credentials.from_service_account_file("/etc/secrets/service_account", scopes=scopes)
      gc = gspread.authorize(creds)
      
      sh = gc.open_by_key(SPREADSHEET_ID)
      worksheet = sh.sheet1

      # Ищем ID пользователя в колонке C
      cell = worksheet.find(user_id_str, in_column=3)

      if not cell:
        await interaction.followup.send(
            f"❌ User ID `{user_id_str}` not found in column C of the Google Sheet.",
            ephemeral=True,
        )
        error_channel = self.bot.get_channel(errors)
        if error_channel:
          await error_channel.send(
              f"⚠️ **XP Warning:** ID `{user_id_str}` not found in column C!"
          )
        return

      row = cell.row

      # Получаем текущее значение из столбца I (9-я колонка)
      current_xp_raw = worksheet.cell(row, 9).value
      try:
        previous_amount = int(current_xp_raw) if current_xp_raw and str(current_xp_raw).strip() != "" else 0
      except ValueError:
        previous_amount = 0

      new_amount = previous_amount + amount

      # Обновляем ячейку в столбце I новым значением
      worksheet.update_cell(row, 9, new_amount)

      # 🟢 Отправка лога в канал progression
      log_channel = self.bot.get_channel(progression)
      if log_channel:
        log_embed = discord.Embed(
            title="📈 XP Added",
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc),
        )
        log_embed.add_field(name="Officer", value=member.mention, inline=False)
        log_embed.add_field(name="Human Resources", value=interaction.user.mention, inline=False)
        log_embed.add_field(name="New Amount", value=str(new_amount), inline=False)
        log_embed.add_field(name="Previous Amount", value=str(previous_amount), inline=False)
        log_embed.add_field(name="Reason", value=reason, inline=False)
        
        await log_channel.send(embed=log_embed)

      await interaction.followup.send(
          f"✅ Successfully added **{amount} XP** to {member.mention}.\n"
          f"📊 Previous: `{previous_amount}` | New: `{new_amount}`",
          ephemeral=True,
      )

    except Exception as e:
      error_type = type(e).__name__
      error_msg = str(e) or repr(e)
      print(f"🚨 Ошибка Google Таблиц в /xp add [{error_type}]: {error_msg}")
      
      error_channel = self.bot.get_channel(errors)
      if error_channel:
        await error_channel.send(
            f"🚨 **Google Sheets Error in XP Add:**\n"
            f"**Type:** `{error_type}`\n"
            f"**Error:** ```python\n{error_msg}\n```"
        )

      await interaction.followup.send(
          "❌ An error occurred while updating the Google Sheet.", ephemeral=True
      )

  @xp_group.command(
      name="remove",
      description="Remove XP from a member and update the Google Sheet",
  )
  @app_commands.describe(
      member="The member to remove XP from",
      amount="Amount of XP to remove",
      reason="Reason for removing XP",
  )
  async def xp_remove(
      self,
      interaction: discord.Interaction,
      member: discord.Member,
      amount: int,
      reason: str,
  ):
    # Проверка роли HR
    role = interaction.guild.get_role(human_resources)
    if not role or role not in interaction.user.roles:
      await interaction.response.send_message(
          "❌ You do not have permission to use this command.", ephemeral=True
      )
      return

    # Откладываем ответ, чтобы избежать тайм-аута при запросе к Google Таблицам
    await interaction.response.defer(ephemeral=True)

    user_id_str = str(member.id).strip()

    try:
      # Подключение к Google Таблицам через Credentials
      scopes = [
          "https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"
      ]
      creds = Credentials.from_service_account_file("/etc/secrets/service_account", scopes=scopes)
      gc = gspread.authorize(creds)
      
      sh = gc.open_by_key(SPREADSHEET_ID)
      worksheet = sh.sheet1

      # Ищем ID пользователя в колонке C
      cell = worksheet.find(user_id_str, in_column=3)

      if not cell:
        await interaction.followup.send(
            f"❌ User ID `{user_id_str}` not found in column C of the Google Sheet.",
            ephemeral=True,
        )
        error_channel = self.bot.get_channel(errors)
        if error_channel:
          await error_channel.send(
              f"⚠️ **XP Warning:** ID `{user_id_str}` not found in column C!"
          )
        return

      row = cell.row

      # Получаем текущее значение из столбца I (9-я колонка)
      current_xp_raw = worksheet.cell(row, 9).value
      try:
        previous_amount = int(current_xp_raw) if current_xp_raw and str(current_xp_raw).strip() != "" else 0
      except ValueError:
        previous_amount = 0

      # Вычитаем XP (может уйти в минус без ограничений)
      new_amount = previous_amount - amount

      # Обновляем ячейку в столбце I новым значением
      worksheet.update_cell(row, 9, new_amount)

      # 🔴 Отправка лога в канал progression (красный цвет для удаления)
      log_channel = self.bot.get_channel(progression)
      if log_channel:
        log_embed = discord.Embed(
            title="📉 XP Removed",
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc),
        )
        log_embed.add_field(name="Officer", value=member.mention, inline=False)
        log_embed.add_field(name="Human Resources", value=interaction.user.mention, inline=False)
        log_embed.add_field(name="New Amount", value=str(new_amount), inline=False)
        log_embed.add_field(name="Previous Amount", value=str(previous_amount), inline=False)
        log_embed.add_field(name="Reason", value=reason, inline=False)
        
        await log_channel.send(embed=log_embed)

      await interaction.followup.send(
          f"✅ Successfully removed **{amount} XP** from {member.mention}.\n"
          f"📊 Previous: `{previous_amount}` | New: `{new_amount}`",
          ephemeral=True,
      )

    except Exception as e:
      error_type = type(e).__name__
      error_msg = str(e) or repr(e)
      print(f"🚨 Ошибка Google Таблиц в /xp remove [{error_type}]: {error_msg}")
      
      error_channel = self.bot.get_channel(errors)
      if error_channel:
        await error_channel.send(
            f"🚨 **Google Sheets Error in XP Remove:**\n"
            f"**Type:** `{error_type}`\n"
            f"**Error:** ```python\n{error_msg}\n```"
        )

      await interaction.followup.send(
          "❌ An error occurred while updating the Google Sheet.", ephemeral=True
      )


async def setup(bot: commands.Bot):
  await bot.add_cog(XPCog2(bot))
      
