#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function for displaying messages
print_step() {
    echo -e "${BLUE}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✔ $1${NC}"
}

print_error() {
    echo -e "${RED}✖ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Function for checking the success of command execution
check_status() {
    if [ $? -ne 0 ]; then
        print_error "$1"
        exit 1
    fi
}

echo -e "${GREEN}"
echo "╔════════════════════════════════════════╗"
echo "║     Blog API - Automated Setup         ║"
echo "╔════════════════════════════════════════╗"
echo -e "${NC}"

# Go to the root of the project (one level above scripts/)
cd "$(dirname "$0")/.." || exit 1


# Step 1: Check environment variables
# ============================================
print_step "Checking environment variables..."

ENV_FILE="settings/.env"

if [ ! -f "$ENV_FILE" ]; then
    print_error "File settings/.env not found!"
    echo "Create a file based on settings/.env.example"
    echo "cp settings/.env.example settings/.env"
    exit 1
fi

# Array of required variables
required_vars=(
    "BLOG_SECRET_KEY"
    "BLOG_DEBUG"
)

# Check each variable
missing_vars=()
for var in "${required_vars[@]}"; do
    value=$(grep "^${var}=" "$ENV_FILE" | cut -d '=' -f2- | xargs)
    if [ -z "$value" ]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -ne 0 ]; then
    print_error "Missing or empty variables in settings/.env:"
    for var in "${missing_vars[@]}"; do
        echo "  - $var"
    done
    exit 1
fi

print_success "All environment variables are present and valid"

# ============================================
# Step 2: Create virtual environment
# ============================================
print_step "Checking virtual environment..."

if [ ! -d "venv" ]; then
    print_step "Creating virtual environment..."
    python3 -m venv venv
    check_status "Failed to create virtual environment"
    print_success "Virtual environment created"
else
    print_warning "Virtual environment already exists"
fi

# Activate the virtual environment
source venv/bin/activate
check_status "Failed to activate virtual environment"

# ============================================
# Step 3: Install dependencies
# ============================================
print_step "Installing dependencies..."

pip install --upgrade pip -q
pip install -r requirements/dev.txt -q
check_status "Failed to install dependencies"

print_success "Dependencies installed"

# ============================================
# Step 4: Database migrations
# ============================================
print_step "Applying migrations..."

python manage.py migrate
check_status "Migrations failed"

print_success "Migrations applied"

# ============================================
# Step 5: Collect static files
# ============================================
print_step "Collecting static files..."

python manage.py collectstatic --noinput -c
check_status "Failed to collect static files"

print_success "Static files collected"

# ============================================
# Step 6: Compile translations
# ============================================
print_step "Compiling translation files..."

python manage.py compilemessages
check_status "Failed to compile translations"

print_success "Translations compiled"

# ============================================
# Step 7: Create superuser
# ============================================
print_step "Checking superuser..."

SUPERUSER_EMAIL="admin@blog-api.com"
SUPERUSER_PASSWORD="admin123"

# Check if the superuser exists
python manage.py shell -c "from apps.users.models import User; exit(0 if User.objects.filter(email='$SUPERUSER_EMAIL').exists() else 1)"

if [ $? -eq 0 ]; then
    print_warning "Superuser already exists"
else
    print_step "Creating superuser..."
    
    python manage.py shell << EOF
from apps.users.models import User
User.objects.create_superuser(
    email='$SUPERUSER_EMAIL',
    password='$SUPERUSER_PASSWORD',
    first_name='Admin',
    last_name='User'
)
EOF
    
    check_status "Failed to create superuser"
    print_success "Superuser created"
fi

# ============================================
# Step 8: Load test data
# ============================================
print_step "Loading test data..."

python manage.py shell << 'EOF'
import sys
from apps.users.models import User
from apps.blog.models import Category, CategoryTranslation, Tag, Post, Comment

# Check if test data already exists
if Post.objects.exists():
    print("Test data already exists, skipping...")
    sys.exit(0)

print("Creating test data...")

# Create users
users = []
for i in range(1, 6):
    user, created = User.objects.get_or_create(
        email=f'user{i}@test.com',
        defaults={
            'first_name': f'User{i}',
            'last_name': f'Test',
            'language': ['en', 'ru', 'kk'][i % 3],
            'timezone': ['UTC', 'Asia/Almaty', 'Europe/Moscow'][i % 3]
        }
    )
    if created:
        user.set_password('password123')
        user.save()
    users.append(user)

print(f"Created {len(users)} users")

# Create categories with translations
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
    
    # Create translations
    for lang, name in cat_data['translations'].items():
        CategoryTranslation.objects.get_or_create(
            category=category,
            language=lang,
            defaults={'name': name}
        )
    
    categories.append(category)

print(f"Created {len(categories)} categories")

# Create tags
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

print(f"Created {len(tags)} tags")

# Create posts
statuses = [Post.Status.PUBLISHED, Post.Status.DRAFT]
posts = []

for i in range(1, 16):
    post, created = Post.objects.get_or_create(
        slug=f'post-{i}',
        defaults={
            'author': users[i % len(users)],
            'title': f'Post number {i}',
            'body': f'This is the content of post number {i}. ' * 10,
            'category': categories[i % len(categories)],
            'status': statuses[i % 2]
        }
    )
    
    if created:
        # Добавляем случайные теги
        post.tags.add(*tags[i % 3:(i % 3) + 2])
    
    posts.append(post)

print(f"Created {len(posts)} posts")

# Create comments
comments_count = 0
for post in posts[:10]:  # Комментарии только к первым 10 постам
    for j in range(3):  # По 3 комментария на пост
        Comment.objects.get_or_create(
            post=post,
            author=users[j % len(users)],
            defaults={
                'body': f'Комментарий {j+1} к посту "{post.title}"'
            }
        )
        comments_count += 1

print(f"Создано {comments_count} комментариев")
print("✔ Тестовые данные успешно загружены!")
EOF

check_status "Failed to load test data"

print_success "Test data loaded"

# ============================================
# Step 9: Starting the server
# ============================================
echo ""
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║        Setup Complete! 🚀              ║${NC}"
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo ""
echo -e "${BLUE}URLs:${NC}"
echo "  📄 API:          http://127.0.0.1:8000/api/"
echo "  📖 Swagger UI:   http://127.0.0.1:8000/api/docs/"
echo "  📋 ReDoc:        http://127.0.0.1:8000/api/redoc/"
echo "  🔧 Admin:        http://127.0.0.1:8000/admin/"
echo ""
echo -e "${BLUE}Superuser credentials:${NC}"
echo "  Email:    $SUPERUSER_EMAIL"
echo "  Password: $SUPERUSER_PASSWORD"
echo ""
echo -e "${BLUE}Test users:${NC}"
echo "  user1@test.com ... user5@test.com"
echo "  Password: password123"
echo ""
print_step "Starting server..."
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
echo ""

python manage.py runserver