import discord
from discord import app_commands
from discord.ext import commands

# Import channel ID for error logging from config
from config import errors


class EmbedCommand(commands.Cog):
  def __init__(self, bot: commands.Bot):
    self.bot = bot

  @app_commands.command(
      name="embed",
      description="Creates and sends an empty embed template in the current channel",
  )
  @app_commands.checks.has_permissions(administrator=True)
  async def embed_command(self, interaction: discord.Interaction):
    # Defer response to prevent timeouts
    await interaction.response.defer(thinking=True, ephemeral=True)

    # Create an embed with "Empty" in both title and description
    embed = discord.Embed(
        title="Empty",
        description="Empty", 
        color=discord.Color.blue()
    )

    # Send the embed to the channel where the command was invoked
    await interaction.channel.send(embed=embed)

    # Notify the administrator privately that the embed has been sent
    await interaction.followup.send(
        "✅ Empty embed successfully sent to this channel!", 
        ephemeral=True
    )

  # Error handler for missing permissions and logging other errors to config.errors
  @embed_command.error
  async def embed_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
      msg = "❌ You don't have administrator permissions to use this command."
      if interaction.response.is_done():
        await interaction.followup.send(msg, ephemeral=True)
      else:
        await interaction.response.send_message(msg, ephemeral=True)
    else:
      # Log unexpected errors as a built-in red embed to the error channel specified in config
      error_channel = self.bot.get_channel(errors)
      if error_channel:
        error_embed = discord.Embed(
            title="⚠️ Command Error",
            description=f"**Command:** `/embed`\n**User:** {interaction.user} (`{interaction.user.id}`)\n**Error:** ```python\n{error}\n```",
            color=discord.Color.red()
        )
        await error_channel.send(embed=error_embed)
      raise error


async def setup(bot: commands.Bot):
  await bot.add_cog(EmbedCommand(bot))
  
