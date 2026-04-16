"""Main application entry point for the sample project."""

from config import Config
from models import User
from routes import create_user, create_post, health_check


class Application:
    """Main application class."""

    def __init__(self):
        self.config = Config()
        self.running = False

    def start(self):
        """Start the application."""
        self.running = True
        result = health_check()
        print(f"App started: {result}")

    def stop(self):
        """Stop the application."""
        self.running = False


def main():
    """Application entry point."""
    app = Application()
    app.start()

    # Demo usage
    user = create_user("john", "john@example.com")
    post = create_post("Hello World", "This is my first post!", user)

    app.stop()


if __name__ == "__main__":
    main()
