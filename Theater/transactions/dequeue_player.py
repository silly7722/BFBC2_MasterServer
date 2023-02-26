from django.core.cache import cache

from BFBC2_MasterServer.packet import Packet


async def dequeue_player(connection, message):
    gid = message.Get("GID")
    pid = message.Get("PID")

    queue_str = cache.get_or_set(f"queue:{gid}", "", timeout=None)
    queue_list = queue_str.split(";")
    queue_list.remove(str(pid))
    cache.set(f"queue:{gid}", ";".join(queue_list), timeout=None)

    cache.delete(f"players:{gid}:{pid}")
    cache.delete(f"playerData:{gid}:{pid}")

    yield Packet()
