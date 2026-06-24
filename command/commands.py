import os


def handle_command(server, player, raw: str) -> None:
    parts = raw.strip().split()
    if not parts:
        return
    cmd, args = parts[0].lower(), parts[1:]

    if server.plugin_manager and server.plugin_manager.fire_command(player, cmd, args):
        return

    if cmd == "help":
        _cmd_help(server, player)
    elif cmd in ("players", "who", "list"):
        _cmd_players(server, player)
    elif cmd == "spawn":
        _cmd_spawn(server, player)
    elif cmd == "pos":
        _cmd_pos(server, player)
    elif cmd == "me" and args:
        _cmd_me(server, player, args)
    elif cmd in ("msg", "tell", "pm") and args:
        _cmd_msg(server, player, args)
    elif cmd in ("r", "reply") and args:
        _cmd_reply(server, player, args)
    elif cmd == "plugins":
        _cmd_plugins(server, player)
    elif cmd == "tp" and player.op:
        _cmd_tp(server, player, args)
    elif cmd == "kick" and player.op:
        _cmd_kick(server, player, args)
    elif cmd == "ban" and player.op:
        _cmd_ban(server, player, args)
    elif cmd == "unban" and player.op:
        _cmd_unban(server, player, args)
    elif cmd == "op" and player.op and args:
        _cmd_op(server, player, args, grant=True)
    elif cmd == "deop" and player.op and args:
        _cmd_op(server, player, args, grant=False)
    elif cmd == "setspawn" and player.op:
        _cmd_setspawn(server, player)
    elif cmd == "save" and player.op:
        _cmd_save(server, player)
    elif cmd == "reload" and player.op:
        _cmd_reload(server, player, args)
    else:
        player.send_message("&cUnknown command. Try /help")


def _cmd_help(server, player):
    cmds = "/help /players /who /spawn /pos /me /msg /r /plugins"
    if player.op:
        cmds += " /tp /kick /ban /unban /op /deop /setspawn /save /reload"
    if server.plugin_manager:
        extra = " ".join(f"/{k}" for k in server.plugin_manager.get_commands())
        if extra:
            cmds += " " + extra
    player.send_message(f"&fCommands: {cmds}")


def _cmd_players(server, player):
    all_p = server.players.get_all()
    names = "&f, &a".join(p.name for p in all_p)
    player.send_message(f"&fOnline ({len(all_p)}): &a{names}")


def _cmd_spawn(server, player):
    player.send_teleport(
        server.world.spawn_x, server.world.spawn_y, server.world.spawn_z,
        server.world.spawn_yaw, server.world.spawn_pitch,
    )
    player.send_message("&aTeleported to spawn")


def _cmd_pos(server, player):
    player.send_message(f"&fPosition: &a{player.x:.1f}, {player.y:.1f}, {player.z:.1f}")


def _cmd_me(server, player, args):
    action = " ".join(args)
    server.players.broadcast_message(f"&5* {player.name} {action}")
    server.log(f"* {player.name} {action}")


def _cmd_msg(server, player, args):
    if len(args) < 2:
        player.send_message("&cUsage: /msg <player> <message>"); return
    target = server.players.find_by_name(args[0])
    if target is None:
        player.send_message("&cPlayer not found"); return
    if target.player_id == player.player_id:
        player.send_message("&cYou can't message yourself"); return
    msg_text = " ".join(args[1:])
    player.send_message(f"&7[&fYou &7-> &f{target.name}&7] &f{msg_text}")
    target.send_message(f"&7[&f{player.name} &7-> &fYou&7] &f{msg_text}")
    server.log(f"[PM] {player.name} -> {target.name}: {msg_text}")
    server._pm_last[str(target.uuid)] = player.player_id
    server._pm_last[str(player.uuid)] = target.player_id


def _cmd_reply(server, player, args):
    last_id = server._pm_last.get(str(player.uuid))
    if last_id is None:
        player.send_message("&cNo one to reply to"); return
    target = server.players.get_by_id(last_id)
    if target is None:
        player.send_message("&cThat player is no longer online"); return
    msg_text = " ".join(args)
    player.send_message(f"&7[&fYou &7-> &f{target.name}&7] &f{msg_text}")
    target.send_message(f"&7[&f{player.name} &7-> &fYou&7] &f{msg_text}")
    server.log(f"[PM] {player.name} -> {target.name}: {msg_text}")
    server._pm_last[str(target.uuid)] = player.player_id
    server._pm_last[str(player.uuid)] = target.player_id


def _cmd_plugins(server, player):
    if not server.plugin_manager or not server.plugin_manager.plugins:
        player.send_message("&fNo plugins loaded"); return
    names = "&f, &a".join(f"{p.name} &7v{p.version}" for p in server.plugin_manager.plugins)
    player.send_message(f"&fPlugins ({len(server.plugin_manager.plugins)}): &a{names}")


def _cmd_tp(server, player, args):
    if not args:
        player.send_message("&cUsage: /tp <player>"); return
    target = server.players.find_by_name(args[0])
    if target is None:
        player.send_message("&cPlayer not found"); return
    player.send_teleport(target.x, target.y, target.z, target.yaw, target.pitch)
    player.send_message(f"&aTeleported to {target.name}")


def _cmd_kick(server, player, args):
    if not args:
        player.send_message("&cUsage: /kick <player> [reason]"); return
    reason = " ".join(args[1:]) or "Kicked by an operator"
    target = server.players.find_by_name(args[0])
    if target is None:
        player.send_message("&cPlayer not found"); return
    target.kick(reason)
    server.players.broadcast_message(f"&c{args[0]} was kicked: {reason}")
    server.log(f"{player.name} kicked {args[0]}: {reason}")


def _cmd_ban(server, player, args):
    if not args:
        player.send_message("&cUsage: /ban <player>"); return
    name = args[0]
    _append_list(os.path.join(server.base_dir, "banned.txt"), name)
    server.banned_players.add(name.lower())
    target = server.players.find_by_name(name)
    if target is not None:
        target.kick("Banned by an operator")
    server.players.broadcast_message(f"&c{name} was banned")
    server.log(f"{player.name} banned {name}")


def _cmd_unban(server, player, args):
    if not args:
        player.send_message("&cUsage: /unban <player>"); return
    _remove_list(os.path.join(server.base_dir, "banned.txt"), args[0])
    server.banned_players.discard(args[0].lower())
    player.send_message(f"&a{args[0]} was unbanned")


def _cmd_op(server, player, args, grant: bool):
    server.set_op(args[0], grant)
    msg = f"&a{args[0]} is now an operator" if grant else f"&c{args[0]} is no longer an operator"
    player.send_message(msg)


def _cmd_setspawn(server, player):
    server.world.spawn_x = player.x
    server.world.spawn_y = player.y
    server.world.spawn_z = player.z
    server.world.spawn_yaw = player.yaw
    server.world.spawn_pitch = player.pitch
    server._do_save()
    player.send_message("&aSpawn point updated")


def _cmd_save(server, player):
    server._do_save()
    player.send_message("&aWorld saved")


def _cmd_reload(server, player, args):
    if not args:
        player.send_message("&cUsage: /reload <plugin>"); return
    if not server.plugin_manager:
        player.send_message("&cPlugin system unavailable"); return
    ok = server.plugin_manager.reload(args[0])
    if ok:
        player.send_message(f"&aPlugin {args[0]} reloaded")
        server.log(f"{player.name} reloaded plugin {args[0]}")
    else:
        player.send_message(f"&cPlugin '{args[0]}' not found")


def _append_list(path: str, entry: str) -> None:
    with open(path, "a") as f:
        f.write(entry + "\n")


def _remove_list(path: str, entry: str) -> None:
    try:
        with open(path) as f:
            lines = f.readlines()
        with open(path, "w") as f:
            f.writelines(l for l in lines if l.strip().lower() != entry.lower())
    except FileNotFoundError:
        pass
