from django.contrib import admin
from apps.blog.models import Category, Tag, Post, Comment, CategoryTranslation

# Создаем встроенную панель для переводов
class CategoryTranslationInline(admin.TabularInline):
    model = CategoryTranslation
    extra = 3
    max_num = 3

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['slug', 'get_names']
    prepopulated_fields = {'slug': ('slug',)}
    inlines = [CategoryTranslationInline]
    
    def get_names(self, obj):
        """Show all translation"""
        translations = obj.translations.all()
        return ' | '.join([f'{t.language}: {t.name}' for t in translations])
    get_names.short_description = 'Name'

@admin.register(Tag)
class Tagadmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Post)
class Postadmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'category', 'status', 'created_at']
    list_filter = ['status', 'category', 'created_at']
    search_fields = ['title', 'body']
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'created_at'

    filter_horizontal = ['tags']

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['post', 'author', 'created_at']
    list_filter = ['created_at']
    search_fields = ['body', 'author_email']