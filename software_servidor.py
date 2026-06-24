

import hashlib

import os

import random

import socket

import string

import struct

import sys

import threading

import time

import traceback

import urllib.parse

import urllib.request


CODE_DIR = os.path.dirname(os.path.abspath(__file__))

for _sub in ("network", "world", "block", "plugin", "api", "command"):

    sys.path.insert(0, os.path.join(CODE_DIR, _sub))


BASE_DIR = os.path.dirname(CODE_DIR)


from protocolo import ProtocolConfig, UserType, BlockChangeMode              

from packet import (              

    Identification, LevelInitialize, LevelDataChunk, LevelFinalize,

    SetBlockClient, SetBlockServer, PlayerTeleport, Message, Ping,

    DisconnectPlayer, UpdateUserType, read_packet, send_packet,

    ExtInfo, ExtEntry, CustomBlockSupportLevel,

)

from world import World              

from block import can_place, can_break, get_block, needs_support

import fluids              
from heartbeat import heartbeat_loop
from commands import handle_command

import gravity              

from Player import Player, PlayerManager, SELF_ID              

import playerdata              


SOFTWARE_NAME = "PyCraft"

SOFTWARE_VERSION = "0.2.6"


MIN_NAME_LENGTH = 2


_SALT_CHARS = string.ascii_letters + string.digits


def _gen_salt(length: int = 16) -> str:

    return "".join(random.choices(_SALT_CHARS, k=length))


def log(msg: str, level: str = "INFO") -> None:


    ts = time.strftime("%H:%M:%S")

    print(f"[{ts}] [Server thread/{level}]: {msg}", flush=True)


DEFAULT_PROPERTIES = {

    "server-name":              "A Minecraft Classic Server",

    "motd":                     "Welcome!",

    "port":                     str(ProtocolConfig.DEFAULT_PORT),

    "max-players":              "32",

    "public":                   "false",

    "world-name":               "world",

    "world-size-x":             "128",

    "world-size-y":             "64",

    "world-size-z":             "128",

    "world-generator":          "normal",
    "cpe-blocks":               "true",

    "save-interval":            "300",

                                                                         
    "connection-timeout":       "30",                                  

    "max-connections-per-ip":   "3",                                         

    "max-violations-before-ban":"5",                                            

}


def load_properties(path: str) -> dict:

    if not os.path.exists(path):

        save_properties(path, DEFAULT_PROPERTIES)

        return dict(DEFAULT_PROPERTIES)

    props = dict(DEFAULT_PROPERTIES)

    with open(path, "r", encoding="utf-8") as f:

        for line in f:

            line = line.strip()

            if not line or line.startswith("#") or "=" not in line:

                continue

            key, _, value = line.partition("=")

            props[key.strip()] = value.strip()

    return props


def save_properties(path: str, props: dict) -> None:

    with open(path, "w", encoding="utf-8") as f:

        f.write(f"# {SOFTWARE_NAME} - server.properties\n")

        f.write(f"# generado {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        for key, value in props.items():

            f.write(f"{key}={value}\n")


def load_list(path: str) -> set:

    if not os.path.exists(path):

        open(path, "w", encoding="utf-8").close()

        return set()

    with open(path, "r", encoding="utf-8") as f:

        return {line.strip().lower() for line in f if line.strip() and not line.startswith("#")}


def append_to_list(path: str, entry: str) -> None:

    with open(path, "a", encoding="utf-8") as f:

        f.write(entry.strip().lower() + "\n")


def remove_from_list(path: str, entry: str) -> None:

    entry = entry.strip().lower()

    if not os.path.exists(path):

        return

    with open(path, "r", encoding="utf-8") as f:

        lines = [line for line in f if line.strip().lower() != entry]

    with open(path, "w", encoding="utf-8") as f:

        f.writelines(lines)


DEFAULT_SOFTWARE_YML = {

    "software":         SOFTWARE_NAME,

    "version":          SOFTWARE_VERSION,

    "protocol":         ProtocolConfig.VERSION,

    "plugins-enabled":  [],

}


def load_software_yml(path: str) -> dict:

    if not os.path.exists(path):

        save_software_yml(path, DEFAULT_SOFTWARE_YML)

        return dict(DEFAULT_SOFTWARE_YML)

    data = dict(DEFAULT_SOFTWARE_YML)

    current_list_key = None

    with open(path, "r", encoding="utf-8") as f:

        for raw_line in f:

            line = raw_line.rstrip("\n")

            stripped = line.strip()

            if not stripped or stripped.startswith("#"):

                continue

            if line.startswith("  - "):

                if current_list_key is not None:

                    data[current_list_key].append(stripped[2:].strip())

                continue

            if ":" in stripped:

                key, _, value = stripped.partition(":")

                key = key.strip()

                value = value.strip()

                if value == "":

                    data[key] = []

                    current_list_key = key

                else:

                    current_list_key = None

                    data[key] = int(value) if value.isdigit() else value

    return data


def save_software_yml(path: str, data: dict) -> None:

    with open(path, "w", encoding="utf-8") as f:

        f.write(f"# {SOFTWARE_NAME} - software.yml\n")

        for key, value in data.items():

            if isinstance(value, list):

                f.write(f"{key}:\n")

                for item in value:

                    f.write(f"  - {item}\n")

            else:

                f.write(f"{key}: {value}\n")


def verify_mppass(salt: str, username: str, mppass: str) -> bool:


    expected = hashlib.md5((salt + username).encode("utf-8")).hexdigest()

    return expected == mppass.strip()


def _get_public_ip() -> str | None:


    try:

        req = urllib.request.Request(

            "https://api.ipify.org",

            headers={"User-Agent": SOFTWARE_NAME},

        )

        with urllib.request.urlopen(req, timeout=5) as resp:

            ip = resp.read().decode("utf-8").strip()

            return ip if ip else None

    except Exception:

        return None





class _IpTracker:


    WINDOW = 10.0                                         


    def __init__(self, max_conns: int = 3, max_violations: int = 5):

        self.max_conns      = max_conns

        self.max_violations = max_violations

        self._conns:      dict[str, list[float]] = {}

        self._violations: dict[str, int]         = {}

        self._lock = threading.Lock()


    def check_rate(self, ip: str) -> bool:


        now = time.time()

        with self._lock:

            times = [t for t in self._conns.get(ip, [])

                     if now - t < self.WINDOW]

            times.append(now)

            self._conns[ip] = times

        return len(times) <= self.max_conns


    def add_violation(self, ip: str) -> int:


        with self._lock:

            n = self._violations.get(ip, 0) + 1

            self._violations[ip] = n

        return n


    def violations(self, ip: str) -> int:

        return self._violations.get(ip, 0)


    def reset_violations(self, ip: str) -> None:

        with self._lock:

            self._violations.pop(ip, None)


class Server:

    def __init__(self, base_dir: str = BASE_DIR):

        self.base_dir = base_dir

        self.props = load_properties(os.path.join(base_dir, "server.properties"))

        self.software_meta = load_software_yml(os.path.join(base_dir, "software.yml"))


        self.ops = load_list(os.path.join(base_dir, "ops.txt"))

        self.banned_players = load_list(os.path.join(base_dir, "banned.txt"))

        self.banned_ips = load_list(os.path.join(base_dir, "banned-ips.txt"))

        self.whitelist = load_list(os.path.join(base_dir, "white-list.txt"))


        world_path = os.path.join(base_dir, "worlds", self.props["world-name"] + ".cw")

        self.world = World.load_or_create(

            world_path,

            name=self.props["world-name"],

            size_x=int(self.props["world-size-x"]),

            size_y=int(self.props["world-size-y"]),

            size_z=int(self.props["world-size-z"]),

            generator=self.props["world-generator"],

        )

        self.world_path = world_path


        self.players = PlayerManager()

        self._sock: socket.socket | None = None

        self._running = False

        self.plugin_manager = None


        self.SOFTWARE_NAME = SOFTWARE_NAME
        self.salt = _gen_salt()

        self._listed_url: str = ""

        self._start_time: float = 0.0


        self._pm_last: dict[str, int] = {}

        self._ip_tracker = _IpTracker(
            max_conns=int(self.props.get("max-connections-per-ip", "3")),
            max_violations=int(self.props.get("max-violations-before-ban", "5")),
        )

    def log(self, msg: str, level: str = "INFO") -> None:
        log(msg, level=level)


    def is_banned_name(self, name: str) -> bool:

        return name.lower() in self.banned_players


    def is_banned_ip(self, ip: str) -> bool:

        return ip.lower() in self.banned_ips


    def whitelist_enabled(self) -> bool:

        return len(self.whitelist) > 0


    def is_whitelisted(self, name: str) -> bool:

        return name.lower() in self.whitelist


    def is_op(self, name: str) -> bool:

        return name.lower() in self.ops


    def set_op(self, name: str, value: bool) -> None:

        name_lower = name.strip().lower()

        ops_path = os.path.join(self.base_dir, "ops.txt")

        if value:

            self.ops.add(name_lower)

            append_to_list(ops_path, name_lower)

        else:

            self.ops.discard(name_lower)

            remove_from_list(ops_path, name_lower)


        target = self.players.find_by_name(name)

        if target is not None:

            target.op = value

            target.send(UpdateUserType(UserType.OP if value else UserType.NORMAL))

            target.send_message("&aYou are now an operator" if value else "&cYou are no longer an operator")


    def run(self) -> None:

        self._start_time = time.time()

        log(f"Starting {SOFTWARE_NAME} server version {SOFTWARE_VERSION} (Classic 0x07)")

        log("Loading properties")

        log(f"Default world generator: {self.props['world-generator']}")


        port = int(self.props["port"])

        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self._sock.bind(("0.0.0.0", port))

        self._sock.listen(8)

        self._running = True

        log(f"Starting {SOFTWARE_NAME} server on *:{port}")


        log(f'Preparing level "{self.world.name}"')

        log(f"Preparing start region for level "

            f"(size {self.world.size_x}x{self.world.size_y}x{self.world.size_z})")


        try:

            from manager import PluginManager

            self.plugin_manager = PluginManager(self, BASE_DIR)

            self.plugin_manager.load_all()

        except Exception as exc:

            log(f"No se pudieron cargar los plugins: {exc}", level="WARN")


        if self.props.get("public", "false").lower() == "true":

            log(f"Server salt: {self.salt}")

            pub_ip = _get_public_ip()

            if pub_ip:

                log(f"Public IP detected: {pub_ip} — make sure port "

                    f"{self.props['port']} is open (port forwarding on your router)")

            else:

                log("Could not detect public IP — server may not be reachable "

                    "from the internet without port forwarding", level="WARN")


            threading.Thread(target=heartbeat_loop, args=(self,), daemon=True).start()

        else:

            log("Server is not set to public, not sending heartbeat")

            log(f"To connect from ClassiCube: Options → Servers → Direct connect → "

                f"localhost:{self.props['port']}")


        threading.Thread(target=self._fluid_loop,   daemon=True).start()

        threading.Thread(target=self._gravity_loop, daemon=True).start()


        save_interval = int(self.props.get("save-interval", "300"))

        if save_interval > 0:

            threading.Thread(target=self._autosave_loop, daemon=True).start()


        elapsed = time.time() - self._start_time

        log(f'Done ({elapsed:.3f}s)! For help, type "help" or "?"')


        threading.Thread(target=self._console_loop, daemon=True).start()


        try:

            while self._running:

                client_sock, addr = self._sock.accept()

                threading.Thread(

                    target=self._handle_client,

                    args=(client_sock, addr),

                    daemon=True,

                ).start()

        except KeyboardInterrupt:

            pass

        finally:

            self.shutdown()


    def _console_loop(self) -> None:

        while self._running:

            try:

                line = input()

            except EOFError:

                break

            self._on_console_command(line)


    def _on_console_command(self, raw: str) -> None:

        parts = raw.strip().split()

        if not parts:

            return

        cmd, args = parts[0].lower(), parts[1:]


        if cmd in ("help", "?"):

            log("Comandos: help, players, op <j>, deop <j>, kick <j>, ban <j>, "

                "unban <j>, banip <ip>, say <msg>, save, time, stop")

        elif cmd == "players":

            names = ", ".join(p.name for p in self.players.get_all()) or "(none)"

            log(f"Players online ({len(self.players.get_all())}): {names}")

        elif cmd == "op" and args:

            self.set_op(args[0], True); log(f"{args[0]} is now an operator")

        elif cmd == "deop" and args:

            self.set_op(args[0], False); log(f"{args[0]} is no longer an operator")

        elif cmd == "kick" and args:

            reason = " ".join(args[1:]) or "Kicked from console"

            t = self.players.find_by_name(args[0])

            if t: t.kick(reason); log(f"{args[0]} was kicked")

            else: log(f"Player '{args[0]}' not found", level="WARN")

        elif cmd == "ban" and args:

            name = args[0]

            append_to_list(os.path.join(self.base_dir, "banned.txt"), name)

            self.banned_players.add(name.lower())

            t = self.players.find_by_name(name)

            if t: t.kick("Banned")

            log(f"{name} was banned")

        elif cmd == "unban" and args:

            remove_from_list(os.path.join(self.base_dir, "banned.txt"), args[0])

            self.banned_players.discard(args[0].lower())

            log(f"{args[0]} was unbanned")

        elif cmd == "banip" and args:

            append_to_list(os.path.join(self.base_dir, "banned-ips.txt"), args[0])

            self.banned_ips.add(args[0].lower())

            log(f"IP {args[0]} banned")

        elif cmd == "say" and args:

            msg = " ".join(args)

            self.players.broadcast_message(f"&e[Server] {msg}")

            log(f"[Server] {msg}")

        elif cmd == "save":

            self._do_save()

        elif cmd == "time":

            uptime = int(time.time() - self._start_time)

            h, m, s = uptime // 3600, (uptime % 3600) // 60, uptime % 60

            log(f"Uptime: {h:02d}:{m:02d}:{s:02d}")

        elif cmd == "stop":

            log("Stopping the server...")

            self._running = False

            if self._sock:

                try: self._sock.close()

                except OSError: pass

        else:

            log(f"Unknown command: '{cmd}'. Type 'help'.", level="WARN")


    def _fluid_loop(self) -> None:

        while self._running:

            time.sleep(fluids.TICK_INTERVAL)

            try:

                changes = fluids.tick(self.world)

            except Exception:

                traceback.print_exc(); continue

            for x, y, z, block_id in changes:

                self.players.broadcast(SetBlockServer(x, y, z, block_id))


    def _gravity_loop(self) -> None:

        while self._running:

            time.sleep(gravity.TICK_INTERVAL)

            try:

                changes = gravity.tick(self.world)

            except Exception:

                traceback.print_exc(); continue

            for x, y, z, block_id in changes:

                self.players.broadcast(SetBlockServer(x, y, z, block_id))


    def _autosave_loop(self) -> None:

        interval = int(self.props.get("save-interval", "300"))

        while self._running:

            time.sleep(interval)

            if self._running:

                self._do_save()


    def _do_save(self) -> None:

        try:

            self.world.save(self.world_path)

            log("World saved")

        except Exception as exc:

            log(f"Error al guardar el mundo: {exc}", level="WARN")


    def shutdown(self) -> None:

        log("Stopping the server")

        self._running = False

        for p in self.players.get_all():

            playerdata.save_position(

                self.base_dir, p.uuid, p.name, p.x, p.y, p.z, p.yaw, p.pitch

            )

            p.kick("Server closing")

        if self._sock:

            self._sock.close()

        log("Saving worlds")

        self._do_save()

        log("Done")


    def _handle_client(self, sock: socket.socket, addr) -> None:

        ip     = addr[0]

        player = None


        timeout = int(self.props.get("connection-timeout", "30"))

        sock.settimeout(float(timeout))


        try:

                                                                           
            if self.is_banned_ip(ip):

                send_packet(sock, DisconnectPlayer("Your IP is banned"))

                return


            if not self._ip_tracker.check_rate(ip):

                send_packet(sock, DisconnectPlayer("Too many connections"))

                log(f"Rate limit exceeded: {ip} — connection refused", level="WARN")

                return


            handshake = read_packet(sock)

            if not isinstance(handshake, Identification):

                got = type(handshake).__name__

                log(f"{ip} lost connection: Internal Exception: "

                    f"DecoderException: Expected Identification, got {got}",

                    level="WARN")

                n = self._ip_tracker.add_violation(ip)

                self._maybe_autoban(ip, n)

                return


            proto = handshake.protocol_version

            if proto != ProtocolConfig.VERSION:

                if proto < ProtocolConfig.VERSION:

                                                         
                    send_packet(sock, DisconnectPlayer(

                        f"Outdated client (protocol {proto}). "

                        f"This server requires Classic protocol 7. "

                        f"Update your client at classicube.net"

                    ))

                    log(

                        f"{ip} disconnected: outdated protocol {proto} "

                        f"(server requires 7)",

                        level="WARN",

                    )

                else:

                                                                                        
                    send_packet(sock, DisconnectPlayer(

                        "Outdated server! New PyCraft update may be out. Be patient."

                    ))

                    log(

                        f"{ip} disconnected: server is outdated "

                        f"(client uses protocol {proto}, server is 7)",

                        level="WARN",

                    )

                return

            cpe_enabled = self.props.get("cpe-blocks", "true").lower() == "true"
            client_cpe  = (handshake.user_type == 0x42)
            cpe_negotiated = False

            if cpe_enabled and client_cpe:
                send_packet(sock, ExtInfo(SOFTWARE_NAME, 1))
                send_packet(sock, ExtEntry("CustomBlocks", 1))
                client_ext_info = read_packet(sock)
                if isinstance(client_ext_info, ExtInfo):
                    client_exts = set()
                    for _ in range(client_ext_info.extension_count):
                        entry = read_packet(sock)
                        if isinstance(entry, ExtEntry):
                            client_exts.add(entry.ext_name)
                    if "CustomBlocks" in client_exts:
                        send_packet(sock, CustomBlockSupportLevel(1))
                        lvl = read_packet(sock)
                        if isinstance(lvl, CustomBlockSupportLevel):
                            cpe_negotiated = True
                            log(f"{ip} CPE CustomBlocks level {lvl.level} negotiated")

            name = handshake.username.strip()

            if not name or len(name) < MIN_NAME_LENGTH:

                send_packet(sock, DisconnectPlayer(

                    f"Invalid name (minimum {MIN_NAME_LENGTH} characters)"

                ))

                return


            if self.props.get("public", "false").lower() == "true":

                if not verify_mppass(self.salt, name, handshake.verification_key):

                    send_packet(sock, DisconnectPlayer(

                        "You need a ClassiCube account. "

                        "Connect from classicube.net or the official client"

                    ))

                    log(f"Unverified name: {name} ({ip}) — "

                        "player did not use the official client or has no account",

                        level="WARN")

                    return


            if self.is_banned_name(name):

                send_packet(sock, DisconnectPlayer("You are banned")); return

            if self.whitelist_enabled() and not self.is_whitelisted(name):

                send_packet(sock, DisconnectPlayer("You are not whitelisted")); return


            existing = self.players.find_by_name(name)

            if existing is not None:

                existing.kick("Someone logged in with your name")


            max_players = int(self.props.get("max-players", "32"))

            player = self.players.join(sock, name, max_players)

            if player is None:

                send_packet(sock, DisconnectPlayer("Server is full")); return


            player.op = self.is_op(name)
            player.cpe_blocks = cpe_negotiated


            self._ip_tracker.reset_violations(ip)


            send_packet(sock, Identification(

                ProtocolConfig.VERSION,

                self.props["server-name"],

                self.props["motd"],

                UserType.OP if player.op else UserType.NORMAL,

            ))


            self._send_world(player)


            saved = playerdata.load_position(self.base_dir, player.uuid)

            if saved is not None:

                sx, sy, sz, syaw, spitch = saved

                player.set_spawn(sx, sy, sz, syaw, spitch)

            else:

                player.set_spawn(

                    self.world.spawn_x, self.world.spawn_y, self.world.spawn_z,

                    self.world.spawn_yaw, self.world.spawn_pitch,

                )

            player.send_self_spawn()

            self.players.introduce(player)

            self.players.broadcast_message(f"&e{name} joined the game")

            log(f"{name}[/{ip}] logged in with entity id {player.player_id} "

                f"at ({player.x:.1f}, {player.y:.1f}, {player.z:.1f})")

            log(f"UUID of player {name} is {player.uuid}")

            if self.plugin_manager:

                self.plugin_manager.fire_player_join(player)


            threading.Thread(

                target=self._ping_loop, args=(player,), daemon=True

            ).start()


            self._client_loop(player)


        except (TimeoutError, socket.timeout):

                                                     
            who = player.name if player else ip

            log(f"{who} lost connection: Timed out")


        except (ConnectionResetError, ConnectionAbortedError):

                                                        
            who = player.name if player else ip

            log(f"{who} lost connection: Connection reset by peer")


        except BrokenPipeError:

                                                                 
            who = player.name if player else ip

            log(f"{who} lost connection: Broken pipe")


        except EOFError:

                                                                       
            who = player.name if player else ip

            log(f"{who} lost connection: End of stream")


        except struct.error as exc:

                                                           
            who = player.name if player else ip

            log(f"{who} lost connection: Internal Exception: "

                f"DecoderException: {exc}", level="WARN")

            n = self._ip_tracker.add_violation(ip)

            self._maybe_autoban(ip, n)


        except (ValueError, UnicodeDecodeError) as exc:

                                                   
            who = player.name if player else ip

            log(f"{who} lost connection: Internal Exception: "

                f"DecoderException: {type(exc).__name__}: {exc}", level="WARN")

            n = self._ip_tracker.add_violation(ip)

            self._maybe_autoban(ip, n)


        except OverflowError as exc:

                                                            
            who = player.name if player else ip

            log(f"{who} lost connection: Internal Exception: "

                f"DecoderException: VarInt too big ({exc})", level="WARN")

            n = self._ip_tracker.add_violation(ip)

            self._maybe_autoban(ip, n)


        except OSError:

                                                        
            pass


        except Exception:

            traceback.print_exc()


        finally:

            if player is not None:

                playerdata.save_position(

                    self.base_dir, player.uuid, player.name,

                    player.x, player.y, player.z, player.yaw, player.pitch,

                )

                self.players.leave(player)

                self.players.announce_leave(player)

                self.players.broadcast_message(f"&e{player.name} left the game")

                log(f"{player.name} lost connection: Disconnected")

                if self.plugin_manager:

                    self.plugin_manager.fire_player_leave(player)

            try:

                sock.close()

            except OSError:

                pass


    def _maybe_autoban(self, ip: str, violation_count: int) -> None:


        threshold = int(self.props.get("max-violations-before-ban", "5"))

        if violation_count < threshold:

            log(f"Protocol violation from {ip} "

                f"({violation_count}/{threshold})", level="WARN")

            return

        if self.is_banned_ip(ip):

            return                     

        append_to_list(os.path.join(self.base_dir, "banned-ips.txt"), ip)

        self.banned_ips.add(ip.lower())

        log(f"Auto-banned {ip} after {violation_count} protocol violations",

            level="WARN")


    def _send_world(self, player: Player) -> None:

        send_packet(player.sock, LevelInitialize())

        for length, data, percent in self.world.iter_chunks():

            send_packet(player.sock, LevelDataChunk(length, data, percent))

        send_packet(player.sock, LevelFinalize(

            self.world.size_x, self.world.size_y, self.world.size_z

        ))


    def _ping_loop(self, player: Player) -> None:


        while player.connected and self._running:

            time.sleep(2)

            if player.connected:

                player.send(Ping())


    def _client_loop(self, player: Player) -> None:

        while player.connected:

            pkt = read_packet(player.sock)


            if isinstance(pkt, SetBlockClient):

                self._on_set_block(player, pkt)

            elif isinstance(pkt, PlayerTeleport):

                player.x, player.y, player.z = pkt.x, pkt.y, pkt.z

                player.yaw, player.pitch = pkt.yaw, pkt.pitch

                self.players.broadcast(

                    PlayerTeleport(

                        player.player_id, pkt.x, pkt.y, pkt.z, pkt.yaw, pkt.pitch

                    ),

                    exclude=player,

                )

                if self.plugin_manager:

                    self.plugin_manager.fire_player_move(

                        player, pkt.x, pkt.y, pkt.z, pkt.yaw, pkt.pitch

                    )

            elif isinstance(pkt, Message):

                self._on_message(player, pkt.message)


    def _on_set_block(self, player: Player, pkt: SetBlockClient) -> None:

        if pkt.mode == BlockChangeMode.PLACE:

            if not can_place(pkt.block_type, cpe=player.cpe_blocks) and not player.op:

                real = self.world.get_block(pkt.x, pkt.y, pkt.z)

                player.send(SetBlockServer(pkt.x, pkt.y, pkt.z, real))

                return

            if self.plugin_manager:

                if not self.plugin_manager.fire_block_place(

                    player, pkt.x, pkt.y, pkt.z, pkt.block_type

                ):

                    real = self.world.get_block(pkt.x, pkt.y, pkt.z)

                    player.send(SetBlockServer(pkt.x, pkt.y, pkt.z, real))

                    return

            self.world.set_block(pkt.x, pkt.y, pkt.z, pkt.block_type)

                                                                                 
            if pkt.block_type in (8, 9):

                self.world.set_block(pkt.x, pkt.y, pkt.z, 8)

            elif pkt.block_type in (10, 11):

                self.world.set_block(pkt.x, pkt.y, pkt.z, 10)

        else:

            current = self.world.get_block(pkt.x, pkt.y, pkt.z)

            if not can_break(current) and not player.op:

                player.send(SetBlockServer(pkt.x, pkt.y, pkt.z, current))

                return

            if self.plugin_manager:

                if not self.plugin_manager.fire_block_break(

                    player, pkt.x, pkt.y, pkt.z, current

                ):

                    player.send(SetBlockServer(pkt.x, pkt.y, pkt.z, current))

                    return

            self.world.set_block(pkt.x, pkt.y, pkt.z, 0)


        new_block = self.world.get_block(pkt.x, pkt.y, pkt.z)

        self.players.broadcast(SetBlockServer(pkt.x, pkt.y, pkt.z, new_block))


        if new_block == 0:

                                                                              
            for wx, wy, wz, wblk in fluids.wake_neighbors(self.world, pkt.x, pkt.y, pkt.z):

                self.players.broadcast(SetBlockServer(wx, wy, wz, wblk))

            gravity.notify(pkt.x, pkt.y + 1, pkt.z)

            above = self.world.get_block(pkt.x, pkt.y + 1, pkt.z)
            if needs_support(above):
                self.world.set_block(pkt.x, pkt.y + 1, pkt.z, 0)
                self.players.broadcast(SetBlockServer(pkt.x, pkt.y + 1, pkt.z, 0))

        elif new_block in (8, 10):                                        

            fluids.activate(pkt.x, pkt.y, pkt.z)

        elif new_block in (12, 13):                                  

            gravity.notify(pkt.x, pkt.y, pkt.z)


    def _on_message(self, player: Player, text: str) -> None:

        if self.plugin_manager and not self.plugin_manager.fire_message(player, text):

            return


        if text.startswith("/"):

            self._on_command(player, text[1:])

            return


        prefix = "&7[&cOP&7] " if player.op else ""

        line = f"{prefix}{player.name}&f: {text}"

        log(f"<{player.name}> {text}")

        self.players.broadcast_message(line)



    def _on_command(self, player: Player, raw: str) -> None:
        handle_command(self, player, raw)


if __name__ == "__main__":

    Server().run()

