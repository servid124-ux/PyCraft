<div align="center">

```
██████╗ ██╗   ██╗ ██████╗██████╗  █████╗ ███████╗████████╗
██╔══██╗╚██╗ ██╔╝██╔════╝██╔══██╗██╔══██╗██╔════╝╚══██╔══╝
██████╔╝ ╚████╔╝██║     ██████╔╝███████║█████╗     ██║   
██╔═══╝   ╚██╔╝  ██║     ██╔══██╗██╔══██║██╔══╝     ██║   
██║        ██║   ╚██████╗██║  ██║██║  ██║██║        ██║   
╚═╝        ╚═╝    ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝        ╚═╝   
```

**Minecraft Classic server — built from scratch in Python**

![Version](https://img.shields.io/badge/version-0.2.7-blue?style=flat-square)
![Protocol](https://img.shields.io/badge/protocol-Classic%200x07-green?style=flat-square)
![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20Termux-orange?style=flat-square)
![Python](https://img.shields.io/badge/python-3.10%2B-yellow?style=flat-square)

</div>

---

PyCraft is a Minecraft Classic server written entirely in Python, compatible with ClassiCube. It runs on Linux and Android via Termux with no external dependencies.

---

## Installation

**Android (Termux)**

```bash
pkg install python unzip
wget https://github.com/user-attachments/files/29407007/PyCraft_v0_2_7.zip
unzip PyCraft_v0.2.7.zip -d PyCraft && cd PyCraft
sh Start.sh
```

**Linux**

```bash
sudo apt install python3 unzip wget
wget https://github.com/user-attachments/files/29407007/PyCraft_v0_2_7.zip
unzip PyCraft_v0.2.7.zip -d PyCraft && cd PyCraft
sh Start.sh
```

---

## Connecting

Open ClassiCube → Options → Servers → Direct connect and enter your server address on port `25565`. To connect from another device on the same network, use your local IP instead of `localhost`.

---

## Configuration

Edit `server.properties` after the first launch. The defaults are sensible — the only things you'll likely want to change are `server-name`, `motd`, and `public`.

```properties
server-name=A Minecraft Classic Server
motd=Welcome!
port=25565
max-players=32
public=false
world-name=world
world-size-x=128
world-size-y=64
world-size-z=128
world-generator=normal
cpe-blocks=true
save-interval=300
connection-timeout=30
max-connections-per-ip=3
max-violations-before-ban=5
```

Set `public=true` to list your server on classicube.net. Use `world-generator=flat` for a flat world on first creation. `save-interval` is in seconds.

---

## Commands

```
/help               list all commands
/players            show online players
/spawn              teleport to spawn
/pos                show your coordinates
/me <text>          action message
/msg <player>       private message
/r <text>           reply to last message
/plugins            list loaded plugins
```

**OP only**

```
/tp <player>        teleport to player
/kick <player>      kick a player
/ban / /unban       manage bans
/op / /deop         manage operators
/setspawn           set world spawn
/save               force world save
/reload             reload all plugins
```

---

## Plugins

Drop a `.py` file in the `plugins/` folder. Plugins load on startup and can be reloaded live with `/reload`.

```python
from plugin.plugin_base import Plugin

class MyPlugin(Plugin):
    name    = "MyPlugin"
    version = "1.0.0"
    author  = "You"

    def on_enable(self):
        self.log("Hello from MyPlugin!")
```

Two example plugins are included in the `plugins/` folder:

**Login** — optional account system with `/register` and `/login`. Passwords are hashed with PBKDF2-SHA256 (200k iterations). Unauthenticated players are frozen until they log in. The server itself has no built-in password system — drop this plugin to enable it.

**Homes** — home teleportation with `/sethome [name]`, `/home [name]`, `/delhome <name>`, and `/homes`. Configurable max homes per player.

---

## CPE

PyCraft supports the **CustomBlocks** extension (level 1). ClassiCube clients negotiate this automatically — no setup needed.

All 16 CPE blocks (IDs 50–65) are fully defined with correct `CollideType` and `DrawType` values derived from the ClassiCube client source:

| ID | Name | ID | Name |
|----|------|----|------|
| 50 | Cobblestone Slab | 58 | Deep Blue |
| 51 | Rope | 59 | Turquoise |
| 52 | Sandstone | 60 | Ice |
| 53 | Snow | 61 | Ceramic Tile |
| 54 | Fire | 62 | Magma |
| 55 | Light Pink | 63 | Pillar |
| 56 | Forest Green | 64 | Crate |
| 57 | Brown | 65 | Stone Brick |

Special properties: Ice uses `CollideType.ICE` (slippery), Rope uses `CollideType.CLIMB`, Magma and Fire emit light, Water/Lava use `CollideType.WATER`/`LAVA`.

---

## Changelog

**v0.2.7**
— Corrected all CPE block definitions (IDs 50–65) with proper `CollideType` and `DrawType` enumerations from ClassiCube source  
— Added `BlockID` class with named constants for all 66 blocks (0–65) and `CPE_MIN`/`CPE_MAX` sentinels  
— Added `block/ids.py`, `block/fluids.py` (fluid simulation tick), `block/gravity.py` (sand/gravel fall)  
— Added `_ansi.py` —colored logger shared by server, plugin manager, and plugins  
— Added example `Login` plugin (PBKDF2-SHA256 password hashing, player freeze on join)  
— Added example `Homes` plugin (`/sethome`, `/home`, `/delhome`, `/homes` with configurable limits)

**v0.2.6**
— Fixed `BufferUnderrun` crash on player movement (`PlayerTeleport 0x08` body size corrected)

**v0.2.5**
— Initial public release

---

<div align="center">

[github.com/servid124-ux/PyCraft](https://github.com/servid124-ux/PyCraft) · Classic protocol 7 · Python

</div>
