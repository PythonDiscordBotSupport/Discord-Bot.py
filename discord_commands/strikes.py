import asyncio
from datetime import datetime, timezone
import discord
from discord import app_commands
from discord.ext import commands
from google.oauth2.service_account import Credentials
import gspread

# Импорты из вашего конфига (config.py)
from config import (
    errors,          # ID канала для логирования ошибок
    human_resources,  # ID роли HR
    strike_tracker,   # ID канала для логов страйков
)

# ID вашей Google Таблицы
SPREADSHEET_ID = "18v7NrP7-ipz6fBQ84yqvfrsIdfOao0EzUDrRQdokUX4"


class StrikeCog(commands.Cog):

  def __init__(self, bot: commands.Bot):
    self.bot = bot

  # Создаем единую группу команд /strike
  strike_group = app_commands.Group(name="strike", description="Manage member strikes")

  async def _check_hr_role(self, interaction: discord.Interaction) -> bool:
    """Вспомогательная проверка роли HR"""
    role = interaction.guild.get_role(human_resources)
    if not role or role not in interaction.user.roles:
      await interaction.response.send_message(
          "❌ You do not have permission to use this command.", ephemeral=True
      )
      return False
    return True

  async def _process_strike_update(
      self,
      interaction: discord.Interaction,
      member: discord.Member,
      mode: str,
      reason: str,
      set_value: str = None,
  ):
    """Единая асинхронная логика для таблицы, ЛС и логов"""
    await interaction.response.defer(ephemeral=True)
    user_id_str = str(member.id).strip()

    # Синхронная функция для работы с gspread, которую мы запустим в отдельном потоке
    def update_google_sheet():
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
        return None, None, None

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
      elif mode == "remove":
        if previous_amount == "Removal":
          new_amount = "Strike 2"
        elif previous_amount == "Strike 2":
          new_amount = "Strike 1"
        else:
          new_amount = ""
      else:  # set
        new_amount = set_value if set_value else ""

      # Обновляем колонку J (10)
      worksheet.update_cell(row, 10, new_amount)
      return previous_amount, new_amount, row

    try:
      # Запускаем блокирующий gspread асинхронно через asyncio.to_thread
      previous_amount, new_amount, row = await asyncio.to_thread(update_google_sheet)

      if previous_amount is None:
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

      display_new = new_amount if new_amount != "" else "None"
      display_prev = previous_amount if previous_amount != "" else "None"

      # Определяем стиль логов в зависимости от мода
      if mode == "add":
        title, color, action_text = "⚠️ Strike Added", discord.Color.red(), "added a strike to"
      elif mode == "remove":
        title, color, action_text = "🛡️ Strike Removed", discord.Color.green(), "removed a strike from"
      else:
        title, color, action_text = "⚙️ Strike Status Set", discord.Color.blue(), "set strike status for"

      # Подготавливаем эмбед для логов и ЛС
      embed_data = {
          "title": title,
          "color": color,
          "prev": display_prev,
          "new": display_new,
          "reason": reason
      }

      # Отправка лога в канал strike_tracker и ЛС пользователю параллельно (асинхронно)
      log_channel = self.bot.get_channel(strike_tracker)
      
      async def send_log():
        if log_channel:
          log_embed = discord.Embed(
              title=embed_data["title"],
              color=embed_data["color"],
              timestamp=datetime.now(timezone.utc),
          )
          log_embed.add_field(name="Officer", value=member.mention, inline=False)
          log_embed.add_field(name="Human Resources", value=interaction.user.mention, inline=False)
          log_embed.add_field(name="New Status", value=embed_data["new"], inline=False)
          log_embed.add_field(name="Previous Status", value=embed_data["prev"], inline=False)
          log_embed.add_field(name="Reason", value=embed_data["reason"], inline=False)
          await log_channel.send(embed=log_embed)

      async def send_dm():
        try:
          dm_embed = discord.Embed(
              title=embed_data["title"],
              description=f"Your strike status has been updated in **{interaction.guild.name}**.",
              color=embed_data["color"],
              timestamp=datetime.now(timezone.utc),
          )
          dm_embed.add_field(name="New Status", value=embed_data["new"], inline=False)
          dm_embed.add_field(name="Previous Status", value=embed_data["prev"], inline=False)
          dm_embed.add_field(name="Reason", value=embed_data["reason"], inline=False)
          dm_embed.set_footer(text="Action performed by HR team")
          await member.send(embed=dm_embed)
        except discord.Forbidden:
          pass
        except Exception as dm_error:
          print(f"⚠️ Не удалось отправить ЛС пользователю {member.id}: {dm_error}")

      # Выполняем отправку лога и ЛС одновременно
      await asyncio.gather(send_log(), send_dm())

      msg = f"✅ Successfully {action_text} {member.mention}.\n📊 Previous: `{display_prev}` | New: `{display_new}`"
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
    if not await self._check_hr_role(interaction): return
    await self._process_strike_update(interaction, member, "add", reason)

  @strike_group.command(name="remove", description="Remove a strike from a member")
  @app_commands.describe(member="The member to remove a strike from", reason="Reason for removal")
  async def strike_remove(self, interaction: discord.Interaction, member: discord.Member, reason: str):
    if not await self._check_hr_role(interaction): return
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
    if not await self._check_hr_role(interaction): return
    await self._process_strike_update(interaction, member, "set", reason, set_value=status.value)


async def setup(bot: commands.Bot):
  await bot.add_cog(StrikeCog(bot))
                       
