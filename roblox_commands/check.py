import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

# Импортируем ID группы и канала ошибок из конфига
from config import errors, group_id

# Импортируем структуры ролей из файла group_roles.py
from group_roles import complete_roles, immutable_roles, operational_roles


class CheckCommand(commands.Cog):
  # Оставляем только красный для ошибок логов
  COLOR_RED = discord.Color.red()

  def __init__(self, bot: commands.Bot):
    self.bot = bot

  async def _log_error_to_channel(self, error_message: str):
    if not errors:
      return
    channel = self.bot.get_channel(errors)
    if channel:
      embed_log = discord.Embed(
          title="🚨 Check Command Error Log",
          description=error_message,
          color=self.COLOR_RED,
      )
      embed_log.timestamp = discord.utils.utcnow()
      try:
        await channel.send(embed=embed_log)
      except Exception:
        pass

  async def _get_user_id_by_username(self, username: str) -> int | None:
    url = "https://users.roblox.com/v1/usernames/users"
    payload = {"usernames": [username], "excludeBannedUsers": True}
    async with aiohttp.ClientSession() as session:
      async with session.post(url, json=payload) as resp:
        if resp.status == 200:
          data = await resp.json()
          users = data.get("data", [])
          if users:
            return users[0].get("id")
    return None

  async def _get_username_by_user_id(self, user_id: int) -> str | None:
    url = f"https://users.roblox.com/v1/users/{user_id}"
    async with aiohttp.ClientSession() as session:
      async with session.get(url) as resp:
        if resp.status == 200:
          data = await resp.json()
          return data.get("name")
    return None

  async def _get_user_group_role(self, user_id: int) -> tuple[str, int]:
    url = f"https://groups.roblox.com/v1/users/{user_id}/groups/roles"
    async with aiohttp.ClientSession() as session:
      async with session.get(url) as resp:
        if resp.status == 200:
          data = await resp.json()
          for group in data.get("data", []):
            if group.get("group", {}).get("id") == group_id:
              role_data = group.get("role", {})
              return role_data.get("name", "Guest"), role_data.get(
                  "id", 82396917
              )
    return "Guest", 82396917

  @app_commands.command(
      name="check",
      description=(
          "Checks a Roblox user's rank and role in the group by username or ID"
      ),
  )
  @app_commands.describe(
      query=(
          "Roblox Username (string) or User ID (number/string containing"
          " numbers)"
      )
  )
  async def check(self, interaction: discord.Interaction, query: str):
    await interaction.response.defer(thinking=True)

    user_id = None
    username = None

    if query.isdigit():
      user_id = int(query)
      username = await self._get_username_by_user_id(user_id)
      if not username:
        error_desc = f"User with ID `{user_id}` not found on Roblox."
        await self._log_error_to_channel(
            f"**Command:** `/check`\n**Query:** `{query}`\n**Reason:**"
            f" {error_desc}"
        )
        embed_err = discord.Embed(
            title="❌ Error", description=error_desc, color=self.COLOR_RED
        )
        await interaction.followup.send(embed=embed_err)
        return
    else:
      username = query.strip()
      user_id = await self._get_user_id_by_username(username)
      if not user_id:
        error_desc = f"Roblox user `{username}` not found."
        await self._log_error_to_channel(
            f"**Command:** `/check`\n**Query:** `{query}`\n**Reason:**"
            f" {error_desc}"
        )
        embed_err = discord.Embed(
            title="❌ Error", description=error_desc, color=self.COLOR_RED
        )
        await interaction.followup.send(embed=embed_err)
        return

    roblox_role_name, roblox_role_id = await self._get_user_group_role(user_id)

    matched_role_name = "Guest"
    for role_name, data in complete_roles.items():
      if data["role_id"] == roblox_role_id:
        matched_role_name = role_name
        break

    if matched_role_name == "Guest":
      role_status = "Guest"
    elif matched_role_name in immutable_roles:
      role_status = "Immutable Role"
    else:
      role_status = "Operational Role"

    embed = discord.Embed(
        title="🔍 Roblox User Verification",
        description=(
            f"• **Username:** `{username}`\n"
            f"• **User ID:** `{user_id}`\n"
            f"• **Rank:** `{matched_role_name}`\n"
            f"• **Status:** `{role_status}`"
        ),
        color=discord.Color.random(),  # Теперь цвет будет каждый раз случайным!
    )

    embed.set_footer(text=f"Requested by {interaction.user.name}")
    embed.timestamp = discord.utils.utcnow()

    await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
  await bot.add_cog(CheckCommand(bot))
        
