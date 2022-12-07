from django.contrib import admin

from Theater.models import Game, Lobby


# Register your models here.
class LobbyAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "name",
        "locale",
        "maxGames",
    ]
    list_filter = (
        "name",
        "locale",
    )


class GameAdmin(admin.ModelAdmin):
    list_display = ["id", "lobby", "name"]
    list_filter = ("lobby", "name")


admin.site.register(Lobby, LobbyAdmin)
admin.site.register(Game, GameAdmin)
