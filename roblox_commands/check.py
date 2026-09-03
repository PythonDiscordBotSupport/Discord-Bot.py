import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

# Импортируем готовые структуры ролей из отдельного файла
from group_roles import complete_roles, immutable_roles, operational_roles


class CheckCommand(commands.Cog):
  # Цветовая палитра под ваш стиль
  COLOR_ORANGE = discord.Color.from_str("#e8b53f")
  COLOR_RED = discord.Color.from_str("#b81f24")

  def __init__(self, bot: commands.Bot):
    self.bot = bot
    self.group_id = 14543769

  async def _get_user_id_by_username(self, username: str) -> int | None:
    """Конвертирует никнейм Roblox в UserId через публичный API"""
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
    """Получает никнейм пользователя по его UserId"""
    url = f"https://users.roblox.com/v1/users/{user_id}"
    async with aiohttp.ClientSession() as session:
      async with session.get(url) as resp:
        if resp.status == 200:
          data = await resp.json()
          return data.get("name")
    return None

  async def _get_user_group_role(self, user_id: int) -> tuple[str, int]:
    """Запрашивает роль пользователя в целевой группе по API"""
    url = f"https://groups.roblox.com/v1/users/{user_id}/groups/roles"
    async with aiohttp.ClientSession() as session:
      async with session.get(url) as resp:
        if resp.status == 200:
          data = await resp.json()
          for group in data.get("data", []):
            if group.get("group", {}).get("id") == self.group_id:
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

    # Определяем, передали ли нам числовой ID или строковый ник
    if query.isdigit():
      user_id = int(query)
      username = await self._get_username_by_user_id(user_id)
      if not username:
        embed_err = discord.Embed(
            title="❌ Error",
            description=f"User with ID `{user_id}` not found on Roblox.",
            color=self.COLOR_RED,
        )
        await interaction.followup.send(embed=embed_err)
        return
    else:
      username = query.strip()
      user_id = await self._get_user_id_by_username(username)
      if not user_id:
        embed_err = discord.Embed(
            title="❌ Error",
            description=f"Roblox user `{username}` not found.",
            color=self.COLOR_RED,
        )
        await interaction.followup.send(embed=embed_err)
        return

    # Получаем роль игрока в группе
    roblox_role_name, roblox_role_id = await self._get_user_group_role(user_id)

    # Ищем чистое название роли в complete_roles по role_id
    matched_role_name = "Guest"
    for role_name, data in complete_roles.items():
      if data["role_id"] == roblox_role_id:
        matched_role_name = role_name
        break

    # Определяем статус роли (Immutable или Operational)
    if matched_role_name in immutable_roles:
      role_status = "Immutable Role"
    else:
      role_status = "Operational Role"

    # Формируем пастельно-оранжевый эмбед
    embed = discord.Embed(
        title="🔍 Roblox User Verification",
        description=(
            f"• **Username:** `{username}`\n"
            f"• **User ID:** `{user_id}`\n"
            f"• **Rank:** `{matched_role_name}`\n"
            f"• **Status:** `{role_status}`"
        ),
        color=self.COLOR_ORANGE,
    )

    embed.set_footer(text=f"Requested by {interaction.user.name}")
    embed.timestamp = discord.utils.utcnow()

    await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
  await bot.add_cog(CheckCommand(bot))
  
