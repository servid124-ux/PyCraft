"""
protodef/primitives.py

Tipos primitivos: no dependen de protocol.json, son los bloques de bytes
más básicos (enteros de tamaño fijo, varints, floats, bool, strings).

Cada primitivo expone:
    read(reader: Reader) -> Any
    write(value: Any, writer: Writer) -> None
    size_of(value: Any) -> int

Se registran en un dict PRIMITIVES { nombre: Primitive } que después
el motor principal (core.py) usa como tipos base resolvibles por nombre.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Any, Callable

from .io import Reader, Writer


@dataclass(frozen=True)
class Primitive:
    name: str
    read: Callable[[Reader], Any]
    write: Callable[[Any, Writer], None]
    size_of: Callable[[Any], int] | None = None


def _fixed_size_primitive(name: str, fmt: str, little_endian: bool = False) -> Primitive:
    size = struct.calcsize(fmt)
    full_fmt = ("<" if little_endian else ">") + fmt

    def read(r: Reader) -> Any:
        data = r.read_bytes(size)
        return struct.unpack(full_fmt, data)[0]

    def write(value: Any, w: Writer) -> None:
        w.write_bytes(struct.pack(full_fmt, value))

    return Primitive(name=name, read=read, write=write, size_of=lambda v: size)


# ---------------------------------------------------------------------------
# Enteros de tamaño fijo big-endian (estándar en protocolos Minecraft)
# ---------------------------------------------------------------------------

i8 = _fixed_size_primitive("i8", "b")
u8 = _fixed_size_primitive("u8", "B")
i16 = _fixed_size_primitive("i16", "h")
u16 = _fixed_size_primitive("u16", "H")
i32 = _fixed_size_primitive("i32", "i")
u32 = _fixed_size_primitive("u32", "I")
i64 = _fixed_size_primitive("i64", "q")
u64 = _fixed_size_primitive("u64", "Q")
f32 = _fixed_size_primitive("f32", "f")
f64 = _fixed_size_primitive("f64", "d")

# little-endian (RakNet y algunos campos de protocolos viejos los usan)
li16 = _fixed_size_primitive("li16", "h", little_endian=True)
lu16 = _fixed_size_primitive("lu16", "H", little_endian=True)
li32 = _fixed_size_primitive("li32", "i", little_endian=True)
lu32 = _fixed_size_primitive("lu32", "I", little_endian=True)
li64 = _fixed_size_primitive("li64", "q", little_endian=True)
lu64 = _fixed_size_primitive("lu64", "Q", little_endian=True)
lf32 = _fixed_size_primitive("lf32", "f", little_endian=True)
lf64 = _fixed_size_primitive("lf64", "d", little_endian=True)


def _bool_read(r: Reader) -> bool:
    return r.read_bytes(1)[0] != 0


def _bool_write(value: bool, w: Writer) -> None:
    w.write_bytes(b"\x01" if value else b"\x00")


bool_ = Primitive("bool", _bool_read, _bool_write, lambda v: 1)


def _void_read(r: Reader) -> None:
    return None


def _void_write(value: Any, w: Writer) -> None:
    pass


void = Primitive("void", _void_read, _void_write, lambda v: 0)


# ---------------------------------------------------------------------------
# Varint / Varlong (LEB128, estilo Protocol Buffers / Minecraft)
# ---------------------------------------------------------------------------

def _varint_read_raw(r: Reader, max_bits: int) -> int:
    """Lee el valor crudo unsigned de hasta max_bits bits."""
    result = 0
    shift = 0
    while True:
        byte = r.read_bytes(1)[0]
        result |= (byte & 0x7F) << shift
        shift += 7
        if not (byte & 0x80):
            break
        if shift > max_bits + 7:
            raise ValueError(f"varint excede {max_bits} bits")
    return result & ((1 << max_bits) - 1)


def _to_signed(value: int, bits: int) -> int:
    sign_bit = 1 << (bits - 1)
    return value - (1 << bits) if value & sign_bit else value


def _varint_read(r: Reader, max_bits: int = 32) -> int:
    raw = _varint_read_raw(r, max_bits)
    return _to_signed(raw, max_bits)


def _varint_write(value: int, w: Writer, max_bits: int = 32) -> None:
    v = value & ((1 << max_bits) - 1)
    out = bytearray()
    while True:
        byte = v & 0x7F
        v >>= 7
        if v != 0:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            break
    w.write_bytes(bytes(out))


def _varint_size_of(value: int, max_bits: int = 32) -> int:
    v = value & ((1 << max_bits) - 1)
    size = 1
    v >>= 7
    while v != 0:
        size += 1
        v >>= 7
    return size


varint = Primitive(
    "varint",
    lambda r: _varint_read(r, 32),
    lambda v, w: _varint_write(v, w, 32),
    lambda v: _varint_size_of(v, 32),
)

varlong = Primitive(
    "varlong",
    lambda r: _varint_read(r, 64),
    lambda v, w: _varint_write(v, w, 64),
    lambda v: _varint_size_of(v, 64),
)

# variantes "unsigned" explícitas: nunca interpretan el bit de signo
# (útiles para protocolos que documentan varints siempre positivos, p.ej counts grandes)
uvarint = Primitive(
    "uvarint",
    lambda r: _varint_read_raw(r, 32),
    lambda v, w: _varint_write(v, w, 32),
    lambda v: _varint_size_of(v, 32),
)
uvarlong = Primitive(
    "uvarlong",
    lambda r: _varint_read_raw(r, 64),
    lambda v, w: _varint_write(v, w, 64),
    lambda v: _varint_size_of(v, 64),
)


# zigzag varint (protobuf-style: 0,-1,1,-2,2 -> 0,1,2,3,4 antes de LEB128)
def _zigzag_encode(value: int, bits: int) -> int:
    return ((value << 1) ^ (value >> (bits - 1))) & ((1 << bits) - 1)


def _zigzag_decode(value: int) -> int:
    return (value >> 1) ^ -(value & 1)


zigzag32 = Primitive(
    "zigzag32",
    lambda r: _zigzag_decode(_varint_read_raw(r, 32)),
    lambda v, w: _varint_write(_zigzag_encode(v, 32), w, 32),
    lambda v: _varint_size_of(_zigzag_encode(v, 32), 32),
)
zigzag64 = Primitive(
    "zigzag64",
    lambda r: _zigzag_decode(_varint_read_raw(r, 64)),
    lambda v, w: _varint_write(_zigzag_encode(v, 64), w, 64),
    lambda v: _varint_size_of(_zigzag_encode(v, 64), 64),
)


# ---------------------------------------------------------------------------
# Strings de longitud terminada en null byte (C-style)
# ---------------------------------------------------------------------------

def _cstring_read(r: Reader) -> str:
    out = bytearray()
    while True:
        b = r.read_bytes(1)
        if b == b"\x00":
            break
        out += b
    return out.decode("utf-8")


def _cstring_write(value: str, w: Writer) -> None:
    w.write_bytes(value.encode("utf-8") + b"\x00")


cstring = Primitive(
    "cstring",
    _cstring_read,
    _cstring_write,
    lambda v: len(v.encode("utf-8")) + 1,
)


def make_fixed_utf16be_string(length: int) -> Primitive:
    """
    Minecraft Classic: strings de longitud fija en caracteres, codificados
    UTF-16BE y rellenados con espacios (' ') hasta completar `length`.
    """

    def read(r: Reader) -> str:
        data = r.read_bytes(length * 2)
        return data.decode("utf-16-be").rstrip(" ")

    def write(value: str, w: Writer) -> None:
        padded = value[:length].ljust(length)
        w.write_bytes(padded.encode("utf-16-be"))

    return Primitive(f"fixed_utf16be_{length}", read, write, lambda v: length * 2)


PRIMITIVES: dict[str, Primitive] = {
    p.name: p
    for p in [
        i8, u8, i16, u16, i32, u32, i64, u64, f32, f64,
        li16, lu16, li32, lu32, li64, lu64, lf32, lf64,
        bool_, void,
        varint, varlong, uvarint, uvarlong, zigzag32, zigzag64,
        cstring,
    ]
}
PRIMITIVES["bool"] = bool_
