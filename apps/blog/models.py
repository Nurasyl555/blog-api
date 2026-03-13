from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _, get_language
# Create your models here.
class Category(models.Model):
    """
    Category for post
    """
    #name = models.CharField(max_length=100, unique=True, verbose_name=_('name'))
    slug = models.SlugField(unique=True, verbose_name=_('slug'))

    class Meta:
        verbose_name = _('Category')
        verbose_name_plural = _('Categories')

    def __str__(self) -> str:
        translation = self.translations.filter(language=get_language()).first()
        if translation:
            return translation.name
        en_translation = self.translations.filter(language='en').first()
        return en_translation.name if en_translation else self.slug
    
    def get_name(self, language: str = None) -> str:
        """Get name in current language"""
        if language is None:
            # Получаем текущий язык (может вернуть ru-ru, en-us и тд)
            raw_lang = get_language() or 'en'
            # Отрезаем всё после дефиса, оставляем только 'ru', 'en', 'kk'
            language = raw_lang.split('-')[0] 

        # Ищем перевод строго по 2 буквам
        translation = self.translations.filter(language=language).first()
        if translation:
            return translation.name

        # Fallback to en
        en_translation = self.translations.filter(language='en').first()
        return en_translation.name if en_translation else self.slug

class CategoryTranslation(models.Model):
    """Translation name category"""
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='translations',
        verbose_name=_('Category')
    )
    language = models.CharField(
        max_length=5,
        choices=[('en', 'English'), ('ru', 'Русский'), ('kk', 'Қазақша')],
        verbose_name=_('Language')
    )
    name = models.CharField(max_length=100, verbose_name=_('Name'))

    class Meta:
        unique_together = ['category', 'language']
        verbose_name = _('Translate category')
        verbose_name_plural = _('Translate categories')
    
    def __str__(self) -> str:
        return f'{self.category.slug} - {self.language}: {self.name}'


class Tag(models.Model):
    """
    Docstring for Tag
    """
    name = models.CharField(max_length=50, unique=True, verbose_name=_('name'))
    slug = models.SlugField(unique=True, verbose_name=_('slug'))

    class Meta:
        verbose_name = _('Tag')
        verbose_name_plural = _('Tags')

    def __str__(self) -> str:
        return self.name


class Post(models.Model):
    """
    Post for blog
    """
    class Status(models.TextChoices):
        DRAFT = 'draft', _('draft')
        PUBLISHED = 'published', _('published')
    
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='posts',
        verbose_name=_('author')
    )
    title = models.CharField(max_length=200, verbose_name=_('title'))
    slug = models.SlugField(unique=True, verbose_name=_('slug'))
    body = models.TextField(verbose_name=_('content'))
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='posts',
        verbose_name=_('Category')
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name='posts', verbose_name=_('Tags'))
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name=_('Status')
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated'))

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Post')
        verbose_name_plural = _('Posts')
    
    def __str__(self)-> str:
        return self.title
    

class Comment(models.Model):
    post = models.ForeignKey(
        Post, 
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name=_('Post')
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name=_('Author')
    )
    body = models.TextField(verbose_name=_('Text'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created'))

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Comment')
        verbose_name_plural = _('Comments')
    
    def __str__(self):
        comment_from = _("Comment from")
        for_text = _("for")
        return f'{comment_from} {self.author.email} {for_text} "{self.post.title}"'