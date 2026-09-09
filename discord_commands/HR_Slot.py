import discord
from discord import app_commands
from discord.ext import commands

# Import channel ID from config
from config import errors


class HRSlotsSetupCommand(commands.Cog):
  # Color palette
  COLOR_BLUE = discord.Color.from_str("#4ec3ed")

  def __init__(self, bot: commands.Bot):
    self.bot = bot

  @app_commands.command(
      name="HRs",
      description="Creates an empty HR Slots embed template for future updates",
  )
  @app_commands.checks.has_permissions(administrator=True)
  async def hr_slots_setup(self, interaction: discord.Interaction):
    # Defer response to prevent timeouts
    await interaction.response.defer(thinking=True, ephemeral=True)

    # Get the target channel using ID from config
    target_channel = self.bot.get_channel(errors)

    if not target_channel:
      await interaction.followup.send(
          "❌ Error: Could not find the channel specified in `config.errors`. Check the ID.",
          ephemeral=True
      )
      return

    # Create an empty embed with title only
    embed = discord.Embed(
        title="HR Slots",
        description="...",
        color=self.COLOR_BLUE,
    )

    # Send the embed to the channel from config
    message = await target_channel.send(embed=embed)

    # Notify the administrator privately and log the ID in console
    await interaction.followup.send(
        f"Embed successfully created in {target_channel.mention}! Message ID: `{message.id}`", 
        ephemeral=True
    )
    print(f"[HR Slots] Embed created. Message ID: {message.id} in channel {target_channel.name}")

  # Error handler if user lacks administrator permissions
  @hr_slots_setup.error
  async def hr_slots_setup_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
      if interaction.response.is_done():
        await interaction.followup.send("❌ You don't have administrator permissions to use this command.", ephemeral=True)
      else:
        await interaction.response.send_message("❌ You don't have administrator permissions to use this command.", ephemeral=True)
    else:
      raise error


async def setup(bot: commands.Bot):
  await bot.add_cog(HRSlotsSetupCommand(bot))
  
