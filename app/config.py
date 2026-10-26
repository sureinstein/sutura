import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'instance' / 'sutura.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    OTP_TTL_SECONDS = int(os.getenv("OTP_TTL_SECONDS", "300"))
    TOKEN_TTL_HOURS = int(os.getenv("TOKEN_TTL_HOURS", "168"))
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", str(BASE_DIR / "instance" / "uploads"))
    MAX_IMAGE_BYTES = int(os.getenv("MAX_IMAGE_BYTES", "204800"))
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    ADMIN_TELEPHONE = os.getenv("ADMIN_TELEPHONE", "+221770000000")
    NOMINATIM_URL = os.getenv("NOMINATIM_URL", "https://nominatim.openstreetmap.org")
