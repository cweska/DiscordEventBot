"""Food Fight Cog for Discord bot commands."""
import logging
import random
from datetime import datetime, timezone
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from food_fight_manager import FoodFightManager

logger = logging.getLogger(__name__)


def is_admin(interaction: discord.Interaction) -> bool:
    """Check if the user has administrator permissions."""
    if not interaction.guild:
        return False
    if interaction.user.guild_permissions.administrator:
        return True
    return False


class FoodFightCog(commands.Cog):
    """Cog handling food fight commands and reaction tracking."""

    def __init__(
        self,
        bot: commands.Bot,
        food_fight_manager: FoodFightManager,
    ):
        self.bot = bot
        self.food_fight_manager = food_fight_manager

    async def cog_load(self):
        """Called when the cog is loaded."""
        logger.info("FoodFightCog loaded")

    @app_commands.command(name="foodfight-start", description="Start tracking a food fight")
    @app_commands.describe(
        message_id="The message ID of the announcement",
        channel="The channel where the announcement is (optional, uses current channel if not provided)",
        emojis="Comma-separated list of valid team emojis (e.g., 🐕,🐈 or :dog:,:cat:)",
    )
    async def foodfight_start(
        self,
        interaction: discord.Interaction,
        message_id: str,
        channel: Optional[discord.TextChannel] = None,
        emojis: str = "",
    ):
        """Start tracking a food fight from an announcement message."""
        # Check admin permissions
        if not is_admin(interaction):
            await interaction.response.send_message(
                "You need administrator permissions to use this command.",
                ephemeral=True,
            )
            return

        try:
            # Parse message ID
            try:
                msg_id = int(message_id)
            except ValueError:
                await interaction.response.send_message(
                    "Invalid message ID. Please provide a valid numeric message ID.",
                    ephemeral=True,
                )
                return

            # Use current channel if not specified
            target_channel = channel or interaction.channel
            if not isinstance(target_channel, discord.TextChannel):
                await interaction.response.send_message(
                    "Please specify a text channel or use this command in a text channel.",
                    ephemeral=True,
                )
                return

            # Fetch the message
            try:
                message = await target_channel.fetch_message(msg_id)
            except discord.NotFound:
                await interaction.response.send_message(
                    f"Message {msg_id} not found in {target_channel.mention}.",
                    ephemeral=True,
                )
                return
            except discord.Forbidden:
                await interaction.response.send_message(
                    "I don't have permission to read messages in that channel.",
                    ephemeral=True,
                )
                return
            except Exception as e:
                logger.error(f"Error fetching message {msg_id}: {e}")
                await interaction.response.send_message(
                    f"Error fetching message: {e}",
                    ephemeral=True,
                )
                return

            # Parse emojis
            if not emojis:
                await interaction.response.send_message(
                    "Please provide at least one valid team emoji.",
                    ephemeral=True,
                )
                return

            valid_emojis = [e.strip() for e in emojis.split(",") if e.strip()]
            if not valid_emojis:
                await interaction.response.send_message(
                    "Please provide at least one valid team emoji.",
                    ephemeral=True,
                )
                return

            # Normalize emoji strings (handle both Unicode and :name: format)
            normalized_emojis = []
            for emoji_str in valid_emojis:
                # If it's a custom emoji in :name: format, try to resolve it
                if emoji_str.startswith(":") and emoji_str.endswith(":"):
                    emoji_name = emoji_str[1:-1]
                    # Try to find in guild emojis
                    if interaction.guild:
                        custom_emoji = discord.utils.get(interaction.guild.emojis, name=emoji_name)
                        if custom_emoji:
                            normalized_emojis.append(str(custom_emoji))
                            continue
                    # Fall back to original format if not found
                    normalized_emojis.append(emoji_str)
                else:
                    normalized_emojis.append(emoji_str)

            # Fetch reactions and get team assignments
            team_assignments = {}
            user_reactions: dict[int, list[str]] = {}

            for reaction in message.reactions:
                emoji_str = str(reaction.emoji)
                if emoji_str not in normalized_emojis:
                    continue

                # Fetch users who reacted
                try:
                    async for user in reaction.users():
                        if user.bot:
                            continue
                        if user.id not in user_reactions:
                            user_reactions[user.id] = []
                        user_reactions[user.id].append(emoji_str)
                except Exception as e:
                    logger.warning(f"Error fetching users for reaction {emoji_str}: {e}")
                    continue

            # Resolve multiple team assignments (randomly pick one if user has multiple)
            for user_id, reaction_emojis in user_reactions.items():
                valid_reactions = [e for e in reaction_emojis if e in normalized_emojis]
                if valid_reactions:
                    # Randomly pick one if multiple
                    selected_emoji = random.choice(valid_reactions)
                    team_assignments[user_id] = selected_emoji

            if not team_assignments:
                await interaction.response.send_message(
                    "No valid team reactions found on the message. Make sure users have reacted with the specified team emojis.",
                    ephemeral=True,
                )
                return

            # Generate fight ID (use message ID as base)
            fight_id = f"fight_{msg_id}"

            # Check if fight already exists
            existing_fight = await self.food_fight_manager.get_active_fight(fight_id)
            if existing_fight:
                await interaction.response.send_message(
                    f"A food fight with ID `{fight_id}` is already active.",
                    ephemeral=True,
                )
                return

            # Get message creation time as start time
            start_time = message.created_at

            # Start the food fight
            food_fight = await self.food_fight_manager.start_food_fight(
                fight_id=fight_id,
                announcement_message_id=msg_id,
                channel_id=target_channel.id,
                valid_emojis=normalized_emojis,
                team_assignments=team_assignments,
                start_time=start_time,
            )

            await interaction.response.send_message(
                f"✅ Food fight started!\n"
                f"**Fight ID:** `{fight_id}`\n"
                f"**Participants:** {len(team_assignments)} users\n"
                f"**Teams:** {', '.join(normalized_emojis)}\n"
                f"Tracking dishes logged via `/cooked` starting from {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}",
                ephemeral=True,
            )

        except Exception as e:
            logger.error(f"Error starting food fight: {e}", exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    f"An error occurred: {e}",
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    f"An error occurred: {e}",
                    ephemeral=True,
                )

    @app_commands.command(name="foodfight-end", description="End a food fight and show results")
    @app_commands.describe(fight_id="The fight ID (e.g., fight_123456789)")
    async def foodfight_end(
        self,
        interaction: discord.Interaction,
        fight_id: str,
    ):
        """End a food fight and display the results."""
        # Check admin permissions
        if not is_admin(interaction):
            await interaction.response.send_message(
                "You need administrator permissions to use this command.",
                ephemeral=True,
            )
            return

        try:
            # End the food fight
            food_fight = await self.food_fight_manager.end_food_fight(fight_id)
            if not food_fight:
                await interaction.response.send_message(
                    f"Food fight `{fight_id}` not found or already ended.",
                    ephemeral=True,
                )
                return

            # Get tallies
            tallies = await self.food_fight_manager.get_tallies(fight_id)
            if not tallies:
                await interaction.response.send_message(
                    f"Error retrieving tallies for food fight `{fight_id}`.",
                    ephemeral=True,
                )
                return

            # Build results embed
            embed = discord.Embed(
                title="🍽️ Food Fight Results",
                description=f"**Fight ID:** `{fight_id}`",
                color=discord.Color.gold(),
            )

            # Add team results
            team_results = []
            for emoji, team_data in tallies["teams"].items():
                total = team_data["total_dishes"]
                participant_count = len(team_data["participants"])
                team_results.append((emoji, total, participant_count))

            # Sort by total dishes (descending)
            team_results.sort(key=lambda x: x[1], reverse=True)

            # Build field value with team standings
            results_text = ""
            for idx, (emoji, total, participants) in enumerate(team_results, 1):
                medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"{idx}."
                results_text += f"{medal} {emoji} Team: **{total}** dishes ({participants} participants)\n"

            embed.add_field(name="🏆 Final Standings", value=results_text, inline=False)

            # Add participant details
            participant_details = []
            for emoji, team_data in sorted(tallies["teams"].items(), key=lambda x: x[1]["total_dishes"], reverse=True):
                participants = team_data["participants"]
                # Sort participants by dish count
                participants.sort(key=lambda x: x["dishes"], reverse=True)
                
                team_detail = f"\n**{emoji} Team:**\n"
                if participants:
                    for p in participants:
                        user_id = p["user_id"]
                        dishes = p["dishes"]
                        # Try to get username
                        try:
                            if interaction.guild:
                                member = interaction.guild.get_member(user_id)
                                username = member.display_name if member else f"<@{user_id}>"
                            else:
                                user = self.bot.get_user(user_id)
                                username = user.name if user else f"<@{user_id}>"
                        except Exception:
                            username = f"<@{user_id}>"
                        team_detail += f"  • {username}: {dishes} dish{'es' if dishes != 1 else ''}\n"
                else:
                    team_detail += "  No dishes logged\n"
                participant_details.append(team_detail)

            if participant_details:
                embed.add_field(
                    name="📊 Participant Breakdown",
                    value="".join(participant_details),
                    inline=False,
                )

            # Add timestamps
            start_time_str = datetime.fromisoformat(tallies["start_time"]).strftime("%Y-%m-%d %H:%M:%S UTC")
            end_time_str = datetime.fromisoformat(tallies["end_time"]).strftime("%Y-%m-%d %H:%M:%S UTC") if tallies["end_time"] else "Ongoing"
            embed.add_field(name="⏰ Duration", value=f"Started: {start_time_str}\nEnded: {end_time_str}", inline=False)

            # Set footer
            embed.set_footer(text="Food Fight Results")

            await interaction.response.send_message(embed=embed)

        except Exception as e:
            logger.error(f"Error ending food fight: {e}", exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    f"An error occurred: {e}",
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    f"An error occurred: {e}",
                    ephemeral=True,
                )

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """Handle when a user adds a reaction to a message."""
        # Check if this message is an active food fight announcement
        active_fights = await self.food_fight_manager.get_all_active_fights()
        for fight_id, fight in active_fights.items():
            if fight.announcement_message_id == payload.message_id:
                emoji_str = str(payload.emoji)
                if emoji_str in fight.valid_emojis:
                    # User reacted with a valid team emoji
                    # For now, we don't update team assignments after initial registration
                    # (could be added later if needed)
                    logger.debug(f"User {payload.user_id} reacted with {emoji_str} to food fight {fight_id}")
                break

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        """Handle when a user removes a reaction from a message."""
        # Similar to on_raw_reaction_add, we could handle reaction removals here
        # For now, we'll stick with the initial snapshot approach
        pass

    @app_commands.command(name="foodfight-add-retroactive", description="Add a retroactive food fight (admin only)")
    @app_commands.describe(
        message_id="The message ID of the announcement",
        channel="The channel where the announcement is",
        emojis="Comma-separated list of valid team emojis (e.g., :dog:,:cat:)",
    )
    async def foodfight_add_retroactive(
        self,
        interaction: discord.Interaction,
        message_id: str,
        channel: discord.TextChannel,
        emojis: str,
    ):
        """Add a retroactive food fight using the message's creation time as the start time."""
        # Check admin permissions
        if not is_admin(interaction):
            await interaction.response.send_message(
                "You need administrator permissions to use this command.",
                ephemeral=True,
            )
            return

        try:
            # Parse message ID
            try:
                msg_id = int(message_id)
            except ValueError:
                await interaction.response.send_message(
                    "Invalid message ID. Please provide a valid numeric message ID.",
                    ephemeral=True,
                )
                return

            # Fetch the message
            try:
                message = await channel.fetch_message(msg_id)
            except discord.NotFound:
                await interaction.response.send_message(
                    f"Message {msg_id} not found in {channel.mention}.",
                    ephemeral=True,
                )
                return
            except discord.Forbidden:
                await interaction.response.send_message(
                    "I don't have permission to read messages in that channel.",
                    ephemeral=True,
                )
                return
            except Exception as e:
                logger.error(f"Error fetching message {msg_id}: {e}")
                await interaction.response.send_message(
                    f"Error fetching message: {e}",
                    ephemeral=True,
                )
                return

            # Parse emojis
            if not emojis:
                await interaction.response.send_message(
                    "Please provide at least one valid team emoji.",
                    ephemeral=True,
                )
                return

            valid_emojis = [e.strip() for e in emojis.split(",") if e.strip()]
            if not valid_emojis:
                await interaction.response.send_message(
                    "Please provide at least one valid team emoji.",
                    ephemeral=True,
                )
                return

            # Normalize emoji strings
            normalized_emojis = []
            for emoji_str in valid_emojis:
                if emoji_str.startswith(":") and emoji_str.endswith(":"):
                    emoji_name = emoji_str[1:-1]
                    if interaction.guild:
                        custom_emoji = discord.utils.get(interaction.guild.emojis, name=emoji_name)
                        if custom_emoji:
                            normalized_emojis.append(str(custom_emoji))
                            continue
                    normalized_emojis.append(emoji_str)
                else:
                    normalized_emojis.append(emoji_str)

            # Fetch reactions and get team assignments
            team_assignments = {}
            user_reactions: dict[int, list[str]] = {}

            for reaction in message.reactions:
                emoji_str = str(reaction.emoji)
                if emoji_str not in normalized_emojis:
                    continue

                try:
                    async for user in reaction.users():
                        if user.bot:
                            continue
                        if user.id not in user_reactions:
                            user_reactions[user.id] = []
                        user_reactions[user.id].append(emoji_str)
                except Exception as e:
                    logger.warning(f"Error fetching users for reaction {emoji_str}: {e}")
                    continue

            # Resolve multiple team assignments
            for user_id, reaction_emojis in user_reactions.items():
                valid_reactions = [e for e in reaction_emojis if e in normalized_emojis]
                if valid_reactions:
                    selected_emoji = random.choice(valid_reactions)
                    team_assignments[user_id] = selected_emoji

            if not team_assignments:
                await interaction.response.send_message(
                    "No valid team reactions found on the message. Make sure users have reacted with the specified team emojis.",
                    ephemeral=True,
                )
                return

            # Generate fight ID
            fight_id = f"fight_{msg_id}"

            # Check if fight already exists
            existing_fight = await self.food_fight_manager.get_active_fight(fight_id)
            if existing_fight:
                await interaction.response.send_message(
                    f"A food fight with ID `{fight_id}` already exists.",
                    ephemeral=True,
                )
                return

            # Use message creation time as start time
            start_time = message.created_at

            # Start the food fight
            food_fight = await self.food_fight_manager.start_food_fight(
                fight_id=fight_id,
                announcement_message_id=msg_id,
                channel_id=channel.id,
                valid_emojis=normalized_emojis,
                team_assignments=team_assignments,
                start_time=start_time,
            )

            await interaction.response.send_message(
                f"✅ Retroactive food fight added!\n"
                f"**Fight ID:** `{fight_id}`\n"
                f"**Participants:** {len(team_assignments)} users\n"
                f"**Teams:** {', '.join(normalized_emojis)}\n"
                f"**Start time:** {start_time.strftime('%Y-%m-%d %H:%M:%S UTC')} (message creation time)",
                ephemeral=True,
            )

        except Exception as e:
            logger.error(f"Error adding retroactive food fight: {e}", exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    f"An error occurred: {e}",
                    ephemeral=True,
                )
            else:
                await interaction.followup.send(
                    f"An error occurred: {e}",
                    ephemeral=True,
                )
