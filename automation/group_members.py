import asyncio
import csv
import io
import aiohttp
import discord
from discord.ext import commands
import config


async def update_division_stats(bot: commands.Bot):
    url = "https://docs.google.com/spreadsheets/d/1sQIT3aOs1dWB9-f8cbsYe7MnSRfCfLRgMDSuE5b3w1I/export?format=csv"
    target = "Sea Agent Recon Unit"

    try:
        # Скачиваем CSV асинхронно через aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    error_msg = f"[Division Info] Error downloading CSV: status {response.status}"
                    print(error_msg)
                    await send_error_embed(bot, error_msg)
                    return
                content = await response.text()

        # Парсим CSV стандартным легким модулем
        f = io.StringIO(content)
        reader = csv.reader(f)
        
        match_row = None
        for row in reader:
            if row and target.lower() in row[0].lower():
                match_row = row
                break

        if not match_row:
            print(f"[Division Info] Nothing found for query: '{target}'")
            return

        # Извлечение цифр из колонок с индексами 1 и 3 (B и D)
        val_b = "".join(filter(str.isdigit, str(match_row[1]))) if len(match_row) > 1 else "0"
        val_d = "".join(filter(str.isdigit, str(match_row[3]))) if len(match_row) > 3 else "0"

        level_name = f"🆙┆Division Level: {val_b}"
        exp_name = f"✨┆Division Experiences: {val_d}"

        level_channel_id = getattr(config, "division_level", None)
        exp_channel_id = getattr(config, "division_exp", None)

        if level_channel_id:
            channel_level = bot.get_channel(int(level_channel_id))
            if channel_level and channel_level.name != level_name:
                await channel_level.edit(name=level_name)
                print(f"[Division Info] Level channel updated: {level_name}")

        if exp_channel_id:
            channel_exp = bot.get_channel(int(exp_channel_id))
            if channel_exp and channel_exp.name != exp_name:
                await channel_exp.edit(name=exp_name)
                print(f"[Division Info] Experience channel updated: {exp_name}")

    except Exception as e:
        error_msg = f"[Division Info] Error updating statistics: {e}"
        print(error_msg)
        await send_error_embed(bot, error_msg)


async def send_error_embed(bot: commands.Bot, error_text: str):
    """Вспомогательная функция для отправки ошибки красным эмбедом в канал из config.errors"""
    error_channel_id = getattr(config, "errors", None)
    if not error_channel_id:
        return

    try:
        channel = bot.get_channel(int(error_channel_id))
        if not channel:
            # Если канал не в кэше, пробуем получить через fetch
            channel = await bot.fetch_channel(int(error_channel_id))
            
        if channel:
            embed = discord.Embed(
                title="⚠️ Error in Division Stats Background Task",
                description=f"```python\n{error_text}\n```",
                color=discord.Color.red()
            )
            embed.set_footer(text="Automated Bot Monitoring")
            await channel.send(embed=embed)
    except Exception as ex:
        print(f"[Critical] Failed to send error to log channel: {ex}")


# Обязательная функция для загрузки модуля в discord.py
async def setup(bot: commands.Bot):
    pass
    
