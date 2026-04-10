# The Shadow of Aldenmoor

A terminal-based text adventure game. Explore the village of Aldenmoor, venture
through a dark forest into a cursed castle, and confront the Shadow Knight in a
quest to free the land from darkness.

## Requirements

Python 3.10+ (no external dependencies)

## Quick Start

```bash
cd projects/text-adventure
python main.py
```

## How to Play

Navigate by choosing numbered options from the menu. At any point you can also:

| Key | Action |
|-----|--------|
| `I` | Open inventory (examine, use, or combine items) |
| `S` | Save your progress |
| `Q` | Quit the game |

### Combat

Encounters use a turn-based system. Each round you can:

1. **Attack** -- deal damage based on your attack vs. enemy defense
2. **Defend** -- halve incoming damage for the round
3. **Use item** -- consume a healing potion mid-fight
4. **Silver Dagger strike** -- bonus option against the final boss if you found the dagger

### Items

Items are found throughout the world and looted from enemies. In the inventory
screen, use `E#` to examine, `U#` to use, or `C#` to combine an item (e.g.
`E1` examines the first item). Some items unlock new paths or are needed
to access areas.

Two amulet halves can be combined into a **Protective Amulet** that boosts
your defense.

## Endings

There are three endings depending on the choices you make and items you find:

- **Hero of Aldenmoor** -- defeat the Shadow Knight with the Silver Dagger
- **Pyrrhic Victory** -- defeat the Shadow Knight without the dagger
- **Redemption** -- find a way to save King Aldric from the curse

## Project Structure

```
text-adventure/
  main.py        # Entry point and main menu
  engine.py      # Game loop, room rendering, choice logic
  combat.py      # Turn-based combat system
  models.py      # Dataclasses for Player, Room, Item, Enemy, etc.
  save.py        # JSON save/load to saves/savegame.json
  data/
    rooms.json   # Room descriptions, choices, and endings
    items.json   # Item definitions and effects
    enemies.json # Enemy stats and loot tables
```

All game content (rooms, items, enemies, endings) is data-driven via the JSON
files in `data/`. To add new rooms or items, edit the JSON files -- no code
changes required.
