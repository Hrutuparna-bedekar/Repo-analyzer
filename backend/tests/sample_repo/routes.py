"""API routes for the sample application."""

from models import User, Post


def get_users() -> list:
    """Fetch all users."""
    return []


def create_user(username: str, email: str) -> User:
    """Create a new user."""
    user = User(username, email)
    user.save()
    return user


def get_user_posts(user: User) -> list:
    """Fetch all posts by a user."""
    return []


def create_post(title: str, content: str, author: User) -> Post:
    """Create a new blog post."""
    post = Post(title, content, author)
    post.publish()
    return post


def health_check() -> dict:
    """API health check endpoint."""
    return {"status": "ok"}
