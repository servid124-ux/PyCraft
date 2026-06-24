

from ids import BlockID


TICK_INTERVAL = 0.02


_FALLING_IDS = frozenset((BlockID.SAND, BlockID.GRAVEL))


_falling: set = set()

_ready:   bool = False


def _init(world) -> None:


    global _ready

    sx, sz = world.size_x, world.size_z

    sxz = sx * sz

    for i, b in enumerate(world.blocks):

        if b in _FALLING_IDS:

            x = i % sx

            z = (i // sx) % sz

            y = i // sxz

            if y > 0 and world.get_block(x, y - 1, z) == BlockID.AIR:

                _falling.add((x, y, z))

    _ready = True


def notify(x: int, y: int, z: int) -> None:


    _falling.add((x, y, z))

    _falling.add((x, y + 1, z))


def tick(world) -> list:

    global _ready, _falling

    if not _ready:

        _init(world)


    changes   = []

    to_remove = set()

    to_add    = set()


    for (x, y, z) in sorted(_falling, key=lambda p: p[1]):

        block = world.get_block(x, y, z)

        if block not in _FALLING_IDS:

            to_remove.add((x, y, z))

            continue

        if y == 0 or world.get_block(x, y - 1, z) != BlockID.AIR:

            to_remove.add((x, y, z))

            continue


        world.set_block(x, y,     z, BlockID.AIR)

        world.set_block(x, y - 1, z, block)

        changes.append((x, y,     z, BlockID.AIR))

        changes.append((x, y - 1, z, block))

        to_remove.add((x, y, z))


        if y - 1 > 0 and world.get_block(x, y - 2, z) == BlockID.AIR:

            to_add.add((x, y - 1, z))


        if y + 1 < world.size_y and world.get_block(x, y + 1, z) in _FALLING_IDS:

            to_add.add((x, y + 1, z))


    _falling -= to_remove

    _falling |= to_add

    return changes

