import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

# Импортируем конфигурационные данные и роли
from config import cloud_api, errors, group_id, human_resources, progression
from group_roles import complete_roles, immutable_roles, operational_roles


class DemoteCommand(commands.Cog):
    COLOR_RED = discord.Color.red()  # Red color for demotions and errors

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
        # Automatically collect IDs of immutable roles
        self.immutable_role_ids = {
            complete_roles[name]["role_id"]
            for name in immutable_roles
            if name in complete_roles
        }
        
        # Automatically collect IDs of operational roles
        self.operational_role_ids = {
            complete_roles[name]["role_id"]
            for name in operational_roles
            if name in complete_roles
        }

    async def _get_roblox_user_id(self, username_or_id: str) -> int | None:
        """Converts a Roblox username to an ID or validates the provided ID."""
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
        """Gets the user's current role in the Roblox group."""
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
        """Sets a new role via the Roblox Cloud API."""
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
        name="demote", description="Demote a group member by 1 rank"
    )
    @app_commands.describe(user="Roblox username or user ID")
    async def demote(self, interaction: discord.Interaction, user: str):
        # 1. Check if the user has the HR role in Discord
        if not any(role.id == human_resources for role in interaction.user.roles):
            await interaction.response.send_message(
                "You do not have permission to use this command.", ephemeral=True
            )
            return

        await interaction.response.defer(thinking=True)

        progression_channel = self.bot.get_channel(progression)
        errors_channel = self.bot.get_channel(errors)

        try:
            # 2. Get the Roblox user ID
            roblox_id = await self._get_roblox_user_id(user)
            if not roblox_id:
                raise ValueError(f"Roblox user '{user}' not found.")

            # 3. Get the current role in the group
            current_role_data = await self._get_user_roblox_role(roblox_id)
            if not current_role_data:
                raise ValueError("User is not in the group.")

            current_role_name = current_role_data["name"]
            current_role_id = current_role_data["id"]

            # Validate current role by ID
            if current_role_id in self.immutable_role_ids:
                raise ValueError(f"The role '{current_role_name}' is protected from changes.")

            if current_role_id not in self.operational_role_ids:
                raise ValueError(f"The role '{current_role_name}' is not within operational roles.")

            # Find the current weight and previous (lower) rank
            current_weight = None
            for r_name, r_info in complete_roles.items():
                if r_info["role_id"] == current_role_id:
                    current_weight = r_info["weight"]
                    break

            if current_weight is None:
                raise ValueError("Current role not found in the system role database.")

            # Decrease weight by 1 for demotion
            next_weight = current_weight - 1
            next_role_name = None
            next_role_id = None

            for r_name, r_info in complete_roles.items():
                if r_info["weight"] == next_weight:
                    next_role_name = r_name
                    next_role_id = r_info["role_id"]
                    break

            if not next_role_name:
                raise ValueError("Minimum possible rank has been reached.")

            # Protection check: ensure the NEW target role is also within operational roles
            if next_role_id not in self.operational_role_ids:
                raise ValueError(f"Demotion failed: the next rank '{next_role_name}' is outside operational roles.")

            # 4. Send request to Cloud API
            success = await self._set_roblox_role(roblox_id, next_role_id)
            if not success:
                raise RuntimeError("Failed to execute request to Roblox Cloud API.")

            # 5. Successful execution: send messages and red embed
            await interaction.followup.send(f"{user} has been demoted.")

            if progression_channel:
                embed = discord.Embed(title="Demotion", color=self.COLOR_RED)
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
            await interaction.followup.send(f"An error occurred: {error_text}", ephemeral=True)

            if errors_channel:
                error_embed = discord.Embed(
                    title="Demotion Error",
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
    await bot.add_cog(DemoteCommand(bot))
                
