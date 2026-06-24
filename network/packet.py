import dataclasses
import json
import os
import socket
import struct
import sys

_NET_DIR  = os.path.dirname(os.path.abspath(__file__))
_SOFT_DIR = os.path.dirname(_NET_DIR)

sys.path.insert(0, os.path.join(_SOFT_DIR, 'librerias'))

from protodef import Protocol, PRIMITIVES, Primitive
from protodef.io import Reader, Writer


# ── Tipos custom del protocolo Classic ────────────────────────────────────────

def _str64_read(r: Reader) -> str:
    return r.read_bytes(64).decode('cp437', errors='replace').rstrip(' ')

def _str64_write(value: str, w: Writer) -> None:
    enc = str(value).encode('cp437', errors='replace')[:64]
    w.write_bytes(enc.ljust(64, b' '))

PRIMITIVES['string64'] = Primitive('string64', _str64_read, _str64_write, lambda _: 64)


def _fpos_read(r: Reader) -> float:
    return struct.unpack('>h', r.read_bytes(2))[0] / 32.0

def _fpos_write(value: float, w: Writer) -> None:
    w.write_bytes(struct.pack('>h', int(float(value) * 32)))

PRIMITIVES['fpos'] = Primitive('fpos', _fpos_read, _fpos_write, lambda _: 2)


def _array1024_read(r: Reader) -> bytes:
    return r.read_bytes(1024)

def _array1024_write(value: bytes, w: Writer) -> None:
    data = bytes(value)
    w.write_bytes(data[:1024].ljust(1024, b'\x00'))

PRIMITIVES['array1024'] = Primitive('array1024', _array1024_read, _array1024_write, lambda _: 1024)


# ── Cargar protocol.json ───────────────────────────────────────────────────────

with open(os.path.join(_SOFT_DIR, 'protocolo', 'protocol.json')) as _f:
    PROTO = Protocol(json.load(_f))


# ── Tamaño de paquetes cliente→servidor (sin length-prefix en Classic) ────────

_C2S_SIZES = {
    0x00: 131,
    0x05: 9,
    0x08: 10,
    0x0D: 66,
    0x10: 67,
    0x11: 69,
    0x13: 2,
}


# ── Base Packet ───────────────────────────────────────────────────────────────

class Packet:
    _proto_name: str = ''
    packet_id:   int = 0

    def _to_params(self) -> dict:
        return dataclasses.asdict(self)

    @classmethod
    def _from_params(cls, params: dict):
        fields = {f.name for f in dataclasses.fields(cls)}
        return cls(**{k: v for k, v in params.items() if k in fields})


# ── Paquetes ──────────────────────────────────────────────────────────────────

@dataclasses.dataclass
class Identification(Packet):
    _proto_name  = 'identification'
    packet_id    = 0x00
    protocol_version: int = 7
    username:         str = ''
    verification_key: str = ''
    user_type:        int = 0

Handshake = Identification


@dataclasses.dataclass
class Ping(Packet):
    _proto_name = 'ping'
    packet_id   = 0x01


@dataclasses.dataclass
class LevelInitialize(Packet):
    _proto_name = 'level_initialize'
    packet_id   = 0x02


@dataclasses.dataclass
class LevelDataChunk(Packet):
    _proto_name      = 'level_data_chunk'
    packet_id        = 0x03
    chunk_length:    int   = 0
    chunk_data:      bytes = b''
    percent_complete:int   = 0

    def _to_params(self):
        return {
            'chunk_length':     self.chunk_length,
            'chunk_data':       self.chunk_data,
            'percent_complete': self.percent_complete,
        }


@dataclasses.dataclass
class LevelFinalize(Packet):
    _proto_name = 'level_finalize'
    packet_id   = 0x04
    size_x: int = 0
    size_y: int = 0
    size_z: int = 0


@dataclasses.dataclass
class SetBlockClient(Packet):
    _proto_name  = 'set_block_client'
    packet_id    = 0x05
    x:          int = 0
    y:          int = 0
    z:          int = 0
    mode:       int = 0
    block_type: int = 0


@dataclasses.dataclass
class SetBlockServer(Packet):
    _proto_name  = 'set_block_server'
    packet_id    = 0x06
    x:          int = 0
    y:          int = 0
    z:          int = 0
    block_type: int = 0


@dataclasses.dataclass
class SpawnPlayer(Packet):
    _proto_name  = 'spawn_player'
    packet_id    = 0x07
    player_id: int   = 0
    name:      str   = ''
    x:         float = 0.0
    y:         float = 0.0
    z:         float = 0.0
    yaw:       int   = 0
    pitch:     int   = 0


@dataclasses.dataclass
class PlayerTeleport(Packet):
    _proto_name  = 'player_teleport'
    packet_id    = 0x08
    player_id: int   = 0
    x:         float = 0.0
    y:         float = 0.0
    z:         float = 0.0
    yaw:       int   = 0
    pitch:     int   = 0


@dataclasses.dataclass
class PositionOrientationUpdate(Packet):
    _proto_name  = 'position_orientation_update'
    packet_id    = 0x09
    player_id: int = 0
    dx:        int = 0
    dy:        int = 0
    dz:        int = 0
    yaw:       int = 0
    pitch:     int = 0


@dataclasses.dataclass
class PositionUpdate(Packet):
    _proto_name  = 'position_update'
    packet_id    = 0x0A
    player_id: int = 0
    dx:        int = 0
    dy:        int = 0
    dz:        int = 0


@dataclasses.dataclass
class OrientationUpdate(Packet):
    _proto_name  = 'orientation_update'
    packet_id    = 0x0B
    player_id: int = 0
    yaw:       int = 0
    pitch:     int = 0


@dataclasses.dataclass
class DespawnPlayer(Packet):
    _proto_name  = 'despawn_player'
    packet_id    = 0x0C
    player_id: int = 0


@dataclasses.dataclass
class Message(Packet):
    _proto_name  = 'message'
    packet_id    = 0x0D
    player_id: int = 0
    message:   str = ''


@dataclasses.dataclass
class DisconnectPlayer(Packet):
    _proto_name  = 'disconnect_player'
    packet_id    = 0x0E
    reason: str = ''


@dataclasses.dataclass
class UpdateUserType(Packet):
    _proto_name  = 'update_user_type'
    packet_id    = 0x0F
    user_type: int = 0


@dataclasses.dataclass
class ExtInfo(Packet):
    _proto_name      = 'ext_info'
    packet_id        = 0x10
    app_name:        str = ''
    extension_count: int = 0


@dataclasses.dataclass
class ExtEntry(Packet):
    _proto_name  = 'ext_entry'
    packet_id    = 0x11
    ext_name: str = ''
    version:  int = 1


@dataclasses.dataclass
class CustomBlockSupportLevel(Packet):
    _proto_name  = 'custom_block_support_level'
    packet_id    = 0x13
    level: int = 1


# ── Registro de paquetes por nombre ───────────────────────────────────────────

_NAME_TO_CLASS: dict[str, type] = {
    cls._proto_name: cls
    for cls in [
        Identification, Ping, LevelInitialize, LevelDataChunk, LevelFinalize,
        SetBlockClient, SetBlockServer, SpawnPlayer, PlayerTeleport,
        PositionOrientationUpdate, PositionUpdate, OrientationUpdate,
        DespawnPlayer, Message, DisconnectPlayer, UpdateUserType,
        ExtInfo, ExtEntry, CustomBlockSupportLevel,
    ]
    if cls._proto_name
}


# ── I/O ───────────────────────────────────────────────────────────────────────

def _recv_exact(sock: socket.socket, n: int) -> bytes:
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError('Connection closed')
        buf.extend(chunk)
    return bytes(buf)


def read_packet(sock: socket.socket) -> Packet:
    id_byte    = _recv_exact(sock, 1)
    packet_id  = id_byte[0]
    size       = _C2S_SIZES.get(packet_id, 1)
    body       = _recv_exact(sock, size - 1) if size > 1 else b''
    result     = PROTO.parse_packet('classic', 'toServer', id_byte + body)
    cls        = _NAME_TO_CLASS.get(result.name)
    if cls is None:
        raise ValueError(f'Packet desconocido: {result.name} (0x{packet_id:02X})')
    return cls._from_params(result.params)


def send_packet(sock: socket.socket, pkt: Packet) -> None:
    data = PROTO.serialize_packet('classic', 'toClient', pkt._proto_name, pkt._to_params())
    sock.sendall(data)
