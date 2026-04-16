"""Database models for the sample application."""

from config import Config


class BaseModel:
    """Base class for all database models."""

    def save(self):
        """Persist the model to database."""
        pass

    def delete(self):
        """Remove the model from database."""
        pass


class User(BaseModel):
    """Represents a user in the system."""

    def __init__(self, username: str, email: str):
        self.username = username
        self.email = email

    def get_profile(self) -> dict:
        """Return user profile data."""
        return {"username": self.username, "email": self.email}

    def update_email(self, new_email: str):
        """Update user email address."""
        self.email = new_email
        self.save()


class Post(BaseModel):
    """Represents a blog post."""

    def __init__(self, title: str, content: str, author: User):
        self.title = title
        self.content = content
        self.author = author

    def publish(self):
        """Publish the post."""
        self.save()

    def get_summary(self) -> str:
        """Return first 100 characters of content."""
        return self.content[:100]
