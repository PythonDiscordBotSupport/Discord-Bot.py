from datetime import datetime
import os
import discord
from discord.ext import commands
from config import bot_token, errors, notifications

# 1. Включаем message_content intent
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

loaded_modules = []
failed_modules = []
is_first_ready = True  # Флаг для предотвращения спама при переподключениях


async def load_extensions():
    folders = ["discord_commands", "roblox_commands", "automation"]

    for folder in folders:
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
    
    # Синхронизируем слеш-команды с Discord
    try:
        synced = await bot.tree.sync()
        print(f"Successfully synced {len(synced)} command(s).")
    except Exception as e:
        print(f"Failed to sync commands: {e}")


@bot.event
async def on_ready():
    global is_first_ready

    # Выполняем отправку сообщений ТОЛЬКО при самом первом успешном запуске
    if is_first_ready:
        print(f"Bot {bot.user} is fully online!")
        current_time = datetime.now().strftime("%H:%M:%S | %d.%m.%Y")

        # --- NOTIFICATIONS CHANNEL ---
        notif_channel = bot.get_channel(notifications)
        if notif_channel:
            embed_status = discord.Embed(
                title="🟢 System Status",
                description=f"Bot **{bot.user.name}** has been successfully launched and ready!",
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

        is_first_ready = False  # Блокируем повторную отправку при переподсоединениях
    else:
        print(f"Bot {bot.user} reconnected to Gateway.")


def start_bot():
    bot.run(bot_token)
    
