from config import bot_token
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

def start_bot():
    # Запуск бота с токеном происходить ТОЛЬКО здесь
    bot.run(bot_token)
  
