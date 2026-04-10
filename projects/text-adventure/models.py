"""Data models for The Shadow of Aldenmoor."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Item:
    id: str
    name: str
    description: str
    usable_on: str | None = None
    effect: str | None = None
    combinable_with: str | None = None
    combine_result: str | None = None


@dataclass
class Enemy:
    id: str
    name: str
    description: str
    hp: int
    max_hp: int
    attack: int
    defense: int
    defeat_flag: str
    loot: list[str] = field(default_factory=list)


@dataclass
class Choice:
    text: str
    target_room: str | None = None
    required_flags: list[str] = field(default_factory=list)
    forbidden_flags: list[str] = field(default_factory=list)
    required_items: list[str] = field(default_factory=list)
    sets_flag: str | None = None
    removes_item: str | None = None
    triggers_combat: str | None = None
    triggers_ending: str | None = None
    description: str = ""


@dataclass
class Room:
    id: str
    name: str
    description: str
    alt_descriptions: dict[str, str] = field(default_factory=dict)
    items: list[str] = field(default_factory=list)
    enemies: list[str] = field(default_factory=list)
    choices: list[Choice] = field(default_factory=list)


@dataclass
class Ending:
    id: str
    title: str
    text: str


@dataclass
class Player:
    name: str = "Adventurer"
    hp: int = 100
    max_hp: int = 100
    attack: int = 10
    defense: int = 3
    inventory: list[str] = field(default_factory=list)
    current_room: str = "village_square"
    flags: set[str] = field(default_factory=set)
    picked_up: set[str] = field(default_factory=set)
