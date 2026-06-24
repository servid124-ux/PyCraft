

import hashlib

import socket

import threading

import uuid as uuid_lib


from packet import (

    SpawnPlayer,

    DespawnPlayer,

    PlayerTeleport,

    Message,

    DisconnectPlayer,

    send_packet,

)


SELF_ID = -1

MAX_PLAYERS = 128              


def offline_uuid(name: str) -> uuid_lib.UUID:


    digest = bytearray(hashlib.md5(f"OfflinePlayer:{name}".encode("utf-8")).digest())

    digest[6] = (digest[6] & 0x0F) | 0x30              

    digest[8] = (digest[8] & 0x3F) | 0x80                      

    return uuid_lib.UUID(bytes=bytes(digest))


class Player:

    def __init__(self, sock: socket.socket, player_id: int, name: str):

        self.sock = sock

        self.player_id = player_id

        self.name = name

        self.uuid = offline_uuid(name)


        self.x = 0.0

        self.y = 0.0

        self.z = 0.0

        self.yaw = 0

        self.pitch = 0


        self.op = False
        self.cpe_blocks: bool = False

        self.connected = True

        self.lock = threading.Lock()                                         


    def set_spawn(self, x: float, y: float, z: float, yaw: int = 0, pitch: int = 0) -> None:

        self.x, self.y, self.z = x, y, z

        self.yaw, self.pitch = yaw, pitch


    def send(self, packet) -> None:


        if not self.connected:

            return

        try:

            with self.lock:

                send_packet(self.sock, packet)

        except (ConnectionError, OSError):

            self.connected = False


    def send_self_spawn(self) -> None:


        self.send(SpawnPlayer(SELF_ID, self.name, self.x, self.y, self.z, self.yaw, self.pitch))


    def send_teleport(self, x: float, y: float, z: float, yaw: int = 0, pitch: int = 0) -> None:

        self.set_spawn(x, y, z, yaw, pitch)

        self.send(PlayerTeleport(SELF_ID, x, y, z, yaw, pitch))


    def send_message(self, text: str) -> None:

        self.send(Message(0, text))


    def kick(self, reason: str = "Kickeado") -> None:

        self.send(DisconnectPlayer(reason))

        self.connected = False

        try:

            self.sock.close()

        except OSError:

            pass


class PlayerManager:


    def __init__(self):

        self._lock = threading.Lock()

        self._players: dict[int, Player] = {}


    def _next_free_id(self) -> int | None:

        used = set(self._players.keys())

        for candidate in range(MAX_PLAYERS):

            if candidate not in used:

                return candidate

        return None                  


    def join(self, sock: socket.socket, name: str, max_players: int = MAX_PLAYERS) -> Player | None:


        with self._lock:

            if len(self._players) >= max_players:

                return None

            pid = self._next_free_id()

            if pid is None:

                return None

            player = Player(sock, pid, name)

            self._players[pid] = player

            return player


    def leave(self, player: Player) -> None:

        with self._lock:

            self._players.pop(player.player_id, None)


    def get_all(self) -> list[Player]:

        with self._lock:

            return list(self._players.values())


    def get_others(self, player: Player) -> list[Player]:

        with self._lock:

            return [p for p in self._players.values() if p.player_id != player.player_id]


    def find_by_name(self, name: str) -> Player | None:

        with self._lock:

            for p in self._players.values():

                if p.name.lower() == name.lower():

                    return p

        return None


    def get_by_id(self, player_id: int) -> Player | None:


        with self._lock:

            return self._players.get(player_id)


    def broadcast(self, packet, exclude: Player | None = None) -> None:

        for p in self.get_all():

            if exclude is not None and p.player_id == exclude.player_id:

                continue

            p.send(packet)


    def broadcast_message(self, text: str, exclude: Player | None = None) -> None:

        self.broadcast(Message(0, text), exclude=exclude)


    def introduce(self, new_player: Player) -> None:


        others = self.get_others(new_player)


        for other in others:

            new_player.send(SpawnPlayer(

                other.player_id, other.name, other.x, other.y, other.z, other.yaw, other.pitch

            ))


        spawn_for_others = SpawnPlayer(

            new_player.player_id, new_player.name,

            new_player.x, new_player.y, new_player.z,

            new_player.yaw, new_player.pitch,

        )

        for other in others:

            other.send(spawn_for_others)


    def announce_leave(self, player: Player) -> None:


        self.broadcast(DespawnPlayer(player.player_id), exclude=player)

