import asyncio
import discord
from discord.ext import commands
import pandas as pd
import config


async def update_hr_slots(bot: commands.Bot):
  url = "https://docs.google.com/spreadsheets/d/1sQIT3aOs1dWB9-f8cbsYe7MnSRfCfLRgMDSuE5b3w1I/export?format=csv"
  target = "[SEA] SEA Agent Recon Unit"

  try:
    df = await asyncio.to_thread(pd.read_csv, url, header=None)

    # regex=False отключает интерпретацию квадратных скобок как спецсимволов поиска
    mask = df.iloc[:, 0].astype(str).str.contains(
        target, case=False, na=False, regex=False
    )
    match_indices = df[mask].index

    if match_indices.empty:
      raise ValueError(f"Target not found: '{target}'")

    start_idx = match_indices[0]
    hr_list = []

    current_idx = start_idx + 1
    while current_idx < len(df):
      val_a = str(df.iloc[current_idx, 0]).strip()
      val_b = str(df.iloc[current_idx, 1]).strip()

      # Стоппер: если обе ячейки пустые
      if (
          not val_a
          or val_a.lower() == "nan"
          and (not val_b or val_b.lower() == "nan")
      ):
        break

      # Стоппер: если началась следующая секция/клан
      if val_a.startswith("[SEA]") and current_idx != start_idx + 1:
        break

      # Очистка столбца А от "DIVISION LEADER"
      if "DIVISION LEADER" in val_a.upper():
        clean_role = val_a.replace("DIVISION LEADER", "").strip(" -")
      else:
        clean_role = val_a

      # Формируем красивую строку для списка
      if val_b and val_b.lower() != "nan":
        if clean_role:
          hr_list.append(f"{clean_role} — {val_b}")
        else:
          hr_list.append(f"{val_b}")
      elif clean_role and clean_role.lower() != "nan":
        hr_list.append(f"{clean_role}")

      current_idx += 1

    description = "\n".join(hr_list) if hr_list else "List is empty"

    embed_info = getattr(config, "hr_embed", None)
    if not embed_info:
      raise ValueError("Parameter hr_embed not found in config.py")

    channel_id = embed_info.get("channel_id")
    message_id = embed_info.get("message_id")

    channel = bot.get_channel(int(channel_id))
    if not channel:
      raise ValueError(f"HR channel with ID {channel_id} not found")

    try:
      message = await channel.fetch_message(int(message_id))
    except discord.NotFound:
      raise ValueError(f"Message with ID {message_id} not found")

    embed = discord.Embed(
        title="HR Slots", description=description, color=discord.Color.blue()
    )

    await message.edit(embed=embed)
    print("[HR Slots] Embed successfully updated!")

  except Exception as e:
    print(f"[HR Slots Error] {e}")

    error_channel_id = getattr(config, "errors", None)
    if error_channel_id:
      error_channel = bot.get_channel(int(error_channel_id))
      if error_channel:
        error_embed = discord.Embed(
            title="❌ HR Update Error",
            description=f"```py\n{e}\n```",
            color=discord.Color.red(),
        )
        await error_channel.send(embed=error_embed)


async def setup(bot: commands.Bot):
  pass
  
