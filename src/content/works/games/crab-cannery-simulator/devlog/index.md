---
title:
date: 2026-03-12
type: devlog
project: crab-cannery-simulator
---

Currently, in Godot 4.6, Dialogic 2 basic functionality is working. Below is a list of what is currently implemented:
- start screen
- start game button
- quit button
- options button (does nothing)

The current components in the game include:
- player
- npc
- interaction_area
  - inherited by player, npc, and env interactable
- env_interactable

Some problems:
- How to determine, when two interactables are within range (equal range?) which is interacted with?
  - In a 3D game presumably there’d be a raycast from screen space, camera, or where the player character is facing
  - Perhaps I can implement it with the direction of the player character in 2D?
  - Currently have it done through `get_closest()` function in interaction_area
    - Seems to work fine
  - Player can repeatedly press the interact key to restart the current dialogue
- There is no state tracking, the same dialogue can occur over and over again
  - There isn’t any indication an option has been selected prior

Things to implement:
- State tracking
  - There is a global script, game_data which is autoloaded
- Barks
  - When within range, a bark will be automatically played… probably need to use labels for each character timeline “bark-1” or something which triggers on entering a body area or interaction area
    - Could implement a disco elysium style ring with tidbits of info
    - Would need to change the area/body erase distance, to keep it in the ring when the point of interest is walked away from…
    - Is that necessary?
