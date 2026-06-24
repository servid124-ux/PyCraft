

import gzip

import struct

import time

import uuid

from pathlib import Path


from generator import generate, index

from ids import BlockID

import nbt


class World:

    def __init__(self, name: str, size_x: int, size_y: int, size_z: int,

                 generator: str = "flat"):

        self.name = name

        self.size_x = size_x

        self.size_y = size_y

        self.size_z = size_z

        self.blocks = generate(generator, size_x, size_y, size_z)


        cx, cz = size_x // 2, size_z // 2

        self.spawn_x = float(cx) + 0.5

        self.spawn_z = float(cz) + 0.5

        self.spawn_y = self.find_spawn_y(cx, cz)

        self.spawn_yaw = 0

        self.spawn_pitch = 0


        self.world_uuid = uuid.uuid4().bytes

        self.time_created = int(time.time())


    def in_bounds(self, x: int, y: int, z: int) -> bool:

        return 0 <= x < self.size_x and 0 <= y < self.size_y and 0 <= z < self.size_z


    def get_block(self, x: int, y: int, z: int) -> int:

        if not self.in_bounds(x, y, z):

            return BlockID.AIR

        return self.blocks[index(x, y, z, self.size_x, self.size_z)]


    def set_block(self, x: int, y: int, z: int, block_id: int) -> bool:


        if not self.in_bounds(x, y, z):

            return False

        self.blocks[index(x, y, z, self.size_x, self.size_z)] = block_id

        return True


    def find_spawn_y(self, x: int, z: int) -> float:


        from block import is_solid, is_liquid, is_transparent


        def _dry_surface(bx: int, bz: int):

            bx = max(0, min(self.size_x - 1, bx))

            bz = max(0, min(self.size_z - 1, bz))

            for y in range(self.size_y - 1, -1, -1):

                b = self.get_block(bx, y, bz)

                                                                               
                if is_solid(b) and not is_transparent(b):

                    if not is_liquid(self.get_block(bx, y + 1, bz)):

                        return float(y + 2)

            return None


        result = _dry_surface(int(x), int(z))

        if result is not None:

            return result


        cx, cz = int(x), int(z)

        max_r = min(self.size_x, self.size_z) // 2

        for r in range(4, max_r, 4):

            for dx in range(-r, r + 1, 4):

                for dz in range(-r, r + 1, 4):

                    result = _dry_surface(cx + dx, cz + dz)

                    if result is not None:

                        return result


        return float(self.size_y // 2 + 1)


    def compressed_level_data(self) -> bytes:


        volume = len(self.blocks)

        raw = struct.pack(">I", volume) + bytes(self.blocks)

        return gzip.compress(raw)


    def iter_chunks(self, chunk_size: int = 1024):


        data = self.compressed_level_data()

        total = len(data)

        if total == 0:

            return

        for offset in range(0, total, chunk_size):

            piece = data[offset:offset + chunk_size]

            percent = min(100, int((offset + len(piece)) * 100 / total))

            yield len(piece), piece, percent


    def save(self, path: str) -> None:

        path = str(path)

        Path(path).parent.mkdir(parents=True, exist_ok=True)


        w = nbt.NBTWriter()

        w.start_compound("ClassicWorld")

        w.byte("FormatVersion", 1)

        w.string("Name", self.name)

        w.byte_array("UUID", self.world_uuid)

        w.short("X", self.size_x)

        w.short("Y", self.size_y)

        w.short("Z", self.size_z)

        w.long("TimeCreated", self.time_created)


        w.start_compound("Spawn")

        w.short("X", int(self.spawn_x * 32))

        w.short("Y", int(self.spawn_y * 32))

        w.short("Z", int(self.spawn_z * 32))

        w.byte("H", self.spawn_yaw)

        w.byte("P", self.spawn_pitch)

        w.end_compound()


        w.byte_array("BlockArray", bytes(self.blocks))

        w.end_compound()


        nbt.save_gzip(path, w.getvalue())


    @classmethod

    def load(cls, path: str) -> "World":

        raw = nbt.load_gzip(path)

        reader = nbt.NBTReader(raw)

        _, data = reader.read_root()


        world = cls.__new__(cls)

        world.name = data["Name"]

        world.size_x = data["X"]

        world.size_y = data["Y"]

        world.size_z = data["Z"]

        world.blocks = bytearray(data["BlockArray"])

        world.world_uuid = data.get("UUID", uuid.uuid4().bytes)

        world.time_created = data.get("TimeCreated", int(time.time()))


        spawn = data.get("Spawn", {})

        world.spawn_x = spawn.get("X", 0) / 32.0

        world.spawn_y = spawn.get("Y", 0) / 32.0

        world.spawn_z = spawn.get("Z", 0) / 32.0

        world.spawn_yaw = spawn.get("H", 0)

        world.spawn_pitch = spawn.get("P", 0)


        return world


    @classmethod

    def load_or_create(cls, path: str, name: str, size_x: int, size_y: int,

                        size_z: int, generator: str = "flat") -> "World":


        if Path(path).exists():

            return cls.load(path)

        world = cls(name, size_x, size_y, size_z, generator)

        world.save(path)

        return world

