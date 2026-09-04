import discord
from discord import app_commands
from discord.ext import commands


class ServersCommand(commands.Cog):
  # Используем ту же палитру для стилевого единства
  COLOR_BLUE = discord.Color.from_str("#4ec3ed")
  COLOR_GREEN = discord.Color.from_str("#73d15e")

  def __init__(self, bot: commands.Bot):
    self.bot = bot

  @app_commands.command(
      name="servers",
      description="Shows the list of Discord servers where the bot is deployed",
  )
  async def servers(self, interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)

    guilds = self.bot.guilds
    total_guilds = len(guilds)
    total_members = sum(g.member_count for g in guilds if g.member_count)

    # Собираем информацию о серверах (берем топ-10 или топ-15, чтобы не упереться в лимиты эмбеда)
    # Если серверов немного, выведем все. Если много — покажем основные.
    server_lines = []
    for index, guild in enumerate(guilds[:15], start=1):
      owner = "Unknown"
      try:
        owner = str(guild.owner) if guild.owner else "N/A"
      except Exception:
        pass

      server_lines.append(
          f"**{index}. {guild.name}**\n"
          f"• ID: `{guild.id}`\n"
          f"• Members: `{guild.member_count}` | Owner: `{owner}`"
      )

    description = (
        f"📊 **Total Servers:** `{total_guilds}`\n"
        f"👥 **Total Reach:** `{total_members}` users\n\n"
    )

    if server_lines:
      description += "📌 **Active Deployments:**\n" + "\n\n".join(server_lines)
    else:
      description += "*Bot is not deployed on any servers yet.*"

    # Если серверов больше 15, добавидим пометку в футер
    footer_text = f"Requested by {interaction.user.name}"
    if total_guilds > 15:
      footer_text = (
          f"Showing first 15 of {total_guilds} servers • Requested by"
          f" {interaction.user.name}"
      )

    embed = discord.Embed(
        title="🌐 Bot Deployment Servers",
        description=description,
        color=self.COLOR_BLUE,
    )
    embed.set_footer(text=footer_text)

    await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
  await bot.add_cog(ServersCommand(bot))
  
