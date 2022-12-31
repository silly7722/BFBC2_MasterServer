import random
import string
from BFBC2_MasterServer.packet import Packet
from django.core.cache import cache
from Plasma.models import Persona
from channels.auth import database_sync_to_async

from Theater.models import Game


async def queue_update(connection, message):
    # {
    #    "LID": int,
    #    "GID": int,
    #    "QUEUE": int,
    #    "TID": int
    # }

    lid = message.Get("LID")
    gid = message.Get("GID")

    game = await Game.objects.get_game(lid, gid)

    if not game:
        return

    pid = message.Get("QUEUE")
    
    queue_str = cache.get_or_set(f"queue:{gid}", "", timeout=None)
    queue_list = queue_str.split(";")
    
    idx = queue_list.index(str(pid)) - 1
    playerSession = cache.get(f"players:{gid}:{pid}")
    
    serverFull = game.activePlayers + 1 > game.maxPlayers

    if serverFull:
        queueInfoNotice = {
            "QPOS": idx,
            "QLEN": len(queue_list) - 1,
            "LID": lid,
            "GID": gid,
        }

        await connection.send_remote_message(playerSession, "QLEN", queueInfoNotice)

    yield Packet()

    if serverFull:
        return
    
    playerData = cache.get(f"playerData:{gid}:{pid}")

    persona_id, int_addr, addr, ptype = playerData.split(";")
    persona = await database_sync_to_async(Persona.objects.get)(id=persona_id)

    int_ip, int_port = int_addr.split(":")
    ip, port = addr.split(":")

    # Ticket is random 10 digit number, it has to be sent to both client and server
    ticket = "".join(random.choices(string.digits, k=10))

    enterGameHostRequest = Packet(service="EGRQ")
    enterGameHostRequest.Set("R-INT-IP", int_ip)
    enterGameHostRequest.Set("R-INT-PORT", int_port)
    enterGameHostRequest.Set("IP", ip)
    enterGameHostRequest.Set("PORT", port)
    enterGameHostRequest.Set("NAME", persona.name)
    enterGameHostRequest.Set("PTYPE", ptype)
    enterGameHostRequest.Set("TICKET", ticket)
    enterGameHostRequest.Set("PID", pid)
    enterGameHostRequest.Set("UID", persona.id)
    enterGameHostRequest.Set("LID", lid)
    enterGameHostRequest.Set("GID", gid)

    yield enterGameHostRequest

    owner = await Game.objects.get_game_owner(lid, gid)

    enterGameNotice = {
        "PL": connection.plat.value,
        "TICKET": ticket,
        "PID": pid,
        "I": game.addrIp,
        "P": game.addrPort,
        "HUID": owner.id,
        "INT-PORT": game.addrPort,
        "INT-IP": game.addrIp,
        "EKEY": game.ekey,
        "UGID": game.ugid,
        "LID": lid,
        "GID": gid,
    }

    await connection.send_remote_message(playerSession, "EGEG", enterGameNotice)
