"""
protodef

Librería propia (no oficial, no depende de la `protodef` de npm/PyPI)
para definir, leer y escribir protocolos binarios a partir de un
protocol.json estilo node-minecraft-protocol / node-protodef.

Uso básico:

    import json
    from protodef import Protocol

    with open("protocol.json") as f:
        proto = Protocol(json.load(f))

    pkt = proto.parse_packet("play", "toServer", raw_bytes)
    print(pkt.name, pkt.params)

    data = proto.serialize_packet("play", "toClient", "keep_alive", {"keepAliveId": 1})
"""

from .core import Protocol, ParsedPacket, Scope
from .io import Reader, Writer, BufferUnderrun
from .primitives import PRIMITIVES, Primitive, make_fixed_utf16be_string
from .errors import (
    ProtodefError,
    UnknownTypeError,
    InvalidTypeDefinition,
    SwitchCaseNotFound,
    ConditionError,
)
from .conditions import eval_condition
from .framer import PacketFramer

__all__ = [
    "Protocol",
    "ParsedPacket",
    "Scope",
    "Reader",
    "Writer",
    "BufferUnderrun",
    "PRIMITIVES",
    "Primitive",
    "make_fixed_utf16be_string",
    "ProtodefError",
    "UnknownTypeError",
    "InvalidTypeDefinition",
    "SwitchCaseNotFound",
    "ConditionError",
    "eval_condition",
    "PacketFramer",
]

__version__ = "0.1.0"
