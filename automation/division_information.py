import asyncio
import pandas as pd
import discord
from discord.ext import commands

# Импортируйте ваш объект конфигурации, например:
# import config


async def update_division_stats(bot: commands.Bot, config):
    url = "https://docs.google.com/spreadsheets/d/1sQIT3aOs1dWB9-f8cbsYe7MnSRfCfLRgMDSuE5b3w1I/export?format=csv"
    target = "Sea Agent Recon Unit"

    try:
        # Выполняем чтение таблицы в отдельном потоке
        df = await asyncio.to_thread(pd.read_csv, url, header=None)

        mask = df.iloc[:, 0].astype(str).str.contains(target, case=False, na=False)
        match = df[mask]

        if match.empty:
            print(f"Ничего не найдено по запросу: '{target}'")
            return

        # Извлечение данных из столбцов B (индекс 1) и D (индекс 3)
        val_b_raw = str(match.iloc[0, 1])
        val_b = "".join(filter(str.isdigit, val_b_raw))
        val_d = str(match.iloc[0, 3]).strip()

        # Форматирование новых имен каналов
        level_name = f"🆙┆Division Level: {val_b}"
        exp_name = f"✨┆Division Experiences: {val_d}"

        # Получение ID каналов прямо из конфига
        # (если config — словарь, используйте config['division_level'], если модуль/класс — config.division_level)
        level_channel_id = getattr(config, "division_level", None) or config.get(
            "division_level"
        )
        exp_channel_id = getattr(config, "division_exp", None) or config.get(
            "division_exp"
        )

        # Обновление канала уровня (столбец B)
        if level_channel_id:
            channel_level = bot.get_channel(int(level_channel_id))
            if channel_level:
                await channel_level.edit(name=level_name)
                print(f"Канал уровня обновлен: {level_name}")

        # Обновление канала опыта (столбец D)
        if exp_channel_id:
            channel_exp = bot.get_channel(int(exp_channel_id))
            if channel_exp:
                await channel_exp.edit(name=exp_name)
                print(f"Канал опыта обновлен: {exp_name}")

    except Exception as e:
        print(f"Ошибка при обновлении статистики дивизиона: {e}")
      
