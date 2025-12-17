import asyncio
import json
import logging
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

logger = logging.getLogger(__name__)


HUMOR_FALLBACK = "Cooking achievement unlocked."


class HumorLoader:
    """Loads and serves random humor lines for meal posts."""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.lines = self._load_lines()

    def _load_lines(self) -> list[str]:
        try:
            if self.file_path.exists():
                with self.file_path.open("r", encoding="utf-8") as f:
                    lines = [line.strip() for line in f if line.strip()]
                    if lines:
                        return lines
            logger.warning(f"Humor file {self.file_path} missing or empty; using fallback.")
        except Exception as e:
            logger.warning(f"Failed to load humor lines from {self.file_path}: {e}")
        return [HUMOR_FALLBACK]

    def get_random_line(self) -> str:
        return random.choice(self.lines)


@dataclass
class MealStats:
    count: int
    streak_current: int
    streak_best: int
    last_post_date_utc: Optional[str]


class StatsManager:
    """Manages meal counts and streaks, persisted to JSON."""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.data: dict[str, dict] = {}
        self._lock = asyncio.Lock()

    async def load(self) -> None:
        """Load stats from disk, creating an empty file if missing."""
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            if not self.file_path.exists():
                self.file_path.write_text("{}", encoding="utf-8")
                self.data = {}
                return

            text = self.file_path.read_text(encoding="utf-8").strip()
            self.data = json.loads(text) if text else {}
        except Exception as e:
            logger.error(f"Failed to load stats file {self.file_path}: {e}")
            self.data = {}

    async def record_meal(self, user_id: int, now: datetime) -> MealStats:
        """Update stats for a user when they log a meal."""
        today = now.astimezone(timezone.utc).date()

        async with self._lock:
            current = self.data.get(
                str(user_id),
                {
                    "count": 0,
                    "streak_current": 0,
                    "streak_best": 0,
                    "last_post_date_utc": None,
                },
            )

            count = current["count"] + 1
            streak_current = current["streak_current"]
            streak_best = current["streak_best"]
            last_date_str = current["last_post_date_utc"]

            if last_date_str:
                try:
                    last_date = datetime.fromisoformat(last_date_str).date()
                except ValueError:
                    last_date = None
            else:
                last_date = None

            if last_date is None:
                streak_current = 1
            elif last_date == today:
                # Same day: keep current streak
                streak_current = max(streak_current, 1)
            elif last_date == (today - timedelta(days=1)):
                streak_current = streak_current + 1 if streak_current else 1
            else:
                streak_current = 1

            streak_best = max(streak_best, streak_current)

            updated = MealStats(
                count=count,
                streak_current=streak_current,
                streak_best=streak_best,
                last_post_date_utc=today.isoformat(),
            )

            self.data[str(user_id)] = updated.__dict__
            await self._save_locked()
            return updated

    async def _save_locked(self) -> None:
        """Persist current stats to disk (call while holding the lock)."""
        try:
            payload = json.dumps(self.data, indent=2)

            def _write():
                self.file_path.write_text(payload, encoding="utf-8")

            await asyncio.to_thread(_write)
        except Exception as e:
            logger.error(f"Failed to write stats file {self.file_path}: {e}")


def build_meal_embed(
    dish_name: str,
    humor_line: str,
    note: Optional[str],
    photo_url: str,
    user: discord.abc.User,
    stats: MealStats,
) -> discord.Embed:
    """Construct the meal embed for posting."""
    description_parts = [humor_line]
    if note:
        description_parts.append(f"Note: {note}")

    embed = discord.Embed(
        title=dish_name,
        description="\n\n".join(description_parts),
        color=discord.Color.blurple(),
    )

    # Author info for attribution
    try:
        avatar_url = user.display_avatar.url  # type: ignore[attr-defined]
    except Exception:
        avatar_url = None

    embed.set_author(name=user.name, icon_url=avatar_url)  # type: ignore[arg-type]
    embed.set_image(url=photo_url)
    embed.set_footer(
        text=f"Meals: {stats.count} | Streak: {stats.streak_current} (best {stats.streak_best})"
    )
    return embed


class MealModal(discord.ui.Modal, title="Log a Meal"):
    """Modal for collecting meal details."""

    dish_name = discord.ui.TextInput(
        label="Dish name",
        placeholder="e.g., Spicy tofu stir fry",
        max_length=200,
    )
    note = discord.ui.TextInput(
        label="Optional note",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=500,
    )

    def __init__(
        self,
        cog: "MealCog",
        photo: discord.Attachment,
    ):
        super().__init__(timeout=180)
        self.cog = cog
        self.photo = photo

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await self.cog.handle_modal_submission(
            interaction=interaction,
            dish_name=str(self.dish_name.value).strip(),
            note=str(self.note.value).strip() if self.note.value else None,
            photo=self.photo,
        )


class MealCog(commands.Cog):
    """Cog handling meal submissions via modal + slash command."""

    def __init__(
        self,
        bot: commands.Bot,
        humor_loader: HumorLoader,
        stats_manager: StatsManager,
        meal_channel_id: int,
    ):
        self.bot = bot
        self.humor_loader = humor_loader
        self.stats_manager = stats_manager
        self.meal_channel_id = meal_channel_id

    @staticmethod
    def _is_image_attachment(attachment: discord.Attachment) -> bool:
        if attachment.content_type:
            return attachment.content_type.startswith("image/")
        return any(str(attachment.filename).lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".gif", ".webp"])

    @app_commands.command(name="cooked", description="Log a cooked meal with a photo")
    @app_commands.describe(photo="Photo of the dish")
    async def meal_command(
        self,
        interaction: discord.Interaction,
        photo: discord.Attachment,
    ) -> None:
        """Slash command entrypoint that launches the modal."""
        if not self._is_image_attachment(photo):
            await interaction.response.send_message(
                "Please attach an image file (png/jpg/gif/webp).",
                ephemeral=True,
            )
            return

        try:
            await interaction.response.send_modal(MealModal(self, photo))
        except Exception as e:
            logger.error(f"Failed to open meal modal: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "Sorry, something went wrong opening the meal form.",
                    ephemeral=True,
                )

    async def handle_modal_submission(
        self,
        interaction: discord.Interaction,
        dish_name: str,
        note: Optional[str],
        photo: discord.Attachment,
    ) -> None:
        """Handle modal submission: update stats, build embed, post to channel."""
        try:
            # Defer early to avoid the 3s Discord interaction timeout
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)

            channel = interaction.client.get_channel(self.meal_channel_id)
            if channel is None or not isinstance(channel, discord.TextChannel):
                await interaction.followup.send(
                    "I can't find the #meal-journal channel.",
                    ephemeral=True,
                )
                logger.error(f"Meal channel {self.meal_channel_id} not found or not a text channel.")
                return

            humor_line = self.humor_loader.get_random_line()
            stats = await self.stats_manager.record_meal(
                user_id=interaction.user.id,
                now=discord.utils.utcnow(),
            )

            embed = build_meal_embed(
                dish_name=dish_name or "Untitled Dish",
                humor_line=humor_line,
                note=note,
                photo_url=photo.url,
                user=interaction.user,
                stats=stats,
            )

            await channel.send(embed=embed)

            # Acknowledge the modal submission
            await interaction.followup.send(
                f"Logged **{dish_name or 'your meal'}** to <#{self.meal_channel_id}>!",
                ephemeral=True,
            )
        except Exception as e:
            logger.error(f"Error handling meal submission: {e}")
            send_error = (
                interaction.followup.send
                if interaction.response.is_done()
                else interaction.response.send_message
            )
            await send_error(
                "Sorry, something went wrong logging your meal.",
                ephemeral=True,
            )

