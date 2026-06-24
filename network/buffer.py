

import socket

import struct


def _recv_exact(sock: socket.socket, n: int) -> bytes:


    if n == 0:

        return b""

    buf = bytearray()

    while len(buf) < n:

        chunk = sock.recv(n - len(buf))

        if not chunk:

            raise ConnectionError("Socket cerrado mientras se leía un paquete")

        buf.extend(chunk)

    return bytes(buf)


class NetWriter:


    def __init__(self):

        self._buf = bytearray()


    def write_u8(self, value: int) -> "NetWriter":

        self._buf += struct.pack(">B", value & 0xFF)

        return self


    def write_i8(self, value: int) -> "NetWriter":

        self._buf += struct.pack(">b", value)

        return self


    def write_u16(self, value: int) -> "NetWriter":

        self._buf += struct.pack(">H", value & 0xFFFF)

        return self


    def write_i16(self, value: int) -> "NetWriter":

        self._buf += struct.pack(">h", value)

        return self


    def write_u32(self, value: int) -> "NetWriter":

        self._buf += struct.pack(">I", value & 0xFFFFFFFF)

        return self


    def write_i32(self, value: int) -> "NetWriter":
        self._buf += struct.pack(">i", value)
        return self


    def write_string(self, s: str, length: int = 64) -> "NetWriter":


        raw = s.encode("cp437", errors="replace")[:length]

        self._buf += raw.ljust(length, b" ")

        return self


    def write_byte_array(self, data: bytes, length: int = 1024) -> "NetWriter":


        self._buf += data[:length].ljust(length, b"\x00")

        return self


    def write_fpos(self, value: float) -> "NetWriter":


        return self.write_i16(int(value * 32))


    def write_raw(self, data: bytes) -> "NetWriter":


        self._buf += data

        return self


    def getvalue(self) -> bytes:

        return bytes(self._buf)


class NetReader:


    def __init__(self, sock: socket.socket):

        self.sock = sock


    def read_u8(self) -> int:

        return _recv_exact(self.sock, 1)[0]


    def read_i8(self) -> int:

        return struct.unpack(">b", _recv_exact(self.sock, 1))[0]


    def read_u16(self) -> int:

        return struct.unpack(">H", _recv_exact(self.sock, 2))[0]


    def read_i16(self) -> int:

        return struct.unpack(">h", _recv_exact(self.sock, 2))[0]


    def read_u32(self) -> int:

        return struct.unpack(">I", _recv_exact(self.sock, 4))[0]


    def read_i32(self) -> int:
        return struct.unpack(">i", _recv_exact(self.sock, 4))[0]


    def read_string(self, length: int = 64) -> str:

        raw = _recv_exact(self.sock, length)

        return raw.rstrip(b" \x00").decode("cp437", errors="replace")


    def read_byte_array(self, length: int = 1024) -> bytes:

        return _recv_exact(self.sock, length)


    def read_fpos(self) -> float:


        return self.read_i16() / 32.0


    def read_raw(self, n: int) -> bytes:

        return _recv_exact(self.sock, n)

