import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

# Импортируем конфигурационные данные и роли
from config import cloud_api, errors, group_id, head_of_human_resources, human_resources, progression
from group_roles import complete_roles, immutable_roles, operational_roles


class SetRankCommand(commands.Cog):
    COLOR_BLUE = discord.Color.blue()
    COLOR_RED = discord.Color.red()

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

    # --- Dynamic Autocomplete Logic ---
    async def rank_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        
        is_head = any(role.id == head_of_human_resources for role in interaction.user.roles)
        is_hr = any(role.id == human_resources for role in interaction.user.roles)

        if not is_head and not is_hr:
            return []

        allowed_role_names = []

        for name in complete_roles:
            if is_head:
                # Head of HR can see all roles in complete_roles
                allowed_role_names.append(name)
            elif is_hr:
                # Regular HR can only see operational roles
                if name in operational_roles:
                    allowed_role_names.append(name)

        # Filter options based on user input
        filtered = [
            name for name in allowed_role_names 
            if current.lower() in name.lower()
        ]

        return [
            app_commands.Choice(name=name, value=name) 
            for name in filtered[:25]
        ]

    @app_commands.command(
        name="setrank", description="Set a user to a specific rank"
    )
    @app_commands.describe(
        user="Roblox username or user ID", 
        rank="Select the rank to set"
    )
    @app_commands.autocomplete(rank=rank_autocomplete)
    async def setrank(self, interaction: discord.Interaction, user: str, rank: str):
        # 1. Check permissions
        is_head = any(role.id == head_of_human_resources for role in interaction.user.roles)
        is_hr = any(role.id == human_resources for role in interaction.user.roles)

        if not is_head and not is_hr:
            await interaction.response.send_message(
                "You do not have permission to use this command.", ephemeral=True
            )
            return

        await interaction.response.defer(thinking=True)

        progression_channel = self.bot.get_channel(progression)
        errors_channel = self.bot.get_channel(errors)

        try:
            # 2. Validate selected rank existence
            if rank not in complete_roles:
                raise ValueError(f"The rank '{rank}' does not exist.")

            target_role_info = complete_roles[rank]
            target_role_id = target_role_info["role_id"]

            # 3. Security checks based on roles
            if target_role_id in self.immutable_role_ids and not is_head:
                raise ValueError("You do not have permission to set protected (immutable) roles.")

            if not is_head and target_role_id not in self.operational_role_ids:
                raise ValueError("You can only set operational roles.")

            # 4. Get Roblox user ID
            roblox_id = await self._get_roblox_user_id(user)
            if not roblox_id:
                raise ValueError(f"Roblox user '{user}' not found.")

            # 5. Get current role in the group
            current_role_data = await self._get_user_roblox_role(roblox_id)
            if not current_role_data:
                raise ValueError("User is not in the group.")

            current_role_name = current_role_data["name"]
            current_role_id = current_role_data["id"]

            # Prevent changing if target user's current role is immutable and runner is not head
            if current_role_id in self.immutable_role_ids and not is_head:
                raise ValueError(f"The user's current role '{current_role_name}' is protected from changes.")

            # 6. Send request to Cloud API
            success = await self._set_roblox_role(roblox_id, target_role_id)
            if not success:
                raise RuntimeError("Failed to execute request to Roblox Cloud API.")

            # 7. Successful execution: send response and log embed
            await interaction.followup.send(f"Successfully set rank for **{user}** to **{rank}**.")

            if progression_channel:
                embed = discord.Embed(title="Set Rank", color=self.COLOR_BLUE)
                embed.add_field(
                    name="Human Resources / Head",
                    value=interaction.user.mention,
                    inline=False,
                )
                embed.add_field(name="Username", value=user, inline=False)
                embed.add_field(name="New Rank", value=rank, inline=False)
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
                    title="Set Rank Error",
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
    await bot.add_cog(SetRankCommand(bot))
      
