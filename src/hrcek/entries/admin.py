from django.contrib import admin

from hrcek.entries.models import Entry, Tag


class EntryAdmin(admin.ModelAdmin):
    list_display = ("display_title", "owner", "url", "created_at")
    list_filter = ("owner",)
    search_fields = ("title", "url", "notes")
    filter_horizontal = ("tags",)


class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "owner")
    list_filter = ("owner",)
    search_fields = ("name",)


admin.site.register(Entry, EntryAdmin)
admin.site.register(Tag, TagAdmin)
