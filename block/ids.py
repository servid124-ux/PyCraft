

class BlockID:

    AIR = 0

    STONE = 1

    GRASS = 2

    DIRT = 3

    COBBLESTONE = 4

    WOOD = 5                    

    SAPLING = 6

    BEDROCK = 7

    WATER = 8                     

    STILL_WATER = 9

    LAVA = 10                     

    STILL_LAVA = 11

    SAND = 12

    GRAVEL = 13

    GOLD_ORE = 14

    IRON_ORE = 15

    COAL_ORE = 16

    LOG = 17

    LEAVES = 18

    SPONGE = 19

    GLASS = 20

    RED = 21

    ORANGE = 22

    YELLOW = 23

    LIME = 24

    GREEN = 25

    TEAL = 26

    AQUA = 27

    CYAN = 28

    BLUE = 29

    INDIGO = 30

    VIOLET = 31

    MAGENTA = 32

    PINK = 33

    BLACK = 34

    GRAY = 35

    WHITE = 36

    DANDELION = 37

    ROSE = 38

    BROWN_MUSHROOM = 39

    RED_MUSHROOM = 40

    GOLD = 41

    IRON = 42

    DOUBLE_SLAB = 43

    SLAB = 44

    BRICK = 45

    TNT = 46

    BOOKSHELF = 47

    MOSSY_COBBLESTONE = 48

    OBSIDIAN = 49

    COBBLESTONE_SLAB = 50
    ROPE             = 51
    SANDSTONE        = 52
    SNOW             = 53
    FIRE             = 54
    LIGHT_PINK       = 55
    FOREST_GREEN     = 56
    BROWN            = 57
    DEEP_BLUE        = 58
    TURQUOISE        = 59
    ICE              = 60
    CERAMIC_TILE     = 61
    MAGMA            = 62
    PILLAR           = 63
    CACTUS           = 64
    SNOW_GRASS       = 65

    CPE_MIN = 50
    CPE_MAX = 65

    MIN = 0

    MAX = 65


    @classmethod

    def is_valid(cls, block_id: int) -> bool:

        return cls.MIN <= block_id <= cls.MAX

