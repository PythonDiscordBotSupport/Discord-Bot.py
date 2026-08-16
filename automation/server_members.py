import discord
from discord.ext import commands
import config


async def update_server_members(bot: commands.Bot):
    try:
        # Достаем ID сервера и ID канала из конфига
        guild_id = getattr(config, "server_id", None)
        channel_id = getattr(config, "server_members", None)

        if not guild_id or not channel_id:
            print("[Server Members] Ошибка: server_id или server_members не указаны в config")
            return

        guild = bot.get_guild(int(guild_id))
        if not guild:
            print(f"[Server Members] Сервер с ID {guild_id} не найден в кэше бота")
            return

        channel = bot.get_channel(int(channel_id))
        if not channel:
            print(f"[Server Members] Канал с ID {channel_id} не найден в кэше бота")
            return

        # Берем общее количество участников
        member_count = guild.member_count
        new_name = f"👤┆Server Members: {member_count}"

        # Обновляем имя канала только если оно изменилось (чтобы лишний раз не тратить лимиты API)
        if channel.name != new_name:
            await channel.edit(name=new_name)
            print(f"[Server Members] Канал участников обновлен: {new_name}")
        else:
            print("[Server Members] Количество участников не изменилось, обновление пропущено")

    except Exception as e:
        print(f"[Server Members] Ошибка при обновлении участников: {e}")


# Позволяет discord.py распознать этот файл как полноценный загруженный модуль
async def setup(bot: commands.Bot):
    pass
