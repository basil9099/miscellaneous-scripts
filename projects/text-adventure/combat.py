"""Turn-based combat system for The Shadow of Aldenmoor."""

from __future__ import annotations

import random

from models import Enemy, Item, Player


def run_combat(player: Player, enemy: Enemy, items: dict[str, Item]) -> bool:
    """Run a combat encounter. Returns True if player wins, False on death."""
    enemy_hp = enemy.hp
    has_silver_dagger = "silver_dagger" in player.inventory

    print(f"\n{'=' * 50}")
    print(f"  COMBAT: {enemy.name}")
    print(f"{'=' * 50}")
    print(f"\n{enemy.description}\n")

    while enemy_hp > 0 and player.hp > 0:
        print(f"\n  Your HP: {player.hp}/{player.max_hp}  |  {enemy.name} HP: {enemy_hp}/{enemy.max_hp}")
        print()
        print("  1. Attack")
        print("  2. Defend (halve incoming damage)")
        print("  3. Use item")
        if has_silver_dagger and enemy.id == "shadow_knight":
            print("  4. Strike with Silver Dagger")
        print()

        choice = input("  > ").strip()
        defending = False

        if choice == "1":
            damage = max(1, player.attack - enemy.defense + random.randint(-2, 2))
            enemy_hp -= damage
            print(f"\n  You strike for {damage} damage!")

        elif choice == "2":
            defending = True
            print("\n  You raise your guard and brace for impact...")

        elif choice == "3":
            used = _use_combat_item(player, items)
            if not used:
                continue

        elif choice == "4" and has_silver_dagger and enemy.id == "shadow_knight":
            reduced_def = enemy.defense // 2
            damage = max(1, player.attack + 15 - reduced_def + random.randint(-2, 2))
            enemy_hp -= damage
            print(f"\n  The Silver Dagger blazes with holy light! You strike for {damage} damage!")

        else:
            print("\n  Invalid choice.")
            continue

        if enemy_hp <= 0:
            break

        # Enemy turn
        incoming = max(1, enemy.attack - player.defense + random.randint(-2, 2))
        if defending:
            incoming = max(1, incoming // 2)
            print(f"  {enemy.name} attacks, but your guard absorbs the blow! You take {incoming} damage.")
        else:
            print(f"  {enemy.name} strikes you for {incoming} damage!")
        player.hp -= incoming

    if player.hp <= 0:
        print(f"\n  You have been defeated by {enemy.name}...")
        return False

    print(f"\n{'=' * 50}")
    print(f"  VICTORY! You defeated {enemy.name}!")
    print(f"{'=' * 50}")

    player.flags.add(enemy.defeat_flag)

    for loot_id in enemy.loot:
        if loot_id in items:
            player.inventory.append(loot_id)
            print(f"  Obtained: {items[loot_id].name}")

    print()
    return True


def _use_combat_item(player: Player, items: dict[str, Item]) -> bool:
    """Use an item during combat. Returns True if item was used."""
    usable = [
        (item_id, items[item_id])
        for item_id in player.inventory
        if item_id in items and items[item_id].effect and items[item_id].effect.startswith("heal:")
    ]

    if not usable:
        print("\n  You have no usable items!")
        return False

    print("\n  Usable items:")
    for i, (item_id, item) in enumerate(usable, 1):
        print(f"    {i}. {item.name} ({item.effect})")
    print(f"    0. Cancel")

    choice = input("  > ").strip()
    if choice == "0":
        return False

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(usable):
            item_id, item = usable[idx]
            heal_amount = int(item.effect.split(":")[1])
            old_hp = player.hp
            player.hp = min(player.max_hp, player.hp + heal_amount)
            actual_heal = player.hp - old_hp
            player.inventory.remove(item_id)
            print(f"\n  You use {item.name} and restore {actual_heal} HP!")
            return True
    except (ValueError, IndexError):
        pass

    print("\n  Invalid choice.")
    return False
