import re
import discord
from discord import app_commands
from discord.ext import commands

from config import errors


class CustomEmbedCog(commands.Cog):
  def __init__(self, bot: commands.Bot):
    self.bot = bot

  # Create a command group named "custom" -> /custom
  custom_group = app_commands.Group(
      name="custom", 
      description="Custom management commands"
  )

  def parse_colored_text(self, text: str) -> str:
    # ANSI color codes for Discord text blocks
    ansi_colors = {
        "red": "\u001b[31m",
        "green": "\u001b[32m",
        "yellow": "\u001b[33m",
        "blue": "\u001b[34m",
        "purple": "\u001b[35m",
        "cyan": "\u001b[36m",
    }

    # Search for patterns like: text[color]
    pattern = re.compile(r"([^\[]+?)\[(red\vert{}green\vert{}yellow\vert{}blue\vert{}purple\vert{}cyan)\]", re.IGNORECASE)

    def replace_match(match):
      word = match.group(1)
      color = match.group(2).lower()
      code = ansi_colors.get(color, "")
      return f"{code}{word}\u001b[0m"

    processed_text = pattern.sub(replace_match, text)

    # Wrap in an ansi block if color tags were found
    if "\u001b[" in processed_text:
      return f"```ansi\n{processed_text}\n```"
    
    return text

  # Subcommand embed inside custom group -> /custom embed
  @custom_group.command(
      name="embed",
      description="Creates an embed with color tags. Example: Hi[yellow] everyone",
  )
  @app_commands.checks.has_permissions(administrator=True)
  async def custom_embed(
      self, 
      interaction: discord.Interaction, 
      title: str, 
      description: str
  ):
    # Defer response to prevent timeouts
    await interaction.response.defer(thinking=True, ephemeral=True)

    # Parse tags into colored text
    formatted_title = self.parse_colored_text(title)
    formatted_description = self.parse_colored_text(description)

    # Create the embed
    embed = discord.Embed(
        title=formatted_title,
        description=formatted_description,
        color=discord.Color.blue()
    )

    # Send the embed to the current channel
    await interaction.channel.send(embed=embed)

    # Send private confirmation to the admin
    await interaction.followup.send(
        "✅ Custom embed successfully sent to this channel!", 
        ephemeral=True
    )

  # Error handler for the subcommand
  @custom_embed.error
  async def custom_embed_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
      msg = "❌ You don't have administrator permissions to use this command."
      if interaction.response.is_done():
        await interaction.followup.send(msg, ephemeral=True)
      else:
        await interaction.response.send_message(msg, ephemeral=True)
    else:
      # Log unexpected errors to the config error channel
      error_channel = self.bot.get_channel(errors)
      if error_channel:
        error_embed = discord.Embed(
            title="⚠️ Command Error",
            description=f"**Command:** `/custom embed`\n**User:** {interaction.user} (`{interaction.user.id}`)\n**Error:** ```python\n{error}\n```",
            color=discord.Color.red()
        )
        await error_channel.send(embed=error_embed)
      raise error


async def setup(bot: commands.Bot):
  await bot.add_cog(CustomEmbedCog(bot))
  
