import os


class Config:
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # HU-6: timeout y multithreading seguro para concurrencia en SQLite
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {"timeout": 30, "check_same_thread": False}
    }


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///subastas.db"
    )


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {
        "connect_args": {"check_same_thread": False},
    }
