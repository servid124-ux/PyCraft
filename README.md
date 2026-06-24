<div align="center">

# PyCraft
**Minecraft Classic server — built from scratch in Python**

![Version](https://img.shields.io/badge/version-0.2.6-blue)
![Protocol](https://img.shields.io/badge/protocol-Classic%200x07-green)
![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20Android%20Termux-orange)
![Python](https://img.shields.io/badge/python-3.10%2B-yellow)

</div>

---

## Features

- Classic protocol 7 — compatible with ClassiCube
- **CPE CustomBlocks** — 16 extra blocks (IDs 50–65) for CPE clients
- World generation — `normal` with caves, ores, water, trees / `flat`
- Fluid physics — water and lava spread
- External plugin system — hot-reloadable `.py` plugins
- Private messages — `/msg` and `/r`
- OP system with colored chat prefix
- Auto-restart on crash
- Runs on Android via Termux

---

## Installation

### Android (Termux)

```bash
pkg install python unzip
wget https://github.com/user-attachments/files/29273324/PyCraft_v0.2.6.zip
unzip PyCraft_v0.2.6.zip -d PyCraft
cd PyCraft
sh Start.sh
```

### Linux

```bash
sudo apt install python3 unzip wget
wget https://github.com/user-attachments/files/29273324/PyCraft_v0.2.6.zip
unzip PyCraft_v0.2.6.zip -d PyCraft
cd PyCraft
sh Start.sh
```

---

## Connecting

Open **ClassiCube** → Options → Servers → Direct connect

```
Host: localhost
Port: 25565
```

To connect from another device on the same network, replace `localhost` with your local IP address.

---

## Commands

| Command | Description |
|---|---|
| `/help` | List all available commands |
| `/players` | Show connected players |
| `/spawn` | Teleport to world spawn |
| `/pos` | Display your current coordinates |
| `/me <text>` | Send an action message |
| `/msg <player> <text>` | Send a private message |
| `/r <text>` | Reply to last private message |
| `/plugins` | List loaded plugins |

**OP only**

| Command | Description |
|---|---|
| `/tp <player>` | Teleport to a player |
| `/kick <player>` | Kick a player |
| `/ban <player>` | Ban a player |
| `/unban <player>` | Unban a player |
| `/op <player>` | Grant operator status |
| `/deop <player>` | Revoke operator status |
| `/setspawn` | Set world spawn to your position |
| `/save` | Manually save the world |
| `/reload` | Reload all plugins |

---

## Configuration

Edit `server.properties` after the first launch.

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

| Option | Values | Description |
|---|---|---|
| `server-name` | string | Name shown in the server list |
| `motd` | string | Message shown on connect |
| `port` | number | Port to listen on |
| `max-players` | number | Maximum simultaneous players |
| `public` | `true` / `false` | List server on classicube.net |
| `world-name` | string | World save file name |
| `world-size-x/y/z` | number | World dimensions in blocks |
| `world-generator` | `normal` / `flat` | World type on first creation |
| `cpe-blocks` | `true` / `false` | Enable CPE CustomBlocks extension |
| `save-interval` | seconds | Auto-save interval |
| `connection-timeout` | seconds | Idle connection timeout |
| `max-connections-per-ip` | number | Max simultaneous connections per IP |
| `max-violations-before-ban` | number | Auto-ban threshold for rule violations |

---

## Plugins

Place `.py` plugin files in the `plugins/` folder.
Plugins are loaded automatically on startup and can be reloaded with `/reload`.

```python
from plugin.plugin_base import Plugin

class MyPlugin(Plugin):
    name    = "MyPlugin"
    version = "1.0.0"
    author  = "You"

    def on_enable(self):
        self.log("Hello from MyPlugin!")
```

---

## CPE Support

PyCraft supports the **CustomBlocks** extension (level 1).
ClassiCube clients automatically negotiate this on connect — no setup required.
Enables 16 additional blocks (IDs 50–65): Sandstone, Snow, Ice, Cactus, Magma, Pillar, and more.

---

## Changelog

### v0.2.6
- Fixed `BufferUnderrun` crash on player movement — `PlayerTeleport (0x08)` body size corrected from 8 → 9 bytes

### v0.2.5
- Initial public release

---

<div align="center">

Made with Python · Classic protocol 7 · [github.com/servid124-ux/PyCraft](https://github.com/servid124-ux/PyCraft)

</div>
