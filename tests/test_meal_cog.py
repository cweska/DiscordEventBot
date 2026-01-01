import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from meal_cog import (
    HumorLoader,
    MealCog,
    StatsManager,
)


@pytest.mark.asyncio
async def test_stats_manager_streaks(tmp_path: Path):
    stats_path = tmp_path / "stats.json"
    manager = StatsManager(stats_path)
    await manager.load()

    user_id = 123
    day_one = datetime(2025, 1, 1, tzinfo=timezone.utc)

    first = await manager.record_meal(user_id, day_one)
    assert first.count == 1
    assert first.streak_current == 1

    # Same day: streak should not double-count
    second = await manager.record_meal(user_id, day_one)
    assert second.count == 2
    assert second.streak_current == 1

    # Next day: streak increments
    next_day = day_one + timedelta(days=1)
    third = await manager.record_meal(user_id, next_day)
    assert third.count == 3
    assert third.streak_current == 2

    # Skip a day: streak resets
    later = day_one + timedelta(days=3)
    fourth = await manager.record_meal(user_id, later)
    assert fourth.count == 4
    assert fourth.streak_current == 1

    # Data persisted to disk
    saved = json.loads(stats_path.read_text(encoding="utf-8"))
    assert str(user_id) in saved


def test_humor_loader_fallback(tmp_path: Path):
    """If the humor file is missing, we still return a line."""
    loader = HumorLoader(tmp_path / "missing.txt")
    line = loader.get_random_line()
    assert line  # non-empty fallback


@pytest.mark.asyncio
async def test_handle_modal_submission_posts_embed(tmp_path: Path):
    stats_path = tmp_path / "stats.json"
    humor_path = tmp_path / "humor.txt"
    humor_path.write_text("first line\nsecond line\n", encoding="utf-8")

    stats = StatsManager(stats_path)
    await stats.load()
    humor = HumorLoader(humor_path)

    channel = MagicMock(spec=discord.TextChannel)
    channel.id = 1440141058410283039
    channel.send = AsyncMock()

    bot = MagicMock()
    bot.get_channel = MagicMock(return_value=channel)

    user = MagicMock(spec=discord.User)
    user.id = 42
    user.name = "Chef Tester"
    user.mention = "<@42>"
    user.display_avatar = MagicMock()
    user.display_avatar.url = "http://avatar.test/image.png"

    interaction = MagicMock(spec=discord.Interaction)
    interaction.client = bot
    interaction.user = user
    interaction.response = MagicMock()
    interaction.response.is_done = MagicMock(return_value=False)
    interaction.response.defer = AsyncMock()
    interaction.followup = MagicMock()
    interaction.followup.send = AsyncMock()

    photo = MagicMock(spec=discord.Attachment)
    photo.url = "http://example.com/photo.png"
    photo.filename = "photo.png"
    photo.content_type = "image/png"

    cog = MealCog(
        bot=bot,
        humor_loader=humor,
        stats_manager=stats,
        meal_channel_id=channel.id,
        food_fight_manager=None,  # Not needed for this test
    )

    await cog.handle_modal_submission(
        interaction=interaction,
        dish_name="Test Dish",
        note="Tasty",
        photo=photo,
    )

    channel.send.assert_called_once()
    interaction.response.defer.assert_called_once()
    interaction.followup.send.assert_called_once()
    assert stats.data[str(user.id)]["count"] == 1

