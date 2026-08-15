import asyncio
import pandas as pd
from discord.ext import commands
import config


async def update_division_stats(bot: commands.Bot):
    url = "https://docs.google.com/spreadsheets/d/1sQIT3aOs1dWB9-f8cbsYe7MnSRfCfLRgMDSuE5b3w1I/export?format=csv"
    target = "Sea Agent Recon Unit"

    try:
        df = await asyncio.to_thread(pd.read_csv, url, header=None)

        mask = df.iloc[:, 0].astype(str).str.contains(target, case=False, na=False)
        match = df[mask]

        if match.empty:
            print(f"[Division Info] Ничего не найдено по запросу: '{target}'")
            return

        # Извлечение только цифр из столбцов B и D
        val_b_raw = str(match.iloc[0, 1])
        val_b = "".join(filter(str.isdigit, val_b_raw))

        val_d_raw = str(match.iloc[0, 3])
        val_d = "".join(filter(str.isdigit, val_d_raw))

        level_name = f"🆙┆Division Level: {val_b}"
        exp_name = f"✨┆Division Experiences: {val_d}"

        level_channel_id = getattr(config, "division_level", None)
        exp_channel_id = getattr(config, "division_exp", None)

        if level_channel_id:
            channel_level = bot.get_channel(int(level_channel_id))
            if channel_level:
                await channel_level.edit(name=level_name)
                print(f"[Division Info] Канал уровня обновлен: {level_name}")

        if exp_channel_id:
            channel_exp = bot.get_channel(int(exp_channel_id))
            if channel_exp:
                await channel_exp.edit(name=exp_name)
                print(f"[Division Info] Канал опыта обновлен: {exp_name}")

    except Exception as e:
        print(f"[Division Info] Ошибка при обновлении статистики: {e}")
        
