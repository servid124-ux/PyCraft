

import json

import os

from pathlib import Path


def _path_for(base_dir: str, player_uuid) -> Path:

    return Path(base_dir) / "playerdata" / f"{player_uuid}.json"


def load_position(base_dir: str, player_uuid):


    path = _path_for(base_dir, player_uuid)

    if not path.exists():

        return None

    try:

        with open(path, "r", encoding="utf-8") as f:

            data = json.load(f)

        return (

            float(data["x"]), float(data["y"]), float(data["z"]),

            int(data["yaw"]), int(data["pitch"]),

        )

    except (json.JSONDecodeError, KeyError, ValueError, OSError):

                                                                          
        return None


def save_position(base_dir: str, player_uuid, name: str,

                   x: float, y: float, z: float, yaw: int, pitch: int) -> None:


    path = _path_for(base_dir, player_uuid)

    path.parent.mkdir(parents=True, exist_ok=True)


    data = {"name": name, "x": x, "y": y, "z": z, "yaw": yaw, "pitch": pitch}


    tmp_path = path.with_suffix(".tmp")

    with open(tmp_path, "w", encoding="utf-8") as f:

        json.dump(data, f)

    os.replace(tmp_path, path)

