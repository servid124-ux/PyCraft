

import os


class PluginConfig:

    def __init__(self, plugin_name: str, config_dir: str):

        self._name = plugin_name

        self._path = os.path.join(config_dir, f"{plugin_name.lower()}.yml")

        self._data: dict = {}

        self._loaded = False


    def _ensure(self) -> None:

        if self._loaded:

            return

        self._loaded = True

        if not os.path.exists(self._path):

            return

        with open(self._path, "r", encoding="utf-8") as f:

            for raw in f:

                line = raw.strip()

                if not line or line.startswith("#") or ":" not in line:

                    continue

                key, _, val = line.partition(":")

                self._data[key.strip()] = self._parse(val.strip())


    @staticmethod

    def _parse(val: str):

        if val.lower() == "true":  return True

        if val.lower() == "false": return False

        try:    return int(val)

        except ValueError: pass

        try:    return float(val)

        except ValueError: pass

        return val


    def get(self, key: str, default=None):

        self._ensure()

        return self._data.get(key, default)


    def set(self, key: str, value) -> None:

        self._ensure()

        self._data[key] = value


    def save(self) -> None:

        self._ensure()

        os.makedirs(os.path.dirname(self._path), exist_ok=True)

        with open(self._path, "w", encoding="utf-8") as f:

            f.write(f"# Config — {self._name}\n")

            for k, v in self._data.items():

                if isinstance(v, bool):

                    f.write(f"{k}: {'true' if v else 'false'}\n")

                else:

                    f.write(f"{k}: {v}\n")


    def __repr__(self) -> str:

        self._ensure()

        return f"PluginConfig({self._name!r}, {self._data})"

