import aiohttp
import asyncio
import discord
from discord.ext import commands, tasks
import config


class OfficerStats(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.ROLE_IDS = [
            97711635, 97711697, 677141025, 678163023, 677087015, 
            677013012, 677157025, 676955009, 677115023, 97711654, 97711670
        ]
        self.update_stats.start()

    @tasks.loop(minutes=3)
    async def update_stats(self):
        group_id = getattr(config, "group_id", None)
        channel_id = getattr(config, "officer_members", None)
        errors_channel_id = getattr(config, "errors", None)

        if not group_id or not channel_id:
            return

        url = f"https://groups.roblox.com/v1/groups/{group_id}/roles"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        raise Exception(f"Roblox API returned status code {response.status}")
                    
                    data = await response.json()
                    roles_data = {r['id']: r['memberCount'] for r in data.get('roles', [])}
                    count = sum(roles_data.get(rid, 0) for rid in self.ROLE_IDS)

                    new_name = f"🎖️┆Officer Members: {count}"

                    channel = self.bot.get_channel(int(channel_id))
                    if channel:
                        if channel.name != new_name:
                            await channel.edit(name=new_name)
                            print(f"[OfficerStats] Channel updated: {new_name}")

        except Exception as e:
            error_msg = f"[OfficerStats] Error updating stats: {e}"
            print(error_msg)

            if errors_channel_id:
                error_channel = self.bot.get_channel(int(errors_channel_id))
                if error_channel:
                    embed = discord.Embed(
                        title="❌ Error",
                        description=str(e),
                        color=discord.Color.red()
                    )
                    await error_channel.send(embed=embed)

    @update_stats.before_loop
    async def before_update_stats(self):
        await self.bot.wait_until_ready()

    def cog_unload(self):
        self.update_stats.cancel()


async def setup(bot: commands.Bot):
    await bot.add_cog(OfficerStats(bot))
  
