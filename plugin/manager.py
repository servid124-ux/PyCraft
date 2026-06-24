

import importlib.util

import inspect

import os

import sys

import threading

import time

import traceback


from plugin_base import Plugin

from config    import PluginConfig


def _ts() -> str:

    return time.strftime("%H:%M:%S")


def _log(msg: str, level: str = "INFO") -> None:

    print(f"[{_ts()}] [PluginManager/{level}]: {msg}", flush=True)


class ScheduledTask:

    def __init__(self, func, args, kwargs, interval: float,

                 repeating: bool, plugin):

        self.func      = func

        self.args      = args

        self.kwargs    = kwargs

        self.interval  = interval

        self.repeating = repeating

        self.plugin    = plugin

        self.next_run  = time.time() + interval

        self.cancelled = False


    def cancel(self) -> None:

        self.cancelled = True


class PluginManager:


    def __init__(self, server, base_dir: str):

        self.server     = server

        self.base_dir   = base_dir

        self.plugin_dir = os.path.join(base_dir, "plugins")


        self.plugins: list[Plugin] = []


        self._commands: dict = {}


        self._tasks:     list[ScheduledTask] = []

        self._task_lock  = threading.Lock()


        self._pdata: dict = {}


        self._tick_n: int = 0


        self._config_dir = os.path.join(self.plugin_dir, "config")

        self._data_dir   = os.path.join(self.plugin_dir, "data")

        for d in (self.plugin_dir, self._config_dir, self._data_dir):

            os.makedirs(d, exist_ok=True)


        if self.plugin_dir not in sys.path:

            sys.path.insert(0, self.plugin_dir)


        threading.Thread(target=self._task_loop, daemon=True).start()

        threading.Thread(target=self._tick_loop, daemon=True).start()


    def _make_config(self, plugin_name: str) -> PluginConfig:

        return PluginConfig(plugin_name, self._config_dir)


    def _make_data_folder(self, plugin_name: str) -> str:

        path = os.path.join(self._data_dir, plugin_name.lower())

        os.makedirs(path, exist_ok=True)

        return path


    def _register_command(self, name: str, func,

                          description: str, op_only: bool, plugin) -> None:

        self._commands[name.lower()] = {

            "func":        func,

            "description": description,

            "op_only":     op_only,

            "plugin":      plugin,

        }


    def _dispatch_registered(self, player, cmd: str, args: list) -> bool:


        info = self._commands.get(cmd.lower())

        if not info:

            return False

        if info["op_only"] and not player.op:

            player.send_message("&cYou don't have permission to use this command")

            return True

        try:

            info["func"](player, args)

        except Exception:

            traceback.print_exc()

            player.send_message("&cPlugin error in that command")

        return True


    def get_commands(self) -> dict:


        return dict(self._commands)


    def _schedule(self, func, args, kwargs, interval: float,

                  repeating: bool, plugin) -> ScheduledTask:

        task = ScheduledTask(func, args, kwargs, interval, repeating, plugin)

        with self._task_lock:

            self._tasks.append(task)

        return task


    def _task_loop(self) -> None:

        while True:

            now = time.time()

            with self._task_lock:

                tasks = list(self._tasks)

            to_remove = []

            for task in tasks:

                if task.cancelled:

                    to_remove.append(task)

                    continue

                if now < task.next_run:

                    continue

                try:

                    task.func(*task.args, **task.kwargs)

                except Exception:

                    traceback.print_exc()

                if task.repeating:

                    task.next_run = now + task.interval

                else:

                    to_remove.append(task)

            if to_remove:

                with self._task_lock:

                    for t in to_remove:

                        try: self._tasks.remove(t)

                        except ValueError: pass

            time.sleep(0.05)


    def _cancel_plugin_tasks(self, plugin) -> None:

        with self._task_lock:

            for t in self._tasks:

                if t.plugin is plugin:

                    t.cancelled = True


    def _tick_loop(self) -> None:

        while True:

            time.sleep(1.0)

            self._tick_n += 1

            for p in list(self.plugins):

                try: p.on_tick(self._tick_n)

                except Exception: traceback.print_exc()


    def get_player_data(self, player, key: str, default=None):

        return self._pdata.get(str(player.uuid), {}).get(key, default)


    def set_player_data(self, player, key: str, value) -> None:

        uid = str(player.uuid)

        if uid not in self._pdata:

            self._pdata[uid] = {}

        self._pdata[uid][key] = value


    def load_all(self) -> None:

        only = self._enabled_filter()

        for filename in sorted(os.listdir(self.plugin_dir)):

            if not filename.endswith(".py") or filename.startswith("_"):

                continue

            stem = filename[:-3]

            if only is not None and stem not in only:

                continue

            self._load_file(filename, stem)


    def _load_file(self, filename: str, stem: str) -> Plugin | None:

        filepath = os.path.join(self.plugin_dir, filename)

        try:

            spec   = importlib.util.spec_from_file_location(stem, filepath)

            module = importlib.util.module_from_spec(spec)

            sys.modules[stem] = module

            spec.loader.exec_module(module)


            for _, obj in inspect.getmembers(module, inspect.isclass):

                if obj is Plugin or not issubclass(obj, Plugin):

                    continue

                if obj.__module__ != stem:

                    continue


                missing = [d for d in getattr(obj, "depends", [])

                           if not self.get_plugin(d)]

                if missing:

                    _log(f"Plugin {obj.name!r} depends on {missing} — not loaded",

                         level="WARN")

                    continue


                instance = obj(self.server, self)

                instance.on_enable()

                self.plugins.append(instance)

                _log(f"Enabled plugin: {instance.name} v{instance.version} "

                     f"by {instance.author}")

                return instance

        except Exception:

            _log(f"Failed to load {filename}:", level="ERROR")

            traceback.print_exc()

        return None


    def reload(self, name: str) -> bool:


        target = self.get_plugin(name)

        if target is None:

            return False


        try: target.on_disable()

        except Exception: traceback.print_exc()

        self.plugins.remove(target)


        self._commands = {k: v for k, v in self._commands.items()

                          if v.get("plugin") is not target}

        self._cancel_plugin_tasks(target)


        for filename in os.listdir(self.plugin_dir):

            stem = filename[:-3]

            if filename.endswith(".py") and stem.lower() == name.lower():

                return self._load_file(filename, stem) is not None

        return False


    def unload_all(self) -> None:

        for p in list(self.plugins):

            try: p.on_disable()

            except Exception: traceback.print_exc()

        self.plugins.clear()

        self._commands.clear()


    def get_plugin(self, name: str) -> Plugin | None:

        for p in self.plugins:

            if p.name.lower() == name.lower():

                return p

        return None


    def _enabled_filter(self) -> set | None:

        enabled = self.server.software_meta.get("plugins-enabled", [])

        if not enabled:

            return None

        return {n.replace(".py", "") for n in enabled}


    def fire_player_join(self, player) -> None:

        for p in list(self.plugins):

            try: p.on_player_join(player)

            except Exception: traceback.print_exc()


    def fire_player_leave(self, player) -> None:

        for p in list(self.plugins):

            try: p.on_player_leave(player)

            except Exception: traceback.print_exc()


    def fire_player_move(self, player, x, y, z, yaw, pitch) -> None:

        for p in list(self.plugins):

            try: p.on_player_move(player, x, y, z, yaw, pitch)

            except Exception: traceback.print_exc()


    def fire_message(self, player, text: str) -> bool:


        result = True

        for p in list(self.plugins):

            try:

                if p.on_chat(player, text) is False:

                    result = False

            except Exception: traceback.print_exc()

        return result


    def fire_command(self, player, cmd: str, args: list) -> bool:


        if self._dispatch_registered(player, cmd, args):

            return True

                                      
        for p in list(self.plugins):

            try:

                if p.on_command(player, cmd, args) is True:

                    return True

            except Exception: traceback.print_exc()

        return False


    def fire_block_place(self, player, x, y, z, block_id) -> bool:

        result = True

        for p in list(self.plugins):

            try:

                if p.on_block_place(player, x, y, z, block_id) is False:

                    result = False

            except Exception: traceback.print_exc()

        return result


    def fire_block_break(self, player, x, y, z, block_id) -> bool:

        result = True

        for p in list(self.plugins):

            try:

                if p.on_block_break(player, x, y, z, block_id) is False:

                    result = False

            except Exception: traceback.print_exc()

        return result

