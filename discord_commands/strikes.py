from datetime import datetime, timezone
import discord
from discord import app_commands
from discord.ext import commands
from google.oauth2.service_account import Credentials
import gspread

# Импорты из вашего конфига (config.py)
from config import (
    errors,  # ID канала для логирования ошибок
)

# ID вашей Google Таблицы
SPREADSHEET_ID = "18v7NrP7-ipz6fBQ84yqvfrsIdfOao0EzUDrRQdokUX4"


class StrikeCog(commands.Cog):

  def __init__(self, bot: commands.Bot):
    self.bot = bot

  # Создаем единую группу команд /strike
  strike_group = app_commands.Group(name="strike", description="Manage member strikes")

  async def _process_strike_update(
      self,
      interaction: discord.Interaction,
      member: discord.Member,
      amount: int,
      mode: str,
      reason: str,
  ):
    """Единая логика для обновления таблицы страйков (колонка J)"""
    await interaction.response.defer(ephemeral=True)
    user_id_str = str(member.id).strip()

    try:
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
              f"⚠️ **Strike Warning:** ID `{user_id_str}` not found in column C!"
          )
        return

      row = cell.row

      # Получаем текущее значение страйков из колонки J (10-я колонка)
      current_strikes_raw = worksheet.cell(row, 10).value
      try:
        previous_amount = int(current_strikes_raw) if current_strikes_raw and str(current_strikes_raw).strip() != "" else 0
      except ValueError:
        previous_amount = 0

      # Вычисляем новое значение в зависимости от команды
      if mode == "add":
        new_amount = previous_amount + amount
        action_text = f" added **{amount}** strike(s) to"
      elif mode == "remove":
        new_amount = max(0, previous_amount - amount)  # Страйки обычно не уходят в минус
        action_text = f" removed **{amount}** strike(s) from"
      else:  # set
        new_amount = amount
        action_text = f" set strikes for"

      # Обновляем ячейку в колонке J
      worksheet.update_cell(row, 10, new_amount)

      if mode == "set":
        msg = f"✅ Successfully set strikes for {member.mention} to **{amount}**.\n📊 Previous: `{previous_amount}` | New: `{new_amount}` | Reason: {reason}"
      else:
        msg = f"✅ Successfully{action_text} {member.mention}.\n📊 Previous: `{previous_amount}` | New: `{new_amount}` | Reason: {reason}"

      await interaction.followup.send(msg, ephemeral=True)

    except Exception as e:
      error_type = type(e).__name__
      error_msg = str(e) or repr(e)
      print(f"🚨 Ошибка Google Таблиц в /strike [{error_type}]: {error_msg}")
      
      error_channel = self.bot.get_channel(errors)
      if error_channel:
        await error_channel.send(
            f"🚨 **Google Sheets Error in Strike Command:**\n"
            f"**Type:** `{error_type}`\n"
            f"**Error:** ```python\n{error_msg}\n```"
        )

      await interaction.followup.send(
          "❌ An error occurred while updating the Google Sheet.", ephemeral=True
      )

  @strike_group.command(name="add", description="Add strikes to a member")
  @app_commands.describe(member="The member who receives strikes", amount="Number of strikes to add", reason="Reason for the strike")
  async def strike_add(self, interaction: discord.Interaction, member: discord.Member, amount: int, reason: str):
    await self._process_strike_update(interaction, member, amount, "add", reason)

  @strike_group.command(name="remove", description="Remove strikes from a member")
  @app_commands.describe(member="The member to remove strikes from", amount="Number of strikes to remove", reason="Reason for removal")
  async def strike_remove(self, interaction: discord.Interaction, member: discord.Member, amount: int, reason: str):
    await self._process_strike_update(interaction, member, amount, "remove", reason)

  @strike_group.command(name="set", description="Set a specific strike amount for a member")
  @app_commands.describe(member="The member to set strikes for", amount="The exact number of strikes", reason="Reason for setting strikes")
  async def strike_set(self, interaction: discord.Interaction, member: discord.Member, amount: int, reason: str):
    await self._process_strike_update(interaction, member, amount, "set", reason)


async def setup(bot: commands.Bot):
  await bot.add_cog(StrikeCog(bot))
