import asyncio
import aiohttp
from discord.ext import commands
from config import restart_token


class ConnectionWatchdog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.disconnect_time = None  # Timestamp when the bot lost connection
        self.max_downtime = 600  # 10 minutes in seconds
        # Start the background task when the module loads
        self.watchdog_task = self.bot.loop.create_task(self.watchdog_loop())

    def cog_unload(self):
        # Cancel the task when the module is unloaded
        self.watchdog_task.cancel()

    async def watchdog_loop(self):
        await self.bot.wait_until_ready()
        print("🛡️ Connection Watchdog started successfully.")

        while not self.bot.is_closed():
            # NORMAL MODE: Bot is connected
            if self.bot.is_connected():
                # If the bot was previously disconnected but recovered on its own, reset the timer
                if self.disconnect_time is not None:
                    print(
                        "🟢 Connection restored! Resetting disconnect timer."
                    )
                    self.disconnect_time = None

                # Check interval in normal mode: 10 minutes (600 seconds)
                await asyncio.sleep(600)
                continue

            # DISCONNECTED MODE: No connection to the Discord gateway
            current_time = asyncio.get_event_loop().time()

            # If this is the first check after a drop, record the time
            if self.disconnect_time is None:
                self.disconnect_time = current_time
                print(
                    "⚠️ Connection lost! Watchdog started tracking downtime..."
                )

            # Calculate how much time has passed since the drop
            elapsed_downtime = current_time - self.disconnect_time
            print(
                f"⏱️ Bot is offline for {int(elapsed_downtime)} seconds (Limit: {self.max_downtime}s)"
            )

            # If offline for more than 10 minutes and hasn't recovered, restart
            if elapsed_downtime >= self.max_downtime:
                print(
                    "🚨 Downtime limit reached! Triggering Render restart via webhook..."
                )
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(restart_token) as response:
                            if response.status == 200:
                                print(
                                    "🚀 Restart request sent successfully!"
                                )
                            else:
                                print(
                                    f"❌ Failed to send restart request. Status: {response.status}"
                                )
                except Exception as e:
                    print(f"❌ Error while sending restart request: {e}")

                # Wait a bit to avoid spamming requests if the restart is delayed
                await asyncio.sleep(60)
            else:
                # If disconnected, check more frequently: every 2 minutes (120 seconds)
                await asyncio.sleep(120)


async def setup(bot: commands.Bot):
    await bot.add_cog(ConnectionWatchdog(bot))
