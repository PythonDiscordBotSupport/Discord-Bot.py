from datetime import datetime, time, timezone
import discord
from discord import app_commands
from discord.ext import commands, tasks
from google.oauth2.service_account import Credentials
import gspread

# Импорты из вашего конфига (config.py)
from config import (
    errors,  # ID канала для логирования ошибок
    human_resources,  # ID роли HR
    loa_apps_channel_id,  # ID канала для заявок
    loa_logs_channel_id,  # ID канала для логов окончания LOA
)

# ID вашей Google Таблицы
SPREADSHEET_ID = "18v7NrP7-ipz6fBQ84yqvfrsIdfOao0EzUDrRQdokUX4"


class LOAView(discord.ui.View):

  def __init__(
      self,
      user: discord.User,
      start_date: str,
      end_date: str,
      duration: int,
      reason: str,
  ):
    super().__init__(timeout=None)
    self.user = user
    self.start_date = start_date
    self.end_date = end_date
    self.duration = duration
    self.reason = reason

  async def interaction_check(self, interaction: discord.Interaction) -> bool:
    role = interaction.guild.get_role(human_resources)
    if role and role in interaction.user.roles:
      return True
    await interaction.response.send_message(
        "❌ You do not have permission to use this button.", ephemeral=True
    )
    return False

  @discord.ui.button(
      label="Accept", style=discord.ButtonStyle.green, custom_id="loa_accept"
  )
  async def accept_callback(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    # Предотвращаем таймаут интеракции (ошибка 10062)
    await interaction.response.defer(ephemeral=True)

    try:
      await self.user.send(
          f"Your LOA request ({self.start_date} - {self.end_date}) has been"
          " **approved**!"
      )
    except discord.Forbidden:
      pass

    # Обновляем Google Таблицу через Credentials
    await self.update_google_sheet(
        interaction, str(self.user.id), f"{self.start_date} - {self.end_date}"
    )

    for child in self.children:
      child.disabled = True
    embed = interaction.message.embeds[0]
    embed.color = discord.Color.green()
    embed.add_field(
        name="Status", value=f"Approved by {interaction.user.mention}", inline=False
    )

    await interaction.message.edit(embed=embed, view=self)

    # 🟢 Отправка лога об ОДОБРЕНИИ в лог-канал
    log_channel = interaction.client.get_channel(loa_logs_channel_id)
    if log_channel:
      log_embed = discord.Embed(
          title="✅ LOA Request Approved",
          color=discord.Color.green(),
          timestamp=datetime.now(timezone.utc),
      )
      log_embed.add_field(name="User", value=self.user.mention, inline=True)
      log_embed.add_field(name="Reviewer (HR)", value=interaction.user.mention, inline=True)
      log_embed.add_field(name="Period", value=f"{self.start_date} - {self.end_date} ({self.duration} days)", inline=False)
      log_embed.add_field(name="Reason", value=self.reason, inline=False)
      await log_channel.send(embed=log_embed)
    
    await interaction.followup.send(
        "✅ Request successfully accepted.", ephemeral=True
    )

  @discord.ui.button(
      label="Deny", style=discord.ButtonStyle.red, custom_id="loa_deny"
  )
  async def deny_callback(
      self, interaction: discord.Interaction, button: discord.ui.Button
  ):
    # Предотвращаем таймаут интеракции (ошибка 10062)
    await interaction.response.defer(ephemeral=True)

    try:
      await self.user.send(
          f"Your LOA request ({self.start_date} - {self.end_date}) has been"
          " **denied**."
      )
    except discord.Forbidden:
      pass

    for child in self.children:
      child.disabled = True
    embed = interaction.message.embeds[0]
    embed.color = discord.Color.red()
    embed.add_field(
        name="Status", value=f"Denied by {interaction.user.mention}", inline=False
    )

    await interaction.message.edit(embed=embed, view=self)

    # 🔴 Отправка лога об ОТКЛОНЕНИИ в лог-канал
    log_channel = interaction.client.get_channel(loa_logs_channel_id)
    if log_channel:
      log_embed = discord.Embed(
          title="❌ LOA Request Denied",
          color=discord.Color.red(),
          timestamp=datetime.now(timezone.utc),
      )
      log_embed.add_field(name="User", value=self.user.mention, inline=True)
      log_embed.add_field(name="Reviewer (HR)", value=interaction.user.mention, inline=True)
      log_embed.add_field(name="Period", value=f"{self.start_date} - {self.end_date} ({self.duration} days)", inline=False)
      log_embed.add_field(name="Reason", value=self.reason, inline=False)
      await log_channel.send(embed=log_embed)
    
    await interaction.followup.send(
        "❌ Request denied.", ephemeral=True
    )

  async def update_google_sheet(self, interaction: discord.Interaction, user_id: str, date_range: str):
    """Обновление таблицы через Credentials для обхода PermissionError на Render"""
    try:
      scopes = [
          "https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"
      ]
      
      creds = Credentials.from_service_account_file("/etc/secrets/service_account", scopes=scopes)
      gc = gspread.authorize(creds)
      
      sh = gc.open_by_key(SPREADSHEET_ID)
      worksheet = sh.sheet1

      cleaned_user_id = str(user_id).strip()
      cell = worksheet.find(cleaned_user_id, in_column=3)
      
      if cell:
        row = cell.row
        worksheet.update_cell(row, 4, True)  # Столбец D - True (чекбокс)
        worksheet.update_cell(row, 5, date_range)  # Столбец E - даты
        print(f"✅ Успешно обновлена строка {row} для ID {cleaned_user_id}")
      else:
        print(f"❌ ID '{cleaned_user_id}' не найден в колонке C.")
        error_channel = interaction.client.get_channel(errors)
        if error_channel:
          all_ids = worksheet.col_values(3)
          await error_channel.send(
              f"⚠️ **LOA Warning:** ID `{cleaned_user_id}` не найден в колонке C!\n"
              f"📋 Список ID в таблице: `{all_ids}`"
          )
        
    except Exception as e:
      error_type = type(e).__name__
      error_msg = str(e) or repr(e)
      print(f"🚨 Ошибка Google Таблиц [{error_type}]: {error_msg}")
      
      error_channel = interaction.client.get_channel(errors)
      if error_channel:
        await error_channel.send(
            f"🚨 **Google Sheets Error in LOA:**\n"
            f"**Type:** `{error_type}`\n"
            f"**Error:** ```python\n{error_msg}\n```"
        )


class LOACog(commands.Cog):

  def __init__(self, bot: commands.Bot):
    self.bot = bot
    self.check_loa_expiry.start()

  def cog_unload(self):
    self.check_loa_expiry.cancel()

  @app_commands.command(
      name="loa",
      description=(
          "Submit a Leave of Absence (LOA) request (Date format: dd.mm)"
      ),
  )
  @app_commands.describe(
      start_date="Start date in dd.mm format",
      end_date="End date in dd.mm format",
      reason="Reason for your request",
  )
  async def loa(
      self,
      interaction: discord.Interaction,
      start_date: str,
      end_date: str,
      reason: str,
  ):
    # Time safety check (1 hour before 12:00 UTC and 00:00 UTC)
    now_utc = datetime.now(timezone.utc)
    hour = now_utc.hour

    if hour == 11 or hour == 23:
      await interaction.response.send_message(
          "⚠️ This command is temporarily unavailable (safety lock 1 hour"
          " before restart at 12:00 / 00:00 UTC). Please try again later.",
          ephemeral=True,
      )
      return

    # Parse dates and calculate duration
    try:
      current_year = now_utc.year
      d1 = datetime.strptime(f"{start_date}.{current_year}", "%d.%m.%Y")
      d2 = datetime.strptime(f"{end_date}.{current_year}", "%d.%m.%Y")

      duration = (d2 - d1).days
      if duration < 0:
        d2 = datetime.strptime(f"{end_date}.{current_year + 1}", "%d.%m.%Y")
        duration = (d2 - d1).days

      if duration < 0:
        raise ValueError

    except ValueError:
      await interaction.response.send_message(
          "❌ Invalid date format or interval. Please use `dd.mm` format (e.g.,"
          " `15.06`).",
          ephemeral=True,
      )
      return

    channel = self.bot.get_channel(loa_apps_channel_id)
    if not channel:
      await interaction.response.send_message(
          "❌ LOA applications channel is not configured.", ephemeral=True
      )
      return

    embed = discord.Embed(
        title="New LOA Request", color=discord.Color.blue(), timestamp=now_utc
    )
    embed.add_field(name="User", value=interaction.user.mention, inline=False)
    embed.add_field(name="User ID", value=str(interaction.user.id), inline=False)
    embed.add_field(name="Start Date", value=start_date, inline=True)
    embed.add_field(name="End Date", value=end_date, inline=True)
    embed.add_field(name="Duration", value=f"{duration} days", inline=True)
    embed.add_field(name="Reason", value=reason, inline=False)

    view = LOAView(
        user=interaction.user,
        start_date=start_date,
        end_date=end_date,
        duration=duration,
        reason=reason,
    )

    await channel.send(embed=embed, view=view)
    await interaction.response.send_message(
        "✅ Your LOA request has been successfully submitted for review!",
        ephemeral=True,
    )

  # Background task runs strictly at 13:00 UTC every day
  @tasks.loop(time=time(hour=13, minute=0, tzinfo=timezone.utc))
  async def check_loa_expiry(self):
    today_str = datetime.now(timezone.utc).strftime("%d.%m")

    try:
      scopes = [
          "https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive"
      ]
      creds = Credentials.from_service_account_file("/etc/secrets/service_account", scopes=scopes)
      gc = gspread.authorize(creds)
      
      sh = gc.open_by_key(SPREADSHEET_ID)
      worksheet = sh.sheet1
      rows = worksheet.get_all_values()

      for row in rows[1:]:
        if len(row) >= 5:
          user_id = row[2].strip()
          is_active = str(row[3]).strip().lower() == "true"
          dates_str = row[4].strip()

          if is_active and dates_str:
            parts = dates_str.split("-")
            if len(parts) == 2:
              end_date_part = parts[1].strip()

              if end_date_part == today_str:
                try:
                  user = await self.bot.fetch_user(int(user_id))
                  if user:
                    await user.send(
                        "⏰ Your LOA period expires today! Welcome back."
                    )
                except Exception:
                  pass

                log_channel = self.bot.get_channel(loa_logs_channel_id)
                if log_channel:
                  await log_channel.send(
                      f"<@1485230165830402168> User <@{user_id}> LOA ends today"
                      f" ({dates_str})."
                  )
    except Exception as e:
      print(f"Error in check_loa_expiry task: {e}")

  @check_loa_expiry.before_loop
  async def before_check_loa_expiry(self):
    await self.bot.wait_until_ready()

  @loa.error
  async def loa_error(
      self, interaction: discord.Interaction, error: app_commands.AppCommandError
  ):
    error_channel = self.bot.get_channel(errors)
    if error_channel:
      error_embed = discord.Embed(
          title="⚠️ Command Error",
          description=(
              f"**Command:** `/loa`\n**User:** {interaction.user}"
              f" (`{interaction.user.id}`)\n**Error:** ```python\n{error}\n```"
          ),
          color=discord.Color.red(),
      )
      await error_channel.send(embed=error_embed)
    raise error


async def setup(bot: commands.Bot):
  await bot.add_cog(LOACog(bot))
          
