from django.contrib import admin
from .models import NewsData

@admin.register(NewsData)
class NewsDataAdmin(admin.ModelAdmin):
    list_display  = ['item_id', 'date', 'category', 'title']
    list_filter   = ['category']
    search_fields = ['title', 'content']
    ordering      = ['-date']
