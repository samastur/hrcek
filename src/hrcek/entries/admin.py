from django.contrib import admin

from hrcek.entries.models import Entry, FieldDefinition, FieldValue, Tag


class EntryAdmin(admin.ModelAdmin):
    list_display = ("display_title", "owner", "url", "created_at")
    list_filter = ("owner",)
    search_fields = ("title", "url", "notes")
    filter_horizontal = ("tags",)


class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "owner")
    list_filter = ("owner",)
    search_fields = ("name",)


class FieldDefinitionAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "kind")
    list_filter = ("owner", "kind")
    search_fields = ("name",)


class FieldValueAdmin(admin.ModelAdmin):
    list_display = ("entry", "definition", "value")
    list_filter = ("definition",)


admin.site.register(Entry, EntryAdmin)
admin.site.register(FieldDefinition, FieldDefinitionAdmin)
admin.site.register(FieldValue, FieldValueAdmin)
admin.site.register(Tag, TagAdmin)
