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
      mode: str,
      reason: str,
      set_value: str = None,
  ):
    """Единая логика для обновления страйков в колонке J"""
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
      current_val_raw = worksheet.cell(row, 10).value
      previous_amount = str(current_val_raw).strip() if current_val_raw and str(current_val_raw).strip() != "" else "None"

      # Логика изменения страйков в колонке J (10)
      if mode == "add":
        if previous_amount in ["None", ""]:
          new_amount = "Strike 1"
        elif previous_amount == "Strike 1":
          new_amount = "Strike 2"
        elif previous_amount == "Strike 2":
          new_amount = "Removal"
        else:
          new_amount = "Removal"
        action_text = f"added a strike to"

      elif mode == "remove":
        if previous_amount == "Removal":
          new_amount = "Strike 2"
        elif previous_amount == "Strike 2":
          new_amount = "Strike 1"
        else:
          new_amount = ""
        action_text = f"removed a strike from"

      else:  # set
        new_amount = set_value if set_value else ""
        action_text = f"set strikes for"

      # Обновляем колонку J (10)
      worksheet.update_cell(row, 10, new_amount)
      display_new = new_amount if new_amount != "" else "None"

      msg = f"✅ Successfully {action_text} {member.mention}.\n📊 Previous: `{previous_amount}` | New: `{display_new}`"
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

  @strike_group.command(name="add", description="Add a strike to a member")
  @app_commands.describe(member="The member to add a strike to", reason="Reason for the strike")
  async def strike_add(self, interaction: discord.Interaction, member: discord.Member, reason: str):
    await self._process_strike_update(interaction, member, "add", reason)

  @strike_group.command(name="remove", description="Remove a strike from a member")
  @app_commands.describe(member="The member to remove a strike from", reason="Reason for removal")
  async def strike_remove(self, interaction: discord.Interaction, member: discord.Member, reason: str):
    await self._process_strike_update(interaction, member, "remove", reason)

  @strike_group.command(name="set", description="Set a specific strike status for a member")
  @app_commands.describe(member="The member to set strikes for", status="Strike status", reason="Reason for setting")
  @app_commands.choices(status=[
      app_commands.Choice(name="None (Clear)", value=""),
      app_commands.Choice(name="Strike 1", value="Strike 1"),
      app_commands.Choice(name="Strike 2", value="Strike 2"),
      app_commands.Choice(name="Removal", value="Removal"),
  ])
  async def strike_set(self, interaction: discord.Interaction, member: discord.Member, status: app_commands.Choice[str], reason: str):
    await self._process_strike_update(interaction, member, "set", reason, set_value=status.value)


async def setup(bot: commands.Bot):
  await bot.add_cog(StrikeCog(bot))
    
