import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

# Импортируем конфиг и роли
from config import errors, group_id
from group_roles import immutable_roles, complete_roles


class RoleReadCommand(commands.Cog):
    COLOR_RED = discord.Color.red()

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _log_error_to_channel(self, error_message: str):
        if not errors:
            return
        channel = self.bot.get_channel(errors)
        if channel:
            embed_log = discord.Embed(
                title="🚨 Role Read Error Log",
                description=error_message,
                color=self.COLOR_RED,
            )
            embed_log.timestamp = discord.utils.utcnow()
            try:
                await channel.send(embed=embed_log)
            except Exception:
                pass

    async def _get_users_in_group_role(self, role_id: int) -> list[str]:
        """Получает список имен пользователей, находящихся на конкретном ранке в группе Roblox."""
        url = f"https://groups.roblox.com/v1/groups/{group_id}/roles/{role_id}/users?limit=100"
        usernames = []
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for user in data.get("data", []):
                        name = user.get("username") or user.get("name")
                        if name:
                            usernames.append(name)
        return usernames

    @app_commands.command(
        name="role_read",
        description="Audits and displays participants holding immutable leadership roles",
    )
    async def role_read(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)

        description_lines = []

        # Проходим по каждой имунной роли из нашего списка
        for role_name in immutable_roles:
            role_data = complete_roles.get(role_name)
            if not role_data:
                continue
            
            role_id = role_data["role_id"]
            users = await self._get_users_in_group_role(role_id)

            if users:
                users_formatted = ", ".join([f"`{u}`" for u in users])
            else:
                users_formatted = "*None*"

            description_lines.append(f"### {role_name}\n{users_formatted}")

        # Если вдруг список пуст
        if not description_lines:
            description_lines.append("No immutable roles found or configured.")

        full_description = "\n\n".join(description_lines)

        if len(full_description) > 4096:
            full_description = full_description[:4093] + "..."

        embed = discord.Embed(
            title="⭐ Senior Team+ Audit",
            description=full_description,
            color=discord.Color.random(),  # Случайный цвет для каждого аудита
        )
        embed.set_footer(text=f"Requested by {interaction.user.name}")
        embed.timestamp = discord.utils.utcnow()

        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(RoleReadCommand(bot))
                                            
