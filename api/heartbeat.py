import time
import urllib.parse
import urllib.request

from protocolo import ProtocolConfig


def heartbeat_loop(server) -> None:
    API_URL = "https://www.classicube.net/server/heartbeat/"
    logged_url = False

    while server._running:
        try:
            params = {
                "name":     server.props["server-name"],
                "port":     server.props["port"],
                "users":    str(len(server.players.get_all())),
                "max":      server.props["max-players"],
                "salt":     server.salt,
                "public":   server.props.get("public", "false"),
                "version":  str(ProtocolConfig.VERSION),
                "software": server.SOFTWARE_NAME,
                "web":      "false",
            }
            url = API_URL + "?" + urllib.parse.urlencode(params)
            req = urllib.request.Request(url, headers={"User-Agent": server.SOFTWARE_NAME})
            with urllib.request.urlopen(req, timeout=10) as resp:
                listed_url = resp.read().decode("utf-8").strip()
                if not logged_url and listed_url.startswith("http"):
                    server.log(f"Server listed at: {listed_url}")
                    server._listed_url = listed_url
                    logged_url = True
        except Exception as exc:
            server.log(f"Heartbeat failed: {exc}", level="WARN")

        time.sleep(45)
