from django.contrib import admin
from .models import TopPerson

@admin.register(TopPerson)
class TopPersonAdmin(admin.ModelAdmin):
    list_display = ('category', 'top_keys', 'created_at')


