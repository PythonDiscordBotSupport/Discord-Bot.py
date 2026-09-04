import discord
from discord import app_commands
from discord.ext import commands


class LeaveCommand(commands.Cog):
  COLOR_BLUE = discord.Color.from_str("#4ec3ed")
  COLOR_GREEN = discord.Color.from_str("#73d15e")
  COLOR_RED = discord.Color.from_str("#ff5555")

  # ID пользователя, которому разрешено использовать эту команду
  ALLOWED_USER_ID = 855164688802906142

  def __init__(self, bot: commands.Bot):
    self.bot = bot

  @app_commands.command(
      name="leave",
      description="Forces the bot to leave a specific Discord server by its ID",
  )
  @app_commands.describe(server_id="The ID of the server the bot should leave")
  async def leave(self, interaction: discord.Interaction, server_id: str):
    # Проверяем ID пользователя
    if interaction.user.id != self.ALLOWED_USER_ID:
      embed = discord.Embed(
          title="❌ Access Denied",
          description="You do not have permission to use this command.",
          color=self.COLOR_RED,
      )
      await interaction.response.send_message(embed=embed, ephemeral=True)
      return

    await interaction.response.defer(thinking=True, ephemeral=True)

    try:
      # Превращаем введенный текст в число (ID сервера)
      guild_id = int(server_id)
    except ValueError:
      embed = discord.Embed(
          title="⚠️ Invalid ID",
          description="Please provide a valid numeric server ID.",
          color=self.COLOR_RED,
      )
      await interaction.followup.send(embed=embed)
      return

    # Ищем сервер среди тех, на которых находится бот
    guild = self.bot.get_guild(guild_id)

    if guild is None:
      embed = discord.Embed(
          title="⚠️ Server Not Found",
          description=(
              f"The bot is not deployed on a server with ID `{guild_id}`."
          ),
          color=self.COLOR_RED,
      )
      await interaction.followup.send(embed=embed)
      return

    guild_name = guild.name

    try:
      # Покидаем сервер
      await guild.leave()

      embed = discord.Embed(
          title="✅ Success",
          description=(
              f"Successfully left the server **{guild_name}** (`{guild_id}`)."
          ),
          color=self.COLOR_GREEN,
      )
      embed.set_footer(text=f"Requested by {interaction.user.name}")
      await interaction.followup.send(embed=embed)

    except Exception as e:
      embed = discord.Embed(
          title="❌ Error",
          description=f"An error occurred while trying to leave the server: `{e}`",
          color=self.COLOR_RED,
      )
      await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
  await bot.add_cog(LeaveCommand(bot))
  
