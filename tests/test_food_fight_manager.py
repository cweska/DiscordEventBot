"""Tests for FoodFightManager."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from food_fight_manager import FoodFightManager, FoodFight


@pytest.mark.asyncio
async def test_load_creates_file_if_missing(tmp_path: Path):
    """Loading should create an empty file if it doesn't exist."""
    file_path = tmp_path / "food_fights.json"
    manager = FoodFightManager(file_path)
    await manager.load()
    
    assert file_path.exists()
    data = json.loads(file_path.read_text(encoding="utf-8"))
    assert "active_fights" in data
    assert "completed_fights" in data


@pytest.mark.asyncio
async def test_start_food_fight(tmp_path: Path):
    """Test starting a food fight."""
    file_path = tmp_path / "food_fights.json"
    manager = FoodFightManager(file_path)
    await manager.load()
    
    fight_id = "fight_123"
    start_time = datetime.now(timezone.utc)
    food_fight = await manager.start_food_fight(
        fight_id=fight_id,
        announcement_message_id=123456,
        channel_id=789012,
        valid_emojis=["🐕", "🐈"],
        team_assignments={100: "🐕", 200: "🐈"},
        start_time=start_time,
    )
    
    assert food_fight.fight_id == fight_id
    assert food_fight.team_assignments[100] == "🐕"
    assert food_fight.team_assignments[200] == "🐈"
    assert food_fight.dishes_counted[100] == 0
    assert food_fight.dishes_counted[200] == 0
    assert food_fight.end_time is None
    
    # Check persistence
    active_fight = await manager.get_active_fight(fight_id)
    assert active_fight is not None
    assert active_fight.fight_id == fight_id


@pytest.mark.asyncio
async def test_record_dish(tmp_path: Path):
    """Test recording dishes for users in active food fights."""
    file_path = tmp_path / "food_fights.json"
    manager = FoodFightManager(file_path)
    await manager.load()
    
    start_time = datetime.now(timezone.utc) - timedelta(hours=1)
    await manager.start_food_fight(
        fight_id="fight_1",
        announcement_message_id=111,
        channel_id=222,
        valid_emojis=["🐕", "🐈"],
        team_assignments={100: "🐕", 200: "🐈"},
        start_time=start_time,
    )
    
    # Record a dish for user 100
    dish_time = datetime.now(timezone.utc)
    counted_fights = await manager.record_dish(user_id=100, dish_time=dish_time)
    
    assert "fight_1" in counted_fights
    active_fight = await manager.get_active_fight("fight_1")
    assert active_fight.dishes_counted[100] == 1
    assert active_fight.dishes_counted[200] == 0


@pytest.mark.asyncio
async def test_record_dish_only_counts_after_start_time(tmp_path: Path):
    """Test that dishes logged before food fight start are not counted."""
    file_path = tmp_path / "food_fights.json"
    manager = FoodFightManager(file_path)
    await manager.load()
    
    start_time = datetime.now(timezone.utc)
    await manager.start_food_fight(
        fight_id="fight_1",
        announcement_message_id=111,
        channel_id=222,
        valid_emojis=["🐕"],
        team_assignments={100: "🐕"},
        start_time=start_time,
    )
    
    # Try to record a dish before the start time
    dish_time = start_time - timedelta(hours=1)
    counted_fights = await manager.record_dish(user_id=100, dish_time=dish_time)
    
    assert "fight_1" not in counted_fights
    active_fight = await manager.get_active_fight("fight_1")
    assert active_fight.dishes_counted[100] == 0
    
    # Record a dish after start time
    dish_time_after = start_time + timedelta(minutes=1)
    counted_fights = await manager.record_dish(user_id=100, dish_time=dish_time_after)
    
    assert "fight_1" in counted_fights
    active_fight = await manager.get_active_fight("fight_1")
    assert active_fight.dishes_counted[100] == 1


@pytest.mark.asyncio
async def test_record_dish_only_counts_for_participants(tmp_path: Path):
    """Test that dishes are only counted for users who are in the food fight."""
    file_path = tmp_path / "food_fights.json"
    manager = FoodFightManager(file_path)
    await manager.load()
    
    start_time = datetime.now(timezone.utc)
    await manager.start_food_fight(
        fight_id="fight_1",
        announcement_message_id=111,
        channel_id=222,
        valid_emojis=["🐕"],
        team_assignments={100: "🐕"},
        start_time=start_time,
    )
    
    # User 999 is not in the food fight
    dish_time = datetime.now(timezone.utc)
    counted_fights = await manager.record_dish(user_id=999, dish_time=dish_time)
    
    assert "fight_1" not in counted_fights
    active_fight = await manager.get_active_fight("fight_1")
    assert 999 not in active_fight.dishes_counted


@pytest.mark.asyncio
async def test_end_food_fight(tmp_path: Path):
    """Test ending a food fight."""
    file_path = tmp_path / "food_fights.json"
    manager = FoodFightManager(file_path)
    await manager.load()
    
    start_time = datetime.now(timezone.utc)
    await manager.start_food_fight(
        fight_id="fight_1",
        announcement_message_id=111,
        channel_id=222,
        valid_emojis=["🐕"],
        team_assignments={100: "🐕"},
        start_time=start_time,
    )
    
    end_time = datetime.now(timezone.utc)
    completed_fight = await manager.end_food_fight("fight_1", end_time)
    
    assert completed_fight is not None
    assert completed_fight.end_time is not None
    assert completed_fight.end_time == end_time.isoformat()
    
    # Should not be in active fights anymore
    active_fight = await manager.get_active_fight("fight_1")
    assert active_fight is None
    
    # Should be in completed fights (check via get_tallies)
    tallies = await manager.get_tallies("fight_1")
    assert tallies is not None
    assert tallies["end_time"] is not None


@pytest.mark.asyncio
async def test_get_tallies(tmp_path: Path):
    """Test getting tallies for a food fight."""
    file_path = tmp_path / "food_fights.json"
    manager = FoodFightManager(file_path)
    await manager.load()
    
    start_time = datetime.now(timezone.utc) - timedelta(hours=1)
    await manager.start_food_fight(
        fight_id="fight_1",
        announcement_message_id=111,
        channel_id=222,
        valid_emojis=["🐕", "🐈"],
        team_assignments={100: "🐕", 200: "🐈", 300: "🐕"},
        start_time=start_time,
    )
    
    # Record some dishes
    dish_time = datetime.now(timezone.utc)
    await manager.record_dish(100, dish_time)  # 🐕 team
    await manager.record_dish(100, dish_time)  # 🐕 team (2 total)
    await manager.record_dish(200, dish_time)  # 🐈 team (1 total)
    await manager.record_dish(300, dish_time)  # 🐕 team (1 total)
    
    tallies = await manager.get_tallies("fight_1")
    
    assert tallies is not None
    assert "🐕" in tallies["teams"]
    assert "🐈" in tallies["teams"]
    assert tallies["teams"]["🐕"]["total_dishes"] == 3  # 2 + 1
    assert tallies["teams"]["🐈"]["total_dishes"] == 1
    assert len(tallies["teams"]["🐕"]["participants"]) == 2
    assert len(tallies["teams"]["🐈"]["participants"]) == 1


@pytest.mark.asyncio
async def test_multiple_active_fights(tmp_path: Path):
    """Test that multiple food fights can be active simultaneously."""
    file_path = tmp_path / "food_fights.json"
    manager = FoodFightManager(file_path)
    await manager.load()
    
    start_time = datetime.now(timezone.utc)
    await manager.start_food_fight(
        fight_id="fight_1",
        announcement_message_id=111,
        channel_id=222,
        valid_emojis=["🐕"],
        team_assignments={100: "🐕"},
        start_time=start_time,
    )
    
    await manager.start_food_fight(
        fight_id="fight_2",
        announcement_message_id=333,
        channel_id=444,
        valid_emojis=["🍕"],
        team_assignments={100: "🍕"},  # Same user in different fight
        start_time=start_time,
    )
    
    # User 100 is in both fights
    dish_time = datetime.now(timezone.utc)
    counted_fights = await manager.record_dish(user_id=100, dish_time=dish_time)
    
    assert "fight_1" in counted_fights
    assert "fight_2" in counted_fights
    
    fight1 = await manager.get_active_fight("fight_1")
    fight2 = await manager.get_active_fight("fight_2")
    assert fight1.dishes_counted[100] == 1
    assert fight2.dishes_counted[100] == 1


@pytest.mark.asyncio
async def test_persistence(tmp_path: Path):
    """Test that food fights persist across manager instances."""
    file_path = tmp_path / "food_fights.json"
    
    # Create and start a fight
    manager1 = FoodFightManager(file_path)
    await manager1.load()
    
    start_time = datetime.now(timezone.utc)
    await manager1.start_food_fight(
        fight_id="fight_1",
        announcement_message_id=111,
        channel_id=222,
        valid_emojis=["🐕"],
        team_assignments={100: "🐕"},
        start_time=start_time,
    )
    
    # Create new manager and load
    manager2 = FoodFightManager(file_path)
    await manager2.load()
    
    active_fight = await manager2.get_active_fight("fight_1")
    assert active_fight is not None
    assert active_fight.fight_id == "fight_1"
    assert active_fight.team_assignments[100] == "🐕"
