import time
from ids import BlockID

TICK_INTERVAL = 0.05

_NEIGHBORS = [
    (0, -1, 0),
    (1, 0, 0), (-1, 0, 0),
    (0, 0, 1), (0, 0, -1),
]

_FLOWING_TO_STILL = {
    BlockID.WATER: BlockID.STILL_WATER,
    BlockID.LAVA:  BlockID.STILL_LAVA,
}

_WATER_IDS   = (BlockID.WATER, BlockID.STILL_WATER)
_LAVA_IDS    = (BlockID.LAVA,  BlockID.STILL_LAVA)
_FLOWING     = frozenset((BlockID.WATER, BlockID.LAVA))

_DISPLACEABLE = frozenset((
    BlockID.SAPLING,
    BlockID.DANDELION, BlockID.ROSE,
    BlockID.BROWN_MUSHROOM, BlockID.RED_MUSHROOM,
    BlockID.FIRE,
))

_active:      set  = set()
_ready:       bool = False
_grass_timer: dict = {}
GRASS_DROWN_SECS   = 5.0


def _init(world) -> None:
    global _ready
    sx, sz = world.size_x, world.size_z
    sxz = sx * sz
    now = time.time()
    for i, b in enumerate(world.blocks):
        x = i % sx
        y = i // sxz
        z = (i // sx) % sz
        if b == BlockID.WATER or b == BlockID.LAVA:
            _active.add((x, y, z))
        elif b == BlockID.STILL_WATER:
            # Grass bajo agua quieta existente → registrar timer desde el inicio
            if y > 0 and world.get_block(x, y - 1, z) == BlockID.GRASS:
                _grass_timer.setdefault((x, y - 1, z), now)
    _ready = True


def activate(x: int, y: int, z: int) -> None:
    _active.add((x, y, z))


def _displace_neighbors(world, x: int, y: int, z: int, changes: list) -> None:
    """Elimina bloques desplazables adyacentes al fluido."""
    for dx, dy, dz in _NEIGHBORS:
        nx, ny, nz = x + dx, y + dy, z + dz
        if not world.in_bounds(nx, ny, nz):
            continue
        nb = world.get_block(nx, ny, nz)
        if nb == BlockID.FIRE:
            world.set_block(nx, ny, nz, BlockID.AIR)
            changes.append((nx, ny, nz, BlockID.AIR))
        elif nb in _DISPLACEABLE:
            world.set_block(nx, ny, nz, BlockID.AIR)
            changes.append((nx, ny, nz, BlockID.AIR))


def tick(world) -> list:
    global _ready, _active
    if not _ready:
        _init(world)

    changes   = []
    to_add    = set()
    to_remove = set()
    now       = time.time()

    for (x, y, z) in list(_active):
        block = world.get_block(x, y, z)
        if block not in _FLOWING:
            to_remove.add((x, y, z))
            continue

        # Registrar grass bajo agua fluyente
        if block == BlockID.WATER:
            by = y - 1
            if world.in_bounds(x, by, z) and world.get_block(x, by, z) == BlockID.GRASS:
                _grass_timer.setdefault((x, by, z), now)

        spread = False
        for dx, dy, dz in _NEIGHBORS:
            nx, ny, nz = x + dx, y + dy, z + dz
            if not world.in_bounds(nx, ny, nz):
                continue
            nb = world.get_block(nx, ny, nz)

            if block == BlockID.WATER and nb == BlockID.FIRE:
                world.set_block(nx, ny, nz, BlockID.AIR)
                changes.append((nx, ny, nz, BlockID.AIR))
                nb = BlockID.AIR

            if nb in _DISPLACEABLE:
                world.set_block(nx, ny, nz, BlockID.AIR)
                changes.append((nx, ny, nz, BlockID.AIR))
                nb = BlockID.AIR

            if nb == BlockID.AIR:
                world.set_block(nx, ny, nz, block)
                changes.append((nx, ny, nz, block))
                to_add.add((nx, ny, nz))
                spread = True
                # Registrar grass bajo la nueva posición de agua
                if block == BlockID.WATER:
                    bby = ny - 1
                    if world.in_bounds(nx, bby, nz) and world.get_block(nx, bby, nz) == BlockID.GRASS:
                        _grass_timer.setdefault((nx, bby, nz), now)
            elif block == BlockID.WATER and nb in _LAVA_IDS:
                world.set_block(nx, ny, nz, BlockID.OBSIDIAN)
                changes.append((nx, ny, nz, BlockID.OBSIDIAN))
                to_remove.add((nx, ny, nz))
            elif block == BlockID.LAVA and nb in _WATER_IDS:
                world.set_block(x, y, z, BlockID.OBSIDIAN)
                changes.append((x, y, z, BlockID.OBSIDIAN))
                to_remove.add((x, y, z))
                spread = False
                break

        if not spread and world.get_block(x, y, z) == block:
            # Antes de quedarse quieto: desplazar vecinos desplazables
            _displace_neighbors(world, x, y, z, changes)
            still = _FLOWING_TO_STILL[block]
            world.set_block(x, y, z, still)
            changes.append((x, y, z, still))
            to_remove.add((x, y, z))

    _active -= to_remove
    _active |= to_add

    # Grass → Dirt: corre independiente, funciona con STILL_WATER también
    done = []
    for (gx, gy, gz), stamp in list(_grass_timer.items()):
        above = world.get_block(gx, gy + 1, gz) if world.in_bounds(gx, gy + 1, gz) else BlockID.AIR
        if above not in _WATER_IDS:
            done.append((gx, gy, gz))
        elif now - stamp >= GRASS_DROWN_SECS:
            world.set_block(gx, gy, gz, BlockID.DIRT)
            changes.append((gx, gy, gz, BlockID.DIRT))
            done.append((gx, gy, gz))
    for pos in done:
        _grass_timer.pop(pos, None)

    return changes


def wake_neighbors(world, x: int, y: int, z: int) -> list:
    changes = []
    for dx, dy, dz in _NEIGHBORS + [(0, 1, 0)]:
        nx, ny, nz = x + dx, y + dy, z + dz
        if not world.in_bounds(nx, ny, nz):
            continue
        nb = world.get_block(nx, ny, nz)
        if nb == BlockID.STILL_WATER:
            world.set_block(nx, ny, nz, BlockID.WATER)
            changes.append((nx, ny, nz, BlockID.WATER))
            _active.add((nx, ny, nz))
        elif nb == BlockID.STILL_LAVA:
            world.set_block(nx, ny, nz, BlockID.LAVA)
            changes.append((nx, ny, nz, BlockID.LAVA))
            _active.add((nx, ny, nz))
    return changes
