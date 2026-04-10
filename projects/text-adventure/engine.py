"""Game engine for The Shadow of Aldenmoor."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

from combat import run_combat
from models import Choice, Enemy, Ending, Item, Player, Room
from save import save_game


DATA_DIR = Path(__file__).parent / "data"
TEXT_WIDTH = 78


def load_data() -> tuple[dict[str, Room], dict[str, Item], dict[str, Enemy], dict[str, Ending]]:
    """Load all game data from JSON files."""
    with open(DATA_DIR / "rooms.json") as f:
        rooms_data = json.load(f)
    with open(DATA_DIR / "items.json") as f:
        items_data = json.load(f)
    with open(DATA_DIR / "enemies.json") as f:
        enemies_data = json.load(f)

    items = {}
    for item_id, d in items_data["items"].items():
        items[item_id] = Item(id=item_id, **d)

    enemies = {}
    for enemy_id, d in enemies_data["enemies"].items():
        enemies[enemy_id] = Enemy(id=enemy_id, **d)

    rooms = {}
    for room_id, d in rooms_data["rooms"].items():
        choices = [Choice(**c) for c in d.get("choices", [])]
        rooms[room_id] = Room(
            id=room_id,
            name=d["name"],
            description=d["description"],
            alt_descriptions=d.get("alt_descriptions", {}),
            items=d.get("items", []),
            enemies=d.get("enemies", []),
            choices=choices,
        )

    endings = {}
    for ending_id, d in rooms_data.get("endings", {}).items():
        endings[ending_id] = Ending(id=ending_id, **d)

    return rooms, items, enemies, endings


def _wrap(text: str) -> str:
    """Wrap text to fit the terminal width."""
    paragraphs = text.split("\n")
    wrapped = []
    for para in paragraphs:
        if para.strip():
            wrapped.append(textwrap.fill(para.strip(), width=TEXT_WIDTH))
        else:
            wrapped.append("")
    return "\n".join(wrapped)


def _get_room_description(room: Room, player: Player) -> str:
    """Get the appropriate room description based on player flags."""
    for flag, desc in room.alt_descriptions.items():
        if flag in player.flags:
            return desc
    return room.description


def _get_visible_choices(room: Room, player: Player) -> list[Choice]:
    """Filter choices to only those the player can currently see."""
    visible = []
    for choice in room.choices:
        if choice.required_flags and not all(f in player.flags for f in choice.required_flags):
            continue
        if choice.forbidden_flags and any(f in player.flags for f in choice.forbidden_flags):
            continue
        if choice.required_items and not all(i in player.inventory for i in choice.required_items):
            continue
        visible.append(choice)
    return visible


def _get_available_items(room: Room, player: Player, items: dict[str, Item]) -> list[tuple[str, Item]]:
    """Get items in the room that haven't been picked up yet."""
    available = []
    for item_id in room.items:
        if item_id not in player.picked_up and item_id in items:
            available.append((item_id, items[item_id]))
    return available


def _display_room(room: Room, player: Player) -> None:
    """Display the current room."""
    print(f"\n{'=' * TEXT_WIDTH}")
    print(f"  {room.name}")
    print(f"{'=' * TEXT_WIDTH}")
    print()
    print(_wrap(_get_room_description(room, player)))
    print()


def _show_inventory(player: Player, items: dict[str, Item]) -> None:
    """Show inventory sub-menu with examine, use, and combine options."""
    while True:
        print(f"\n{'-' * 40}")
        print("  INVENTORY")
        print(f"{'-' * 40}")

        if not player.inventory:
            print("  Your pack is empty.")
            print()
            return

        inv_items = []
        for item_id in player.inventory:
            if item_id in items:
                inv_items.append((item_id, items[item_id]))

        for i, (item_id, item) in enumerate(inv_items, 1):
            print(f"  {i}. {item.name}")

        print()
        print("  E#) Examine item  |  U#) Use item  |  C#) Combine item  |  0) Close")
        print()
        action = input("  > ").strip().upper()

        if action == "0":
            return

        if len(action) < 2:
            print("  Invalid input. Use E1, U1, C1, etc.")
            continue

        cmd = action[0]
        try:
            idx = int(action[1:]) - 1
        except ValueError:
            print("  Invalid input.")
            continue

        if idx < 0 or idx >= len(inv_items):
            print("  Invalid item number.")
            continue

        item_id, item = inv_items[idx]

        if cmd == "E":
            print(f"\n  {item.name}")
            print(f"  {_wrap(item.description)}")

        elif cmd == "U":
            if item.effect and item.effect.startswith("heal:"):
                heal_amount = int(item.effect.split(":")[1])
                old_hp = player.hp
                player.hp = min(player.max_hp, player.hp + heal_amount)
                actual = player.hp - old_hp
                player.inventory.remove(item_id)
                print(f"\n  You use {item.name} and restore {actual} HP! ({player.hp}/{player.max_hp})")
            elif item.effect and item.effect.startswith("unlock:"):
                print(f"\n  You can't use that here. Try using it in the right location.")
            elif item.effect and item.effect.startswith("defense:"):
                bonus = int(item.effect.split(":")[1])
                player.defense += bonus
                player.inventory.remove(item_id)
                player.flags.add("amulet_equipped")
                print(f"\n  You put on the {item.name}. Defense increased by {bonus}! (Defense: {player.defense})")
            else:
                print(f"\n  You can't use that right now.")

        elif cmd == "C":
            if not item.combinable_with:
                print(f"\n  {item.name} can't be combined with anything.")
                continue
            if item.combinable_with in player.inventory:
                other = items[item.combinable_with]
                result = items.get(item.combine_result)
                if result:
                    player.inventory.remove(item_id)
                    player.inventory.remove(item.combinable_with)
                    player.inventory.append(item.combine_result)
                    print(f"\n  You combine {item.name} and {other.name}...")
                    print(f"  Created: {result.name}!")
                else:
                    print(f"\n  Something went wrong.")
            else:
                print(f"\n  You don't have the matching piece to combine with {item.name}.")
        else:
            print("  Invalid command. Use E, U, or C.")


def _handle_choice(
    choice: Choice,
    player: Player,
    rooms: dict[str, Room],
    items: dict[str, Item],
    enemies: dict[str, Enemy],
    endings: dict[str, Ending],
) -> str | None:
    """Process a player's choice. Returns an ending ID if the game should end."""
    if choice.description:
        print()
        print(_wrap(choice.description))

    if choice.triggers_combat:
        enemy = enemies.get(choice.triggers_combat)
        if enemy:
            won = run_combat(player, enemy, items)
            if not won:
                return "death"

    if choice.sets_flag:
        player.flags.add(choice.sets_flag)

    if choice.removes_item and choice.removes_item in player.inventory:
        player.inventory.remove(choice.removes_item)

    # Handle unlocking altar -> silver dagger pickup
    if choice.sets_flag == "altar_unlocked":
        if "silver_dagger" not in player.inventory and "silver_dagger" not in player.picked_up:
            player.inventory.append("silver_dagger")
            player.picked_up.add("silver_dagger")
            print(f"\n  Obtained: Silver Dagger!")

    if choice.triggers_ending:
        return choice.triggers_ending

    if choice.target_room:
        player.current_room = choice.target_room

    return None


def game_loop(player: Player) -> None:
    """Main game loop."""
    rooms, items, enemies, endings = load_data()

    while True:
        room = rooms.get(player.current_room)
        if not room:
            print(f"  Error: Room '{player.current_room}' not found!")
            break

        _display_room(room, player)

        # Show available items
        available_items = _get_available_items(room, player, items)
        visible_choices = _get_visible_choices(room, player)

        # Build action menu
        actions: list[tuple[str, object]] = []
        for item_id, item in available_items:
            actions.append(("pickup", (item_id, item)))
        for choice in visible_choices:
            actions.append(("choice", choice))

        # Display menu
        print(f"  HP: {player.hp}/{player.max_hp}  |  Items: {len(player.inventory)}")
        print()
        idx = 1
        for action_type, action_data in actions:
            if action_type == "pickup":
                _, item = action_data
                print(f"  {idx}. Pick up {item.name}")
            else:
                print(f"  {idx}. {action_data.text}")
            idx += 1

        print(f"  I.  Inventory")
        print(f"  S.  Save game")
        print(f"  Q.  Quit")
        print()

        selection = input("  > ").strip().upper()

        if selection == "I":
            _show_inventory(player, items)
            continue

        if selection == "S":
            save_game(player)
            continue

        if selection == "Q":
            print("\n  Farewell, adventurer. Until next time.\n")
            break

        try:
            sel_idx = int(selection) - 1
        except ValueError:
            print("\n  Invalid choice.\n")
            continue

        if sel_idx < 0 or sel_idx >= len(actions):
            print("\n  Invalid choice.\n")
            continue

        action_type, action_data = actions[sel_idx]

        if action_type == "pickup":
            item_id, item = action_data
            player.inventory.append(item_id)
            player.picked_up.add(item_id)
            print(f"\n  You pick up the {item.name}.")
            # If it's the old scroll, auto-read for lore flag
            if item_id == "old_scroll" and item.effect and item.effect.startswith("unlock:"):
                flag = item.effect.split(":")[1]
                player.flags.add(flag)
                print(f"  You unroll the scroll and read its contents...")
        else:
            choice = action_data
            result = _handle_choice(choice, player, rooms, items, enemies, endings)
            if result == "death":
                print()
                print(_wrap("Your vision fades as darkness closes in. The Shadow of Aldenmoor claims another soul..."))
                print("\n  === GAME OVER ===\n")
                break
            elif result and result in endings:
                ending = endings[result]
                print(f"\n{'=' * TEXT_WIDTH}")
                print(f"  ENDING: {ending.title}")
                print(f"{'=' * TEXT_WIDTH}")
                print()
                print(_wrap(ending.text))
                print()
                break
