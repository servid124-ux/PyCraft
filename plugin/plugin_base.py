

class Plugin:

                                                                           
    name:        str = "Plugin"

    version:     str = "1.0.0"

    author:      str = "Unknown"

    description: str = ""

    depends:     list = []                                        


    def __init__(self, server, manager):

        self.server  = server

        self._mgr    = manager


        self.config      = manager._make_config(self.name)

        self.data_folder = manager._make_data_folder(self.name)


    def on_enable(self) -> None:  pass

    def on_disable(self) -> None: pass


    def on_player_join(self, player) -> None:   pass

    def on_player_leave(self, player) -> None:  pass


    def on_player_move(self, player, x, y, z, yaw, pitch) -> bool:

        return True


    def on_chat(self, player, message: str) -> bool:


        return True


    def on_command(self, player, cmd: str, args: list) -> bool:


        return False


    def on_block_place(self, player, x: int, y: int, z: int, block_id: int) -> bool:


        return True


    def on_block_break(self, player, x: int, y: int, z: int, block_id: int) -> bool:


        return True


    def on_tick(self, tick_n: int) -> None: pass


    def register_command(self, name: str, func,

                         description: str = "", op_only: bool = False) -> None:


        self._mgr._register_command(name, func, description, op_only, plugin=self)


    def schedule(self, interval: float, func, *args, **kwargs):


        return self._mgr._schedule(func, args, kwargs, interval,

                                   repeating=True, plugin=self)


    def schedule_once(self, delay: float, func, *args, **kwargs):


        return self._mgr._schedule(func, args, kwargs, delay,

                                   repeating=False, plugin=self)


    def get_plugin(self, name: str):


        return self._mgr.get_plugin(name)


    def broadcast(self, message: str) -> None:

        self.server.players.broadcast_message(message)


    def get_player_data(self, player, key: str, default=None):

        return self._mgr.get_player_data(player, key, default)


    def set_player_data(self, player, key: str, value) -> None:

        self._mgr.set_player_data(player, key, value)


    def has_permission(self, player, node: str) -> bool:


        return player.op


    def logger(self, msg: str, level: str = "INFO") -> None:

        import time

        ts = time.strftime("%H:%M:%S")

        print(f"[{ts}] [{self.name}/{level}]: {msg}", flush=True)

