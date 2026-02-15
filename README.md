# Blog API

REST API for a blog with JWT authentication.

## ERD (Entity-Relationship Diagram)

![ERD](docs/erd.png)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/Nurasyl555/blog-api.git
cd blog-api
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate # Linux/Mac
venv\Scripts\activate # Windows
```

3. Install dependencies:
```bash
pip install -r requirements/dev.txt
```

4. Create a `.env` file in the folder `settings/`:
```env
BLOG_SECRET_KEY=your-secret-key
BLOG_DEBUG=True
```

5. Apply migrations:
```bash
python manage.py migrate
```

6. Create a superuser:
```bash
python manage.py createsuperuser
```

7. Start Redis:
```bash
redis-server
```

8. Start the server:
```bash
python manage.py runserver
```

## API Endpoints

### Authentication
- `POST /api/auth/register/` - Registration (5 req/min)
- `POST /api/auth/token/` - Receive tokens (10 req/min)
- `POST /api/auth/token/refresh/` - Refresh access token

### Posts
- `GET /api/posts/` - List of posts (cached for 60 seconds)
- `POST /api/posts/` - Create a post (20 req/min)
- `GET /api/posts/{slug}/` - Single post
- `PATCH /api/posts/{slug}/` - Update post
- `DELETE /api/posts/{slug}/` - Delete post

### Comments
- `GET /api/posts/{slug}/comments/` - Comments on a post
- `POST /api/posts/{slug}/comments/` - Add a comment

## Redis Pub/Sub

To listen for comment events:
```bash
python manage.py listen_comments
```

## Technologies

- Django 5.0
- Django REST Framework
- JWT Authentication
- Redis (cache, rate limiting, pub/sub)
- SQLite (dev) / PostgreSQL (prod)