from django.contrib import admin
from .models import News

@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ('title', 'channel', 'category', 'publication_date', 'url')
    search_fields = ('title', 'channel', 'category')
    list_filter = ('channel', 'category')
    date_hierarchy = 'publication_date'
    ordering = ('-publication_date', 'title')
    readonly_fields = ('created_at', 'updated_at')
