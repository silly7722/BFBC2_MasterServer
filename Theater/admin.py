from django.contrib import admin

from Theater.models import Game, GameDescription, Lobby, PlayerData


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


class GameDescriptionAdmin(admin.ModelAdmin):
    list_display = ["id", "index", "owner", "text"]
    list_filter = ("owner",)


class PlayerDataAdmin(admin.ModelAdmin):
    list_display = ["id", "index", "owner", "data"]
    list_filter = ("owner",)


admin.site.register(Lobby, LobbyAdmin)
admin.site.register(Game, GameAdmin)
admin.site.register(GameDescription, GameDescriptionAdmin)
admin.site.register(PlayerData, PlayerDataAdmin)
