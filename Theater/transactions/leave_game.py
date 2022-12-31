from BFBC2_MasterServer.packet import Packet
from Theater.models import Game
from django.core.cache import cache


async def leave_game(connection, message):
    lid = message.Get("LID")
    gid = message.Get("GID")

    if connection.pid:
        queue_str = cache.get_or_set(f"queue:{gid}", "", timeout=None)
        queue_list = queue_str.split(";")
        queue_list.remove(str(connection.pid))
        cache.set(f"queue:{gid}", ";".join(queue_list), timeout=None)

        cache.delete(f"players:{gid}:{connection.pid}")
        cache.delete(f"playerData:{gid}:{connection.pid}")
    
    connection.pid = None

    response = Packet()
    response.Set("LID", lid)
    response.Set("GID", gid)

    yield response
