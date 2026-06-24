

from dataclasses import dataclass


from ids import BlockID


@dataclass(frozen=True)

class BlockInfo:

    id: int

    name: str

    solid: bool = True                                   

    liquid: bool = False                        

    transparent: bool = False                                     

    placeable: bool = True                                            

    breakable: bool = True
    needs_support: bool = False


_BLOCKS = [

    BlockInfo(BlockID.AIR, "Air", solid=False, transparent=True, placeable=False),

    BlockInfo(BlockID.STONE, "Stone"),

    BlockInfo(BlockID.GRASS, "Grass"),

    BlockInfo(BlockID.DIRT, "Dirt"),

    BlockInfo(BlockID.COBBLESTONE, "Cobblestone"),

    BlockInfo(BlockID.WOOD, "Wood"),

    BlockInfo(BlockID.SAPLING, "Sapling", solid=False, transparent=True, needs_support=True),

    BlockInfo(BlockID.BEDROCK, "Bedrock", placeable=False, breakable=False),

    BlockInfo(BlockID.WATER, "Water", solid=False, liquid=True, transparent=True, placeable=True),

    BlockInfo(BlockID.STILL_WATER, "Still Water", solid=False, liquid=True, transparent=True, placeable=False),

    BlockInfo(BlockID.LAVA, "Lava", solid=False, liquid=True, transparent=True, placeable=True),

    BlockInfo(BlockID.STILL_LAVA, "Still Lava", solid=False, liquid=True, transparent=True, placeable=False),

    BlockInfo(BlockID.SAND, "Sand"),

    BlockInfo(BlockID.GRAVEL, "Gravel"),

    BlockInfo(BlockID.GOLD_ORE, "Gold Ore"),

    BlockInfo(BlockID.IRON_ORE, "Iron Ore"),

    BlockInfo(BlockID.COAL_ORE, "Coal Ore"),

    BlockInfo(BlockID.LOG, "Log"),

    BlockInfo(BlockID.LEAVES, "Leaves", transparent=True),

    BlockInfo(BlockID.SPONGE, "Sponge"),

    BlockInfo(BlockID.GLASS, "Glass", transparent=True),

    BlockInfo(BlockID.RED, "Red Cloth"),

    BlockInfo(BlockID.ORANGE, "Orange Cloth"),

    BlockInfo(BlockID.YELLOW, "Yellow Cloth"),

    BlockInfo(BlockID.LIME, "Lime Cloth"),

    BlockInfo(BlockID.GREEN, "Green Cloth"),

    BlockInfo(BlockID.TEAL, "Teal Cloth"),

    BlockInfo(BlockID.AQUA, "Aqua Cloth"),

    BlockInfo(BlockID.CYAN, "Cyan Cloth"),

    BlockInfo(BlockID.BLUE, "Blue Cloth"),

    BlockInfo(BlockID.INDIGO, "Indigo Cloth"),

    BlockInfo(BlockID.VIOLET, "Violet Cloth"),

    BlockInfo(BlockID.MAGENTA, "Magenta Cloth"),

    BlockInfo(BlockID.PINK, "Pink Cloth"),

    BlockInfo(BlockID.BLACK, "Black Cloth"),

    BlockInfo(BlockID.GRAY, "Gray Cloth"),

    BlockInfo(BlockID.WHITE, "White Cloth"),

    BlockInfo(BlockID.DANDELION, "Dandelion", solid=False, transparent=True, needs_support=True),

    BlockInfo(BlockID.ROSE, "Rose", solid=False, transparent=True, needs_support=True),

    BlockInfo(BlockID.BROWN_MUSHROOM, "Brown Mushroom", solid=False, transparent=True, needs_support=True),

    BlockInfo(BlockID.RED_MUSHROOM, "Red Mushroom", solid=False, transparent=True, needs_support=True),

    BlockInfo(BlockID.GOLD, "Gold Block"),

    BlockInfo(BlockID.IRON, "Iron Block"),

    BlockInfo(BlockID.DOUBLE_SLAB, "Double Slab"),

    BlockInfo(BlockID.SLAB, "Slab"),

    BlockInfo(BlockID.BRICK, "Brick"),

    BlockInfo(BlockID.TNT, "TNT"),

    BlockInfo(BlockID.BOOKSHELF, "Bookshelf"),

    BlockInfo(BlockID.MOSSY_COBBLESTONE, "Mossy Cobblestone"),

    BlockInfo(BlockID.OBSIDIAN, "Obsidian", breakable=False),

    BlockInfo(BlockID.COBBLESTONE_SLAB, "CobblestoneSlab", placeable=True),
    BlockInfo(BlockID.ROPE,             "Rope",            placeable=True, transparent=True),
    BlockInfo(BlockID.SANDSTONE,        "Sandstone",       placeable=True),
    BlockInfo(BlockID.SNOW,             "Snow",            placeable=True, transparent=True),
    BlockInfo(BlockID.FIRE,             "Fire",            placeable=True, transparent=True),
    BlockInfo(BlockID.LIGHT_PINK,       "LightPink",       placeable=True),
    BlockInfo(BlockID.FOREST_GREEN,     "ForestGreen",     placeable=True),
    BlockInfo(BlockID.BROWN,            "Brown",           placeable=True),
    BlockInfo(BlockID.DEEP_BLUE,        "DeepBlue",        placeable=True),
    BlockInfo(BlockID.TURQUOISE,        "Turquoise",       placeable=True),
    BlockInfo(BlockID.ICE,              "Ice",             placeable=True, transparent=True),
    BlockInfo(BlockID.CERAMIC_TILE,     "CeramicTile",     placeable=True),
    BlockInfo(BlockID.MAGMA,            "Magma",           placeable=True),
    BlockInfo(BlockID.PILLAR,           "Pillar",          placeable=True),
    BlockInfo(BlockID.CACTUS,           "Cactus",          placeable=True, transparent=True),
    BlockInfo(BlockID.SNOW_GRASS,       "SnowGrass",       placeable=True),
]


BLOCKS: dict[int, BlockInfo] = {b.id: b for b in _BLOCKS}


assert len(BLOCKS) == 66, "Tienen que estar registrados los 66 bloques (0-65)"


def get_block(block_id: int) -> BlockInfo:


    return BLOCKS.get(block_id, BLOCKS[BlockID.AIR])


def needs_support(block_id: int) -> bool:
    return get_block(block_id).needs_support


def is_transparent(block_id: int) -> bool:

    return get_block(block_id).transparent


def is_solid(block_id: int) -> bool:

    return get_block(block_id).solid


def is_liquid(block_id: int) -> bool:

    return get_block(block_id).liquid


def can_place(block_id: int, cpe: bool = False) -> bool:

    if BlockID.CPE_MIN <= block_id <= BlockID.CPE_MAX:
        return cpe


    if not BlockID.is_valid(block_id):

        return False

    return get_block(block_id).placeable


def can_break(block_id: int) -> bool:


    return get_block(block_id).breakable

