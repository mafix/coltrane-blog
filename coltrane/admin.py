from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from coltrane.models import Category, Entry, Link

class CategoryOptions(admin.ModelAdmin):
    prepopulated_fields = {
        'slug': ('title',),
    }

class EntryOptions(admin.ModelAdmin):
    date_hierarchy = 'pub_date'
    fieldsets = (
        (_('metadata'), { 'fields':
                       ('title', 'slug', 'pub_date', 'author', 'status', 'featured', 'enable_comments') }),
        (_('entry'), { 'fields':
                    ('excerpt', 'body') }),
        (_('categorization'), { 'fields':
                             ('tags', 'categories') }),
        )
    filter_horizontal = ('categories',)
    list_display = ('title', 'pub_date', 'author', 'status', 'enable_comments', '_get_comment_count', '_get_category_count')
    list_filter = ('status', 'categories')
    search_fields = ('excerpt', 'body', 'title')
    prepopulated_fields = {
        'slug': ('title',),
    }

class LinkOptions(admin.ModelAdmin):
    date_hierarchy = 'pub_date'
    fieldsets = (
        (_('metadata'), { 'fields':
                       ('title', 'slug', 'pub_date', 'posted_by', 'enable_comments', 'post_elsewhere') }),
        (_('link'), { 'fields':
                  ('url', 'description', 'tags', 'via_name', 'via_url') }),
        )
    list_display = ('title', 'enable_comments')
    search_fields = ('title', 'description')
    prepopulated_fields = {
        'slug': ('title',),
    }

admin.site.register(Category, CategoryOptions)
admin.site.register(Entry, EntryOptions)
admin.site.register(Link, LinkOptions)
