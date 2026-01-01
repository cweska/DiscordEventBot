"""Tests for FoodFightCog."""
import pytest
import discord
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from food_fight_cog import FoodFightCog, is_admin
from food_fight_manager import FoodFightManager


@pytest.mark.asyncio
async def test_is_admin_with_permissions(mock_guild):
    """Test is_admin returns True for user with admin permissions."""
    interaction = MagicMock(spec=discord.Interaction)
    interaction.guild = mock_guild
    interaction.user = MagicMock()
    interaction.user.guild_permissions = MagicMock()
    interaction.user.guild_permissions.administrator = True
    
    assert is_admin(interaction) is True


@pytest.mark.asyncio
async def test_is_admin_without_permissions(mock_guild):
    """Test is_admin returns False for user without admin permissions."""
    interaction = MagicMock(spec=discord.Interaction)
    interaction.guild = mock_guild
    interaction.user = MagicMock()
    interaction.user.guild_permissions = MagicMock()
    interaction.user.guild_permissions.administrator = False
    
    assert is_admin(interaction) is False


@pytest.mark.asyncio
async def test_is_admin_no_guild():
    """Test is_admin returns False when there's no guild."""
    interaction = MagicMock(spec=discord.Interaction)
    interaction.guild = None
    
    assert is_admin(interaction) is False


@pytest.mark.asyncio
async def test_foodfight_start_command_requires_admin(tmp_path: Path, mock_guild):
    """Test that foodfight-start command requires admin permissions."""
    file_path = tmp_path / "food_fights.json"
    manager = FoodFightManager(file_path)
    await manager.load()
    
    bot = MagicMock()
    cog = FoodFightCog(bot, manager)
    
    interaction = MagicMock(spec=discord.Interaction)
    interaction.guild = mock_guild
    interaction.user = MagicMock()
    interaction.user.guild_permissions = MagicMock()
    interaction.user.guild_permissions.administrator = False
    interaction.response = MagicMock()
    interaction.response.send_message = AsyncMock()
    
    # Call the callback function directly (not the command object)
    await cog.foodfight_start.callback(
        cog,
        interaction=interaction,
        message_id="123456",
        channel=None,
        emojis="🐕,🐈",
    )
    
    interaction.response.send_message.assert_called_once()
    call_args = interaction.response.send_message.call_args
    assert "administrator" in call_args[0][0].lower()


@pytest.mark.asyncio
async def test_foodfight_end_command_requires_admin(tmp_path: Path, mock_guild):
    """Test that foodfight-end command requires admin permissions."""
    file_path = tmp_path / "food_fights.json"
    manager = FoodFightManager(file_path)
    await manager.load()
    
    bot = MagicMock()
    cog = FoodFightCog(bot, manager)
    
    interaction = MagicMock(spec=discord.Interaction)
    interaction.guild = mock_guild
    interaction.user = MagicMock()
    interaction.user.guild_permissions = MagicMock()
    interaction.user.guild_permissions.administrator = False
    interaction.response = MagicMock()
    interaction.response.send_message = AsyncMock()
    
    # Call the callback function directly (not the command object)
    await cog.foodfight_end.callback(
        cog,
        interaction=interaction,
        fight_id="fight_123",
    )
    
    interaction.response.send_message.assert_called_once()
    call_args = interaction.response.send_message.call_args
    assert "administrator" in call_args[0][0].lower()


@pytest.mark.asyncio
async def test_foodfight_end_not_found(tmp_path: Path, mock_guild):
    """Test foodfight-end when fight doesn't exist."""
    file_path = tmp_path / "food_fights.json"
    manager = FoodFightManager(file_path)
    await manager.load()
    
    bot = MagicMock()
    cog = FoodFightCog(bot, manager)
    
    interaction = MagicMock(spec=discord.Interaction)
    interaction.guild = mock_guild
    interaction.user = MagicMock()
    interaction.user.guild_permissions = MagicMock()
    interaction.user.guild_permissions.administrator = True
    interaction.response = MagicMock()
    interaction.response.send_message = AsyncMock()
    
    # Call the callback function directly (not the command object)
    await cog.foodfight_end.callback(
        cog,
        interaction=interaction,
        fight_id="nonexistent_fight",
    )
    
    interaction.response.send_message.assert_called_once()
    call_args = interaction.response.send_message.call_args
    assert "not found" in call_args[0][0].lower() or "already ended" in call_args[0][0].lower()
