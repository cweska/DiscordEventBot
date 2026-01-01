"""Food Fight Manager for tracking team assignments and dish counts."""
import asyncio
import json
import logging
import random
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)


@dataclass
class FoodFight:
    """Represents an active or completed food fight."""
    fight_id: str
    announcement_message_id: int
    channel_id: int
    valid_emojis: List[str]
    team_assignments: Dict[int, str]  # user_id -> emoji
    dishes_counted: Dict[int, int]  # user_id -> count
    start_time: str  # ISO format UTC timestamp
    end_time: Optional[str] = None  # ISO format UTC timestamp, None if still active


class FoodFightManager:
    """Manages food fights, team assignments, and dish counting."""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.active_fights: Dict[str, FoodFight] = {}
        self.completed_fights: Dict[str, FoodFight] = {}
        self._lock = asyncio.Lock()

    async def load(self) -> None:
        """Load food fights from disk, creating an empty file if missing."""
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            if not self.file_path.exists():
                initial_data = {"active_fights": {}, "completed_fights": {}}
                self.file_path.write_text(json.dumps(initial_data, indent=2), encoding="utf-8")
                self.active_fights = {}
                self.completed_fights = {}
                return

            text = self.file_path.read_text(encoding="utf-8").strip()
            if text:
                data = json.loads(text)
            else:
                data = {}
            
            # Load active fights
            active_data = data.get("active_fights", {})
            self.active_fights = {}
            for fight_id, fight_data in active_data.items():
                # Convert team_assignments keys from strings to ints (JSON keys are strings)
                if "team_assignments" in fight_data:
                    fight_data["team_assignments"] = {
                        int(user_id): emoji for user_id, emoji in fight_data["team_assignments"].items()
                    }
                # Convert dishes_counted keys from strings to ints
                if "dishes_counted" in fight_data:
                    fight_data["dishes_counted"] = {
                        int(user_id): count for user_id, count in fight_data["dishes_counted"].items()
                    }
                self.active_fights[fight_id] = FoodFight(**fight_data)
            
            # Load completed fights
            completed_data = data.get("completed_fights", {})
            self.completed_fights = {}
            for fight_id, fight_data in completed_data.items():
                # Convert team_assignments keys from strings to ints
                if "team_assignments" in fight_data:
                    fight_data["team_assignments"] = {
                        int(user_id): emoji for user_id, emoji in fight_data["team_assignments"].items()
                    }
                # Convert dishes_counted keys from strings to ints
                if "dishes_counted" in fight_data:
                    fight_data["dishes_counted"] = {
                        int(user_id): count for user_id, count in fight_data["dishes_counted"].items()
                    }
                self.completed_fights[fight_id] = FoodFight(**fight_data)
            
            logger.info(f"Loaded {len(self.active_fights)} active and {len(self.completed_fights)} completed food fights")
        except Exception as e:
            logger.error(f"Failed to load food fights file {self.file_path}: {e}")
            self.active_fights = {}
            self.completed_fights = {}

    async def start_food_fight(
        self,
        fight_id: str,
        announcement_message_id: int,
        channel_id: int,
        valid_emojis: List[str],
        team_assignments: Dict[int, str],
        start_time: datetime,
    ) -> FoodFight:
        """
        Start a new food fight.
        
        Args:
            fight_id: Unique identifier for this food fight
            announcement_message_id: Discord message ID of the announcement
            channel_id: Channel ID where announcement is posted
            valid_emojis: List of valid team emoji strings
            team_assignments: Dictionary mapping user_id to emoji
            start_time: When the food fight started (used for filtering dishes)
            
        Returns:
            The created FoodFight object
        """
        async with self._lock:
            food_fight = FoodFight(
                fight_id=fight_id,
                announcement_message_id=announcement_message_id,
                channel_id=channel_id,
                valid_emojis=valid_emojis,
                team_assignments=team_assignments,
                dishes_counted={user_id: 0 for user_id in team_assignments.keys()},
                start_time=start_time.astimezone(timezone.utc).isoformat(),
                end_time=None,
            )
            self.active_fights[fight_id] = food_fight
            await self._save_locked()
            logger.info(f"Started food fight {fight_id} with {len(team_assignments)} participants")
            return food_fight

    async def end_food_fight(self, fight_id: str, end_time: Optional[datetime] = None) -> Optional[FoodFight]:
        """
        End an active food fight and move it to completed.
        
        Args:
            fight_id: The food fight ID to end
            end_time: When the food fight ended (defaults to now)
            
        Returns:
            The completed FoodFight, or None if not found
        """
        async with self._lock:
            if fight_id not in self.active_fights:
                logger.warning(f"Food fight {fight_id} not found in active fights")
                return None
            
            food_fight = self.active_fights.pop(fight_id)
            food_fight.end_time = (end_time or datetime.now(timezone.utc)).isoformat()
            self.completed_fights[fight_id] = food_fight
            await self._save_locked()
            logger.info(f"Ended food fight {fight_id}")
            return food_fight

    async def get_active_fight(self, fight_id: str) -> Optional[FoodFight]:
        """Get an active food fight by ID."""
        async with self._lock:
            return self.active_fights.get(fight_id)

    async def get_all_active_fights(self) -> Dict[str, FoodFight]:
        """Get all active food fights."""
        async with self._lock:
            return self.active_fights.copy()

    async def record_dish(self, user_id: int, dish_time: datetime) -> List[str]:
        """
        Record a dish for a user in all active food fights they're participating in.
        
        Args:
            user_id: The user who logged the dish
            dish_time: When the dish was logged
            
        Returns:
            List of fight_ids where the dish was counted
        """
        dish_time_utc = dish_time.astimezone(timezone.utc)
        counted_fights = []
        
        async with self._lock:
            for fight_id, fight in self.active_fights.items():
                # Check if user is in this fight
                if user_id not in fight.team_assignments:
                    continue
                
                # Check if dish was logged after fight started
                fight_start = datetime.fromisoformat(fight.start_time)
                if dish_time_utc < fight_start:
                    continue
                
                # Increment dish count
                if user_id not in fight.dishes_counted:
                    fight.dishes_counted[user_id] = 0
                fight.dishes_counted[user_id] += 1
                counted_fights.append(fight_id)
            
            if counted_fights:
                await self._save_locked()
                logger.info(f"Recorded dish for user {user_id} in {len(counted_fights)} active food fights")
        
        return counted_fights

    async def get_tallies(self, fight_id: str) -> Optional[Dict[str, Dict]]:
        """
        Get team tallies for a food fight.
        
        Returns:
            Dictionary with structure:
            {
                "teams": {
                    "emoji": {
                        "total_dishes": int,
                        "participants": [
                            {"user_id": int, "dishes": int, "username": str (if available)}
                        ]
                    }
                },
                "start_time": str,
                "end_time": str or None
            }
            Or None if fight not found
        """
        async with self._lock:
            # Check active fights first
            food_fight = self.active_fights.get(fight_id)
            if not food_fight:
                # Check completed fights
                food_fight = self.completed_fights.get(fight_id)
            
            if not food_fight:
                return None
            
            # Build team tallies
            teams: Dict[str, Dict] = {}
            
            for emoji in food_fight.valid_emojis:
                teams[emoji] = {
                    "total_dishes": 0,
                    "participants": []
                }
            
            for user_id, emoji in food_fight.team_assignments.items():
                if emoji not in teams:
                    continue
                
                dish_count = food_fight.dishes_counted.get(user_id, 0)
                teams[emoji]["total_dishes"] += dish_count
                teams[emoji]["participants"].append({
                    "user_id": user_id,
                    "dishes": dish_count,
                })
            
            return {
                "teams": teams,
                "start_time": food_fight.start_time,
                "end_time": food_fight.end_time,
            }

    async def _save_locked(self) -> None:
        """Persist current food fights to disk (call while holding the lock)."""
        try:
            data = {
                "active_fights": {
                    fight_id: asdict(fight)
                    for fight_id, fight in self.active_fights.items()
                },
                "completed_fights": {
                    fight_id: asdict(fight)
                    for fight_id, fight in self.completed_fights.items()
                }
            }
            payload = json.dumps(data, indent=2)

            def _write():
                self.file_path.write_text(payload, encoding="utf-8")

            await asyncio.to_thread(_write)
            logger.debug(f"Food fights saved to {self.file_path}")
        except Exception as e:
            logger.error(f"Failed to write food fights file {self.file_path}: {e}")

    def _resolve_multiple_team_emojis(self, user_reactions: List[str], valid_emojis: List[str]) -> Optional[str]:
        """
        If a user has multiple valid team emoji reactions, randomly pick one.
        
        Args:
            user_reactions: List of emoji strings the user reacted with
            valid_emojis: List of valid team emoji strings
            
        Returns:
            The randomly selected emoji, or None if no valid reactions
        """
        valid_user_reactions = [emoji for emoji in user_reactions if emoji in valid_emojis]
        if not valid_user_reactions:
            return None
        return random.choice(valid_user_reactions)
