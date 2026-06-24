

import hashlib

import struct


from ids import BlockID


def index(x: int, y: int, z: int, size_x: int, size_z: int) -> int:


    return x + z * size_x + y * size_x * size_z


def generate_flat(size_x: int, size_y: int, size_z: int,

                  dirt_height: int | None = None) -> bytearray:


    blocks = bytearray(size_x * size_y * size_z)


    ground_height = dirt_height if dirt_height is not None else max(1, size_y // 2)

    grass_y = ground_height - 1

    dirt_start_y = max(0, ground_height - 4)


    for y in range(ground_height):

        if y == 0:

            block = BlockID.BEDROCK

        elif y == grass_y:

            block = BlockID.GRASS

        elif y >= dirt_start_y:

            block = BlockID.DIRT

        else:

            block = BlockID.STONE


        for z in range(size_z):

            for x in range(size_x):

                blocks[index(x, y, z, size_x, size_z)] = block


    return blocks


def _lattice_noise(ix: int, iz: int, seed: int) -> float:


    h = hashlib.md5(struct.pack(">iii", seed, ix, iz)).digest()

    return int.from_bytes(h[:2], "big") / 65535.0


def _smoothstep(t: float) -> float:

    return t * t * (3.0 - 2.0 * t)


def _value_noise(x: float, z: float, seed: int) -> float:


    ix0, iz0 = int(x), int(z)

    ix1, iz1 = ix0 + 1, iz0 + 1

    fx = _smoothstep(x - ix0)

    fz = _smoothstep(z - iz0)


    n00 = _lattice_noise(ix0, iz0, seed)

    n10 = _lattice_noise(ix1, iz0, seed)

    n01 = _lattice_noise(ix0, iz1, seed)

    n11 = _lattice_noise(ix1, iz1, seed)


    nx0 = n00 + fx * (n10 - n00)

    nx1 = n01 + fx * (n11 - n01)

    return nx0 + fz * (nx1 - nx0)


def _octave_noise(x: float, z: float,

                  octaves: tuple = ((32, 0.5, 1), (16, 0.3, 2), (8, 0.2, 3))) -> float:


    total = sum(w * _value_noise(x / s, z / s, seed) for s, w, seed in octaves)

    return total / sum(w for _, w, _ in octaves)


def _carve_caves(blocks: bytearray, size_x: int, size_y: int, size_z: int,

                 rng) -> None:


    import math


    num_worms = max(2, (size_x * size_z) // 200)


    DIGGABLE = {BlockID.STONE, BlockID.DIRT, BlockID.GRASS}


    for _ in range(num_worms):

        wx = rng.uniform(0, size_x)

        wy = rng.uniform(4, max(5, size_y * 0.45))                           

        wz = rng.uniform(0, size_z)


        import math as _math

        angle_h = rng.uniform(0, 2 * _math.pi)

        angle_v = rng.uniform(-0.3, 0.3)

        radius   = rng.uniform(1.8, 3.2)

        steps    = int(rng.uniform(60, 150))


        for _ in range(steps):

                               
            wx += _math.cos(angle_h) * _math.cos(angle_v)

            wy += _math.sin(angle_v)

            wz += _math.sin(angle_h) * _math.cos(angle_v)


            angle_h += rng.uniform(-0.25, 0.25)

            angle_v  = max(-0.65, min(0.65, angle_v + rng.uniform(-0.12, 0.12)))

            radius   = max(1.5, min(3.8, radius + rng.uniform(-0.08, 0.08)))


            r = int(radius) + 1

            r2 = radius * radius

            bwx, bwy, bwz = int(wx), int(wy), int(wz)

            for dy in range(-r, r + 1):

                by = bwy + dy

                if by <= 0 or by >= size_y - 1:

                    continue

                for dz in range(-r, r + 1):

                    bz = bwz + dz

                    if not (0 <= bz < size_z):

                        continue

                    for dx in range(-r, r + 1):

                        bx = bwx + dx

                        if not (0 <= bx < size_x):

                            continue

                        if dx * dx + dy * dy + dz * dz <= r2:

                            idx = index(bx, by, bz, size_x, size_z)

                            if blocks[idx] in DIGGABLE:

                                blocks[idx] = BlockID.AIR


def _place_ores(blocks: bytearray, size_x: int, size_y: int, size_z: int,

                heights: list, rng) -> None:


    ORE_SPECS = [

        (BlockID.COAL_ORE,  25, 2, None, 8),                               

        (BlockID.IRON_ORE,  15, 2, 45,   7),

        (BlockID.GOLD_ORE,   6, 2, 30,   6),

        (BlockID.GRAVEL,    10, 2, None, 6),

    ]


    scale = (size_x * size_z) / 256.0


    for block_id, base_count, min_y, max_y_cap, max_vein in ORE_SPECS:

        count = max(1, int(base_count * scale))

        for _ in range(count):

            vx = rng.randint(0, size_x - 1)

            vz = rng.randint(0, size_z - 1)


            surf = heights[vx][vz] - 2                                          

            cap  = min(surf, max_y_cap) if max_y_cap is not None else surf

            if cap < min_y:

                continue


            vy = rng.randint(min_y, cap)

            vein_size = rng.randint(3, max_vein)


            cx, cy, cz = float(vx), float(vy), float(vz)

            for _ in range(vein_size):

                bx, by, bz = int(cx), int(cy), int(cz)

                if 0 <= bx < size_x and 1 <= by < size_y - 1 and 0 <= bz < size_z:

                    idx = index(bx, by, bz, size_x, size_z)

                    if blocks[idx] == BlockID.STONE:

                        blocks[idx] = block_id

                cx += rng.uniform(-1.0, 1.0)

                cy += rng.uniform(-0.5, 0.5)

                cz += rng.uniform(-1.0, 1.0)


def _place_trees(blocks: bytearray, heights: list, sea_level: int,

                 size_x: int, size_y: int, size_z: int) -> None:


    for x in range(2, size_x - 2):

        for z in range(2, size_z - 2):

            h = heights[x][z]

            if h < sea_level:                                       

                continue

            if blocks[index(x, h, z, size_x, size_z)] != BlockID.GRASS:

                continue


            if _lattice_noise(x, z, 77) <= 0.93:

                continue


            trunk_h = 4 + int(_lattice_noise(x, z, 78) * 2)         

            base_y  = h + 1


            if base_y + trunk_h + 2 >= size_y:                

                continue


            for i in range(trunk_h):

                blocks[index(x, base_y + i, z, size_x, size_z)] = BlockID.LOG


            top = base_y + trunk_h

                                    
            leaf_layers = [(-1, 2), (0, 2), (1, 1), (2, 0)]

            for dy, lr in leaf_layers:

                ly = top + dy

                if ly < 1 or ly >= size_y:

                    continue

                for lz in range(-lr, lr + 1):

                    for lx in range(-lr, lr + 1):

                        if lr > 0 and lx * lx + lz * lz > lr * lr + 1:

                            continue

                        bx, bz_ = x + lx, z + lz

                        if not (0 <= bx < size_x and 0 <= bz_ < size_z):

                            continue

                        idx = index(bx, ly, bz_, size_x, size_z)

                        if blocks[idx] == BlockID.AIR:

                            blocks[idx] = BlockID.LEAVES


            top2 = top + 2

            if top2 < size_y:

                idx = index(x, top2, z, size_x, size_z)

                if blocks[idx] == BlockID.AIR:

                    blocks[idx] = BlockID.LEAVES


def generate_normal(size_x: int, size_y: int, size_z: int) -> bytearray:


    import random


    rng = random.Random(42)                                                 


    blocks    = bytearray(size_x * size_y * size_z)

    sea_level = max(2, size_y // 2)

    h_var     = max(4, size_y // 4)


    heights: list[list[int]] = []

    for x in range(size_x):

        row: list[int] = []

        for z in range(size_z):

            n = _octave_noise(float(x), float(z))

            h = sea_level + int(n * h_var - h_var * 0.4)

            row.append(max(2, min(size_y - 6, h)))

        heights.append(row)


    for x in range(size_x):

        for z in range(size_z):

            h        = heights[x][z]

            submerged = h < sea_level


            for y in range(h + 1):

                if y == 0:

                    blk = BlockID.BEDROCK

                elif y == h:

                    blk = BlockID.SAND if submerged else BlockID.GRASS

                elif y >= h - 3:

                    blk = BlockID.SAND if submerged else BlockID.DIRT

                else:

                    blk = BlockID.STONE

                blocks[index(x, y, z, size_x, size_z)] = blk


            if submerged:

                for y in range(h + 1, sea_level):

                    blocks[index(x, y, z, size_x, size_z)] = BlockID.STILL_WATER


    _carve_caves(blocks, size_x, size_y, size_z, rng)


    _place_trees(blocks, heights, sea_level, size_x, size_y, size_z)


    _place_ores(blocks, size_x, size_y, size_z, heights, rng)


    return blocks


GENERATORS = {

    "flat":   generate_flat,

    "normal": generate_normal,

}


def generate(name: str, size_x: int, size_y: int, size_z: int) -> bytearray:


    gen_fn = GENERATORS.get(name, generate_flat)

    return gen_fn(size_x, size_y, size_z)

