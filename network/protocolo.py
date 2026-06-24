class PacketID:
    IDENTIFICATION              = 0x00
    PING                        = 0x01
    LEVEL_INITIALIZE            = 0x02
    LEVEL_DATA_CHUNK            = 0x03
    LEVEL_FINALIZE              = 0x04
    SET_BLOCK_CLIENT            = 0x05
    SET_BLOCK_SERVER            = 0x06
    SPAWN_PLAYER                = 0x07
    PLAYER_TELEPORT             = 0x08
    POSITION_ORIENTATION_UPDATE = 0x09
    POSITION_UPDATE             = 0x0A
    ORIENTATION_UPDATE          = 0x0B
    DESPAWN_PLAYER              = 0x0C
    MESSAGE                     = 0x0D
    DISCONNECT_PLAYER           = 0x0E
    UPDATE_USER_TYPE            = 0x0F
    EXT_INFO                    = 0x10
    EXT_ENTRY                   = 0x11
    CUSTOM_BLOCK_SUPPORT_LEVEL  = 0x13

class ProtocolConfig:
    VERSION     = 0x07
    STRING_LEN  = 64
    ARRAY_LEN   = 1024
    DEFAULT_PORT = 25565

class UserType:
    NORMAL = 0x00
    OP     = 0x64
    CPE    = 0x42

class BlockChangeMode:
    DESTROY = 0x00
    PLACE   = 0x01
