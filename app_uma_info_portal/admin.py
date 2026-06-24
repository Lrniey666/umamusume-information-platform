from django.contrib import admin
from .models import (
    DiscordUser, DiscordGuild, GuildSetting,
    GuildChannelRule, GuildSettingAudit,
    GuildChannelCache, GuildRoleCache,
)


@admin.register(DiscordUser)
class DiscordUserAdmin(admin.ModelAdmin):
    list_display  = ('username', 'discord_id', 'last_login_at', 'token_expires_at')
    search_fields = ('username', 'discord_id')
    readonly_fields = ('access_token_enc', 'refresh_token_enc', 'last_login_at', 'created_at')


class GuildSettingInline(admin.StackedInline):
    model = GuildSetting
    extra = 0


class GuildChannelRuleInline(admin.TabularInline):
    model = GuildChannelRule
    extra = 0


@admin.register(DiscordGuild)
class DiscordGuildAdmin(admin.ModelAdmin):
    list_display  = ('name', 'guild_id', 'is_bot_present', 'member_count', 'joined_at')
    list_filter   = ('is_bot_present',)
    search_fields = ('name', 'guild_id')
    inlines       = [GuildSettingInline, GuildChannelRuleInline]


@admin.register(GuildSetting)
class GuildSettingAdmin(admin.ModelAdmin):
    list_display  = ('guild', 'read_scope', 'news_enabled', 'ai_chat_enabled', 'updated_at')
    list_filter   = ('read_scope', 'news_enabled', 'ai_chat_enabled')


@admin.register(GuildSettingAudit)
class GuildSettingAuditAdmin(admin.ModelAdmin):
    list_display  = ('guild', 'changed_by', 'field_name', 'old_value', 'new_value', 'changed_at')
    list_filter   = ('field_name',)
    readonly_fields = ('guild', 'changed_by', 'changed_at', 'field_name', 'old_value', 'new_value')
