
import socket

import sys

import threading

import time


sys.path.insert(0, "network")

import servidor

from packet import (

    Identification, LevelInitialize, LevelDataChunk, LevelFinalize,

    SpawnPlayer, Message, PlayerTeleport, read_packet, send_packet,

)


TEST_PORT = 39565


def start_server():

    s = servidor.Server(base_dir=".")

    s.props["port"] = str(TEST_PORT)

    t = threading.Thread(target=s.run, daemon=True)

    t.start()

    time.sleep(0.3)                                    

    return s


def real_client_connect(name: str) -> socket.socket:

    sock = socket.create_connection(("127.0.0.1", TEST_PORT), timeout=5)

    send_packet(sock, Identification(7, name, "", 0))

    return sock


def read_until_finalize(sock) -> list:

    pkts = []

    while True:

        pkt = read_packet(sock)

        pkts.append(pkt)

        if isinstance(pkt, LevelFinalize):

            return pkts


def main():

    print("== arrancando server real en hilo de fondo ==")

    start_server()


    print("\n== cliente A (Alice) se conecta por TCP real ==")

    sock_a = real_client_connect("Alice")

    pkts_a = read_until_finalize(sock_a)

    ident = pkts_a[0]

    assert isinstance(ident, Identification)

    print(f"  server respondió Identification: motd='{ident.verification_key}'")

    n_chunks = sum(1 for p in pkts_a if isinstance(p, LevelDataChunk))

    finalize = pkts_a[-1]

    print(f"  recibidos {n_chunks} LevelDataChunk, LevelFinalize size={finalize.size_x}x{finalize.size_y}x{finalize.size_z}")


    self_spawn = read_packet(sock_a)

    assert isinstance(self_spawn, SpawnPlayer) and self_spawn.player_id == -1

    print(f"  self-spawn recibido en ({self_spawn.x}, {self_spawn.y}, {self_spawn.z})")


    print("\n== cliente B (Bob) se conecta por TCP real ==")

    sock_b = real_client_connect("Bob")

    read_until_finalize(sock_b)

    bob_self_spawn = read_packet(sock_b)

    assert isinstance(bob_self_spawn, SpawnPlayer) and bob_self_spawn.player_id == -1


    bob_sees = read_packet(sock_b)

    assert isinstance(bob_sees, SpawnPlayer)

    print(f"  Bob recibió SpawnPlayer de '{bob_sees.name}' (id={bob_sees.player_id}) -> Bob VE a Alice")


    alice_sees = read_packet(sock_a)

    assert isinstance(alice_sees, SpawnPlayer)

    print(f"  Alice recibió SpawnPlayer de '{alice_sees.name}' (id={alice_sees.player_id}) -> Alice VE a Bob")

    print("  *** las dos mitades del handshake de visión funcionan con sockets reales ***")


    time.sleep(0.2)

    join_msg_to_alice = read_packet(sock_a)

    print(f"  Alice también ve el aviso de ingreso: {join_msg_to_alice.message!r}")

    welcome_to_bob = read_packet(sock_b)

    print(f"  Bob recibió el saludo del plugin: {welcome_to_bob.message!r}")


    print("\n== Alice manda un chat real por el socket ==")

    send_packet(sock_a, Message(0, "hola desde un socket TCP de verdad"))

    time.sleep(0.2)

    chat_seen_by_bob = read_packet(sock_b)

    print(f"  Bob recibió en su socket: {chat_seen_by_bob.message!r}")


    print("\n== Alice se mueve (PlayerTeleport real) ==")

    send_packet(sock_a, PlayerTeleport(-1, 10.0, 20.0, 30.0, 64, 32))

    time.sleep(0.2)

    move_seen_by_bob = read_packet(sock_b)

    print(f"  Bob ve el movimiento de Alice: id={move_seen_by_bob.player_id} pos=({move_seen_by_bob.x},{move_seen_by_bob.y},{move_seen_by_bob.z})")


    sock_a.close()

    sock_b.close()

    print("\n== TODO OK con sockets TCP reales, sin fakes ==")


if __name__ == "__main__":

    main()

