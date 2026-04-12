from django.core.management.base import BaseCommand
from django.db import transaction
from apps.users.models import User
from apps.blog.models import Category, CategoryTranslation, Tag, Post, Comment
import sys


class Command(BaseCommand):
    help = 'Загружает тестовые данные в базу'
    
    def handle(self, *args, **options):
        if Post.objects.exists():
            self.stdout.write(self.style.WARNING('Данные уже существуют, пропускаем...'))
            return
        
        self.stdout.write('Создаём тестовые данные...')
        
        with transaction.atomic():
            # Create users
            users = self.create_users()
            self.stdout.write(self.style.SUCCESS(f'✓ Created {len(users)} users'))
            
            # Create categories
            categories = self.create_categories()
            self.stdout.write(self.style.SUCCESS(f'✓ Created {len(categories)} categories'))
            
            # Create tags
            tags = self.create_tags()
            self.stdout.write(self.style.SUCCESS(f'✓ Created {len(tags)} tags'))
            
            # Create posts
            posts = self.create_posts(users, categories, tags)
            self.stdout.write(self.style.SUCCESS(f'✓ Created {len(posts)} posts'))
            
            # Create comments
            comments_count = self.create_comments(users, posts)
            self.stdout.write(self.style.SUCCESS(f'✓ Created {comments_count} comments'))
        
        self.stdout.write(self.style.SUCCESS('✓ Test data loaded successfully!'))
    
    def create_users(self):
        users = []
        for i in range(1, 6):
            user, created = User.objects.get_or_create(
                email=f'user{i}@test.com',
                defaults={
                    'first_name': f'User{i}',
                    'last_name': 'Test',
                    'language': ['en', 'ru', 'kk'][i % 3],
                    'timezone': ['UTC', 'Asia/Almaty', 'Europe/Moscow'][i % 3]
                }
            )
            if created:
                user.set_password('password123')
                user.save()
            users.append(user)
        return users
    
    def create_categories(self):
        categories_data = [
            {
                'slug': 'technology',
                'translations': {
                    'en': 'Technology',
                    'ru': 'Технологии',
                    'kk': 'Технология'
                }
            },
            {
                'slug': 'sport',
                'translations': {
                    'en': 'Sport',
                    'ru': 'Спорт',
                    'kk': 'Спорт'
                }
            },
            {
                'slug': 'news',
                'translations': {
                    'en': 'News',
                    'ru': 'Новости',
                    'kk': 'Жаңалықтар'
                }
            },
            {
                'slug': 'education',
                'translations': {
                    'en': 'Education',
                    'ru': 'Образование',
                    'kk': 'Білім'
                }
            }
        ]
        
        categories = []
        for cat_data in categories_data:
            category, created = Category.objects.get_or_create(slug=cat_data['slug'])
            
            for lang, name in cat_data['translations'].items():
                CategoryTranslation.objects.get_or_create(
                    category=category,
                    language=lang,
                    defaults={'name': name}
                )
            
            categories.append(category)
        
        return categories
    
    def create_tags(self):
        tags_data = [
            'python', 'django', 'rest-api', 'javascript',
            'react', 'docker', 'postgresql', 'redis'
        ]
        
        tags = []
        for tag_name in tags_data:
            tag, created = Tag.objects.get_or_create(
                name=tag_name,
                defaults={'slug': tag_name}
            )

            tags.append(tag)
        
        return tags
    
    def create_posts(self, users, categories, tags):
        statuses = [Post.Status.PUBLISHED, Post.Status.DRAFT]
        posts = []
        
        for i in range(1, 16):
            post, created = Post.objects.get_or_create(
                slug=f'post-{i}',
                defaults={
                    'author': users[i % len(users)],
                    'title': f'Пост номер {i}',
                    'body': f'Это содержание поста номер {i}. ' * 10,
                    'category': categories[i % len(categories)],
                    'status': statuses[i % 2]
                }
            )
            
            if created:
                post.tags.add(*tags[i % 3:(i % 3) + 2])
            
            posts.append(post)
        
        return posts
    
    def create_comments(self, users, posts):
        comments_count = 0
        for post in posts[:10]:
            for j in range(3):
                Comment.objects.get_or_create(
                    post=post,
                    author=users[j % len(users)],
                    defaults={
                        'body': f'Комментарий {j+1} к посту "{post.title}"'
                    }
                )
                comments_count += 1
        
        return comments_count
