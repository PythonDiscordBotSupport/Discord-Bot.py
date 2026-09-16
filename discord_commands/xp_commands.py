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

  # Создаем единую группу команд /xp
  xp_group = app_commands.Group(name="xp", description="Manage member experience (XP)")

  async def _check_hr_role(self, interaction: discord.Interaction) -> bool:
    """Вспомогательная проверка роли HR"""
    role = interaction.guild.get_role(human_resources)
    if not role or role not in interaction.user.roles:
      await interaction.response.send_message(
          "❌ You do not have permission to use this command.", ephemeral=True
      )
      return False
    return True

  async def _process_xp_update(
      self,
      interaction: discord.Interaction,
      member: discord.Member,
      amount: int,
      mode: str,
      reason: str,
  ):
    """Единая логика для обновления таблицы и отправки логов"""
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
              f"⚠️ **XP Warning:** ID `{user_id_str}` not found in column C!"
          )
        return

      row = cell.row

      current_xp_raw = worksheet.cell(row, 9).value
      try:
        previous_amount = int(current_xp_raw) if current_xp_raw and str(current_xp_raw).strip() != "" else 0
      except ValueError:
        previous_amount = 0

      # Вычисляем новое значение в зависимости от команды
      if mode == "add":
        new_amount = previous_amount + amount
        title, color, action_text = "📈 XP Added", discord.Color.green(), f" added **{amount} XP** to"
      elif mode == "remove":
        new_amount = previous_amount - amount
        title, color, action_text = "📉 XP Removed", discord.Color.red(), f" removed **{amount} XP** from"
      else:  # set
        new_amount = amount
        title, color, action_text = "⚙️ XP Set", discord.Color.blue(), f" set XP for"

      worksheet.update_cell(row, 9, new_amount)

      # Отправка лога в канал progression
      log_channel = self.bot.get_channel(progression)
      if log_channel:
        log_embed = discord.Embed(
            title=title,
            color=color,
            timestamp=datetime.now(timezone.utc),
        )
        log_embed.add_field(name="Officer", value=member.mention, inline=False)
        log_embed.add_field(name="Human Resources", value=interaction.user.mention, inline=False)
        log_embed.add_field(name="New Amount", value=str(new_amount), inline=False)
        log_embed.add_field(name="Previous Amount", value=str(previous_amount), inline=False)
        log_embed.add_field(name="Reason", value=reason, inline=False)
        
        await log_channel.send(embed=log_embed)

      msg = f"✅ Successfully{action_text} {member.mention}.\n📊 Previous: `{previous_amount}` | New: `{new_amount}`"
      if mode == "set":
        msg = f"✅ Successfully set XP for {member.mention} to **{amount}**.\n📊 Previous: `{previous_amount}` | New: `{new_amount}`"

      await interaction.followup.send(msg, ephemeral=True)

    except Exception as e:
      error_type = type(e).__name__
      error_msg = str(e) or repr(e)
      print(f"🚨 Ошибка Google Таблиц в /xp [{error_type}]: {error_msg}")
      
      error_channel = self.bot.get_channel(errors)
      if error_channel:
        await error_channel.send(
            f"🚨 **Google Sheets Error in XP Command:**\n"
            f"**Type:** `{error_type}`\n"
            f"**Error:** ```python\n{error_msg}\n```"
        )

      await interaction.followup.send(
          "❌ An error occurred while updating the Google Sheet.", ephemeral=True
      )

  @xp_group.command(name="add", description="Add XP to a member")
  @app_commands.describe(member="The member who receives XP", amount="Amount of XP to add", reason="Reason for granting XP")
  async def xp_add(self, interaction: discord.Interaction, member: discord.Member, amount: int, reason: str):
    if not await self._check_hr_role(interaction): return
    await self._process_xp_update(interaction, member, amount, "add", reason)

  @xp_group.command(name="remove", description="Remove XP from a member")
  @app_commands.describe(member="The member to remove XP from", amount="Amount of XP to remove", reason="Reason for removing XP")
  async def xp_remove(self, interaction: discord.Interaction, member: discord.Member, amount: int, reason: str):
    if not await self._check_hr_role(interaction): return
    await self._process_xp_update(interaction, member, amount, "remove", reason)

  @xp_group.command(name="set", description="Set a specific XP amount for a member")
  @app_commands.describe(member="The member to set XP for", amount="The exact amount of XP to set", reason="Reason for setting XP")
  async def xp_set(self, interaction: discord.Interaction, member: discord.Member, amount: int, reason: str):
    if not await self._check_hr_role(interaction): return
    await self._process_xp_update(interaction, member, amount, "set", reason)


async def setup(bot: commands.Bot):
  await bot.add_cog(XPCog(bot))
        
