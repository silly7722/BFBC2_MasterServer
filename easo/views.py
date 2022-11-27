from django.core.cache import cache
from django.http import HttpResponse
from django.views.defaults import server_error

# Create your views here.


def fileupload_locker(request):
    # More-or-less original server behaviour

    cmd = request.GET.get("cmd", None)

    if cmd != "dir":
        return server_error(request)

    lkey = request.GET.get("lkey")
    personaId = cache.get(f"lkeyMap:{lkey}")

    locker = '<?xml version="1.0" encoding="UTF-8"?>'

    if not personaId:
        locker += '<LOCKER error="2"/>'
        return HttpResponse(locker, content_type="text/xml")

    game = request.GET.get("game")

    if game != "/eagames/BFBC2":
        return HttpResponse("This request requires HTTP authentication.", status=401)

    pers = request.GET.get("pers")
    locker += f'<LOCKER error="0" game="{game}" maxBytes="2867200" maxFiles="10" numBytes="0" numFiles="0" ownr="{personaId}" pers="{pers}"/>'

    return HttpResponse(locker, content_type="text/xml")
