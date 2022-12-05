from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from easo.views import fileupload_locker, healthcheck

urlpatterns = [
    path("healthcheck", healthcheck),
    path("fileupload/locker2.jsp", fileupload_locker),
] + static(
    "/editorial/BF/2010/BFBC2/config/PC/",
    document_root=str(settings.BASE_DIR) + "/easo/static",
)
