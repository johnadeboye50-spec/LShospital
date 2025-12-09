import os

class GeneralConfig:
    ADMIN_EMAIL="johnadeboye50@gmail.com"
    SQLALCHEMY_TRACK_MODIFICATIONS=False

class TestingConfig(GeneralConfig):
    SQLALCHEMY_DATABASE_URI="mysql+mysqlconnector://root@localhost/hospital"

class DevelopmentConfig(GeneralConfig):
    SQLALCHEMY_DATABASE_URI="mysql+mysqlconnector://root@localhost/hospital"

class LiveConfig(GeneralConfig):
    uri = os.environ.get("DATABASE_URL")

    # Fix postgres:// → postgresql://
    if uri and uri.startswith("postgres://"):
        uri = uri.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_DATABASE_URI = uri
