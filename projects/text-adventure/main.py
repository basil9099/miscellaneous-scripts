#!/usr/bin/env python3
"""The Shadow of Aldenmoor - A Text Adventure Game."""

from models import Player
from save import has_save, load_game
from engine import game_loop


TITLE = r"""
 _____ _            ____  _               _                        __
|_   _| |__   ___  / ___|| |__   __ _  __| | _____      __   ___ / _|
  | | | '_ \ / _ \ \___ \| '_ \ / _` |/ _` |/ _ \ \ /\ / /  / _ \ |_
  | | | | | |  __/  ___) | | | | (_| | (_| | (_) \ V  V /  | (_) |  _|
  |_| |_| |_|\___| |____/|_| |_|\__,_|\__,_|\___/ \_/\_/    \___/|_|

                  _    _     _
                 / \  | | __| | ___ _ __  _ __ ___   ___   ___  _ __
                / _ \ | |/ _` |/ _ \ '_ \| '_ ` _ \ / _ \ / _ \| '__|
               / ___ \| | (_| |  __/ | | | | | | | | (_) | (_) | |
              /_/   \_\_|\__,_|\___|_| |_|_| |_| |_|\___/ \___/|_|
"""


def main() -> None:
    print(TITLE)
    print("  A Text Adventure Game")
    print("  " + "=" * 40)
    print()
    print("  1. New Game")
    if has_save():
        print("  2. Continue (Load Save)")
    print("  Q. Quit")
    print()

    while True:
        choice = input("  > ").strip().upper()

        if choice == "1":
            print()
            name = input("  What is your name, adventurer? ").strip()
            if not name:
                name = "Adventurer"
            player = Player(name=name)
            print(f"\n  Welcome, {player.name}. The village of Aldenmoor needs your help.\n")
            game_loop(player)
            break

        elif choice == "2" and has_save():
            player = load_game()
            if player:
                print(f"\n  Welcome back, {player.name}.\n")
                game_loop(player)
            else:
                print("  Failed to load save file.")
                continue
            break

        elif choice == "Q":
            print("\n  Farewell.\n")
            break

        else:
            print("  Invalid choice.")


if __name__ == "__main__":
    main()
