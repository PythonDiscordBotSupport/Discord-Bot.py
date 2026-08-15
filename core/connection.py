from datetime import datetime
import os
import discord
from discord.ext import commands
from config import bot_token, errors, notifications

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="", intents=intents)

loaded_modules = []
failed_modules = []


async def load_extensions():
    # Список папок в корне проекта
    folders = ["discord_commands", "roblox_commands", "automation"]

    for folder in folders:
        # Проверяем наличие папки от корня проекта
        if os.path.exists(folder):
            for filename in os.listdir(folder):
                if filename.endswith(".py") and not filename.startswith("_"):
                    module_name = f"{folder}.{filename[:-3]}"
                    try:
                        await bot.load_extension(module_name)
                        loaded_modules.append(module_name)
                        print(f"Loaded module: {module_name}")
                    except Exception as e:
                        failed_modules.append((module_name, str(e)))
                        print(f"Failed to load {module_name}: {e}")


@bot.event
async def setup_hook():
    await load_extensions()
    await bot.tree.sync()
    print("All slash commands synced successfully!")


@bot.event
async def on_ready():
    print(f"Bot {bot.user} is fully online!")

    current_time = datetime.now().strftime("%H:%M:%S | %d.%m.%Y")

    # --- NOTIFICATIONS CHANNEL ---
    notif_channel = bot.get_channel(notifications)
    if notif_channel:
        embed_status = discord.Embed(
            title="🟢 System Status",
            description=f"Bot **{bot.user.name}** has been successfully launched and is ready!",
            color=discord.Color.green(),
        )
        embed_status.set_footer(text=f"Launch time: {current_time}")

        modules_list_text = (
            "\n".join([f"• `{mod}`" for mod in loaded_modules])
            if loaded_modules
            else "No modules loaded."
        )

        embed_cogs = discord.Embed(
            title="📦 Loaded Modules",
            description=modules_list_text,
            color=discord.Color.green(),
        )

        await notif_channel.send(embeds=[embed_status, embed_cogs])
    else:
        print(f"Could not find notifications channel with ID: {notifications}")

    # --- ERRORS CHANNEL ---
    if failed_modules:
        error_channel = bot.get_channel(errors)
        if error_channel:
            error_text = "\n".join(
                [f"• **{mod}**: `{err}`" for mod, err in failed_modules]
            )

            embed_errors = discord.Embed(
                title="🔴 Module Loading Errors",
                description=error_text,
                color=discord.Color.red(),
            )
            embed_errors.set_footer(text=f"Timestamp: {current_time}")

            await error_channel.send(embed=embed_errors)
        else:
            print(f"Could not find errors channel with ID: {errors}")


def start_bot():
    bot.run(bot_token)
    
