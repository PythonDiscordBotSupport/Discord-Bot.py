import aiohttp
import asyncio
from discord.ext import commands
import config


async def update_roblox_group_members(bot: commands.Bot):
    group_id = getattr(config, "group_id", None)
    channel_id = getattr(config, "group_members", None)
    errors_channel_id = getattr(config, "errors", None)

    if not group_id or not channel_id:
        return

    url = f"https://groups.roblox.com/v1/groups/{group_id}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise Exception(f"Roblox API returned status code {response.status}")
                
                data = await response.json()
                member_count = data.get("memberCount")
                
                if member_count is None:
                    raise Exception("Failed to retrieve member count from Roblox API response.")

                new_name = f"⭐┆Group Members: {member_count}"

                channel = bot.get_channel(int(channel_id))
                if channel:
                    if channel.name != new_name:
                        await channel.edit(name=new_name)
                        print(f"[Roblox Group] Group members channel updated: {new_name}")

    except Exception as e:
        error_msg = f"[Roblox Group] Error updating member count: {e}"
        print(error_msg)

        if errors_channel_id:
            error_channel = bot.get_channel(int(errors_channel_id))
            if error_channel:
                embed = discord.Embed(
                    title="❌ Error",
                    description=str(e),
                    color=discord.Color.red()
                )
                await error_channel.send(embed=embed)


async def setup(bot: commands.Bot):
    # If you want it to run periodically, you can schedule it or run it once upon loading
    bot.loop.create_task(update_roblox_group_members(bot))
  
