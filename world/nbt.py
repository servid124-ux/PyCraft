

import gzip

import struct

from io import BytesIO


TAG_END = 0

TAG_BYTE = 1

TAG_SHORT = 2

TAG_INT = 3

TAG_LONG = 4

TAG_STRING = 8

TAG_BYTE_ARRAY = 7

TAG_COMPOUND = 10


class NBTWriter:


    def __init__(self):

        self._buf = bytearray()


    def _write_tag_header(self, tag_type: int, name: str) -> None:

        self._buf += struct.pack(">B", tag_type)

        name_bytes = name.encode("utf-8")

        self._buf += struct.pack(">H", len(name_bytes))

        self._buf += name_bytes


    def byte(self, name: str, value: int) -> "NBTWriter":

        self._write_tag_header(TAG_BYTE, name)

        self._buf += struct.pack(">b", value)

        return self


    def short(self, name: str, value: int) -> "NBTWriter":

        self._write_tag_header(TAG_SHORT, name)

        self._buf += struct.pack(">h", value)

        return self


    def long(self, name: str, value: int) -> "NBTWriter":

        self._write_tag_header(TAG_LONG, name)

        self._buf += struct.pack(">q", value)

        return self


    def string(self, name: str, value: str) -> "NBTWriter":

        self._write_tag_header(TAG_STRING, name)

        raw = value.encode("utf-8")

        self._buf += struct.pack(">H", len(raw))

        self._buf += raw

        return self


    def byte_array(self, name: str, data: bytes) -> "NBTWriter":

        self._write_tag_header(TAG_BYTE_ARRAY, name)

        self._buf += struct.pack(">I", len(data))

        self._buf += data

        return self


    def start_compound(self, name: str) -> "NBTWriter":

        self._write_tag_header(TAG_COMPOUND, name)

        return self


    def end_compound(self) -> "NBTWriter":

        self._buf += struct.pack(">B", TAG_END)

        return self


    def getvalue(self) -> bytes:

        return bytes(self._buf)


class NBTReader:


    def __init__(self, data: bytes):

        self._io = BytesIO(data)


    def _read(self, n: int) -> bytes:

        chunk = self._io.read(n)

        if len(chunk) != n:

            raise ValueError("NBT corrupto: EOF inesperado")

        return chunk


    def _read_tag_name(self) -> str:

        length = struct.unpack(">H", self._read(2))[0]

        return self._read(length).decode("utf-8")


    def read_compound(self) -> dict:


        result = {}

        while True:

            tag_type = struct.unpack(">B", self._read(1))[0]

            if tag_type == TAG_END:

                break

            name = self._read_tag_name()

            if tag_type == TAG_BYTE:

                result[name] = struct.unpack(">b", self._read(1))[0]

            elif tag_type == TAG_SHORT:

                result[name] = struct.unpack(">h", self._read(2))[0]

            elif tag_type == TAG_INT:

                result[name] = struct.unpack(">i", self._read(4))[0]

            elif tag_type == TAG_LONG:

                result[name] = struct.unpack(">q", self._read(8))[0]

            elif tag_type == TAG_STRING:

                slen = struct.unpack(">H", self._read(2))[0]

                result[name] = self._read(slen).decode("utf-8")

            elif tag_type == TAG_BYTE_ARRAY:

                alen = struct.unpack(">I", self._read(4))[0]

                result[name] = self._read(alen)

            elif tag_type == TAG_COMPOUND:

                result[name] = self.read_compound()

            else:

                raise ValueError(f"Tipo de tag NBT no soportado: {tag_type}")

        return result


    def read_root(self) -> tuple[str, dict]:


        tag_type = struct.unpack(">B", self._read(1))[0]

        if tag_type != TAG_COMPOUND:

            raise ValueError("El root de un .cw siempre tiene que ser TAG_Compound")

        name = self._read_tag_name()

        return name, self.read_compound()


def save_gzip(path: str, raw_nbt: bytes) -> None:


    with gzip.open(path, "wb") as f:

        f.write(raw_nbt)


def load_gzip(path: str) -> bytes:


    with gzip.open(path, "rb") as f:

        return f.read()

