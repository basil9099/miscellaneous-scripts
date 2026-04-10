"""Save and load system for The Shadow of Aldenmoor."""

from __future__ import annotations

import json
from pathlib import Path

from models import Player

SAVE_DIR = Path(__file__).parent / "saves"
SAVE_FILE = SAVE_DIR / "savegame.json"


def save_game(player: Player) -> None:
    """Save the current player state to disk."""
    SAVE_DIR.mkdir(exist_ok=True)
    data = {
        "name": player.name,
        "hp": player.hp,
        "max_hp": player.max_hp,
        "attack": player.attack,
        "defense": player.defense,
        "inventory": player.inventory,
        "current_room": player.current_room,
        "flags": sorted(player.flags),
        "picked_up": sorted(player.picked_up),
    }
    SAVE_FILE.write_text(json.dumps(data, indent=2))
    print("\n  Game saved!\n")


def load_game() -> Player | None:
    """Load a saved player state from disk. Returns None if no save exists."""
    if not SAVE_FILE.exists():
        return None
    try:
        data = json.loads(SAVE_FILE.read_text())
        return Player(
            name=data["name"],
            hp=data["hp"],
            max_hp=data["max_hp"],
            attack=data["attack"],
            defense=data["defense"],
            inventory=data["inventory"],
            current_room=data["current_room"],
            flags=set(data["flags"]),
            picked_up=set(data["picked_up"]),
        )
    except (json.JSONDecodeError, KeyError):
        print("  Warning: Save file is corrupted.")
        return None


def has_save() -> bool:
    """Check if a save file exists."""
    return SAVE_FILE.exists()
