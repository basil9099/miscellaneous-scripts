# The Shadow of Aldenmoor

A text-based adventure game written in Python. Explore the village of Aldenmoor, uncover the mystery of the cursed castle, and face the Shadow Knight in this branching narrative with multiple endings.

## How to Play

```bash
cd projects/text-adventure
python3 main.py
```

No external dependencies required — just Python 3.10+.

## Features

- **8 explorable rooms** — village, forest, chapel, secret passage, castle gate, great hall, dungeon, and throne room
- **Turn-based combat** — attack, defend, or use items against 3 different enemies
- **Inventory & puzzles** — find keys, combine amulet halves, unlock hidden areas
- **Branching narrative** — your choices and discoveries determine which of 3 endings you reach
- **Save/load** — save your progress and pick up where you left off

## Endings

| Ending | How to Reach |
|---|---|
| **Hero of Aldenmoor** | Defeat the Shadow Knight with the Silver Dagger |
| **Pyrrhic Victory** | Defeat the Shadow Knight without the Silver Dagger |
| **Redemption** | Learn the king's history and reason with him instead of fighting |

## Project Structure

```
text-adventure/
├── main.py          # Entry point (title screen, new/load game)
├── engine.py        # Game loop, room display, choice filtering, inventory
├── combat.py        # Turn-based combat system
├── models.py        # Dataclasses (Player, Room, Item, Enemy, Choice, Ending)
├── save.py          # JSON save/load system
└── data/
    ├── rooms.json   # Room descriptions, choices, and endings
    ├── items.json   # Item definitions and effects
    └── enemies.json # Enemy stats and loot tables
```
