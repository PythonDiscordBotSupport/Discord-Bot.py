import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

# Импортируем конфигурационные данные и роли
from config import cloud_api, errors, group_id, human_resources, progression
from group_roles import complete_roles, immutable_roles, operational_roles


class PromoteCommand(commands.Cog):
    COLOR_RED = discord.Color.red()
    COLOR_GREEN = discord.Color.green()

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _get_roblox_user_id(self, username_or_id: str) -> int | None:
        """Конвертирует никнейм Roblox в ID или проверяет переданный ID."""
        if username_or_id.isdigit():
            return int(username_or_id)

        url = "https://users.roblox.com/v1/usernames/users"
        payload = {"usernames": [username_or_id], "excludeBannedUsers": True}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("data"):
                        return data["data"][0]["id"]
        return None

    async def _get_user_roblox_role(self, user_id: int) -> dict | None:
        """Получает текущую роль юзера в Roblox группе."""
        url = f"https://groups.roblox.com/v1/users/{user_id}/groups/roles"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    for group in data.get("data", []):
                        if group.get("group", {}).get("id") == group_id:
                            return group.get("role")
        return None

    async def _set_roblox_role(self, user_id: int, new_role_id: int) -> bool:
        """Устанавливает новую роль через Roblox Cloud API."""
        url = f"https://apis.roblox.com/cloud/v2/groups/{group_id}/memberships/{user_id}"
        headers = {
            "x-api-key": cloud_api,
            "Content-Type": "application/json",
        }
        payload = {"role": f"groups/{group_id}/roles/{new_role_id}"}

        async with aiohttp.ClientSession() as session:
            async with session.patch(url, headers=headers, json=payload) as response:
                return response.status == 200

    @app_commands.command(
        name="promote", description="Повысить участника в группе на 1 ранг"
    )
    @app_commands.describe(user="Никнейм или ID пользователя в Roblox")
    async def promote(self, interaction: discord.Interaction, user: str):
        # 1. Проверка наличия роли HR у пользователя в Discord
        if not any(role.id == human_resources for role in interaction.user.roles):
            await interaction.response.send_message(
                "У вас нет прав для использования этой команды.", ephemeral=True
            )
            return

        await interaction.response.defer(thinking=True)

        progression_channel = self.bot.get_channel(progression)
        errors_channel = self.bot.get_channel(errors)

        try:
            # 2. Получение ID пользователя Roblox
            roblox_id = await self._get_roblox_user_id(user)
            if not roblox_id:
                raise ValueError(f"Пользователь Roblox '{user}' не найден.")

            # 3. Получение текущей роли в группе
            current_role_data = await self._get_user_roblox_role(roblox_id)
            if not current_role_data:
                raise ValueError("Пользователь не состоит в группе.")

            current_role_name = current_role_data["name"]
            current_role_id = current_role_data["id"]

            # Проверки по спискам ролей
            if current_role_name in immutable_roles:
                raise ValueError(f"Роль '{current_role_name}' защищена от изменений.")

            if current_role_name not in operational_roles:
                raise ValueError(f"Роль '{current_role_name}' не входит в operational roles.")

            # Поиск текущего веса и следующей роли
            current_weight = None
            for r_name, r_info in complete_roles.items():
                if r_info["role_id"] == current_role_id:
                    current_weight = r_info["weight"]
                    break

            if current_weight is None:
                raise ValueError("Текущая роль не найдена в системной базе ролей.")

            next_weight = current_weight + 1
            next_role_name = None
            next_role_id = None

            for r_name, r_info in complete_roles.items():
                if r_info["weight"] == next_weight:
                    next_role_name = r_name
                    next_role_id = r_info["role_id"]
                    break

            if not next_role_name:
                raise ValueError("Достигнут максимальный возможный ранг.")

            # 4. Отправка запроса в Cloud API
            success = await self._set_roblox_role(roblox_id, next_role_id)
            if not success:
                raise RuntimeError("Ошибка при запросе к Roblox Cloud API.")

            # 5. Успешное выполнение: отправка сообщений и зеленого эмбеда
            await interaction.followup.send(f"{user} был повышен")

            if progression_channel:
                embed = discord.Embed(title="Promotion", color=self.COLOR_GREEN)
                embed.add_field(
                    name="Human Resources",
                    value=interaction.user.mention,
                    inline=False,
                )
                embed.add_field(name="Username", value=user, inline=False)
                embed.add_field(name="New Rank", value=next_role_name, inline=False)
                embed.add_field(
                    name="Previous Rank", value=current_role_name, inline=False
                )
                embed.timestamp = discord.utils.utcnow()
                await progression_channel.send(embed=embed)

        except Exception as e:
            error_text = str(e)
            await interaction.followup.send(f"Произошла ошибка: {error_text}", ephemeral=True)

            if errors_channel:
                error_embed = discord.Embed(
                    title="Promotion Error",
                    description=error_text,
                    color=self.COLOR_RED,
                )
                error_embed.set_author(
                    name=str(interaction.user),
                    icon_url=interaction.user.display_avatar.url,
                )
                error_embed.timestamp = discord.utils.utcnow()
                await errors_channel.send(embed=error_embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(PromoteCommand(bot))
          
