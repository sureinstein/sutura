import io
import uuid
from pathlib import Path

from flask import current_app
from PIL import Image, ImageOps, UnidentifiedImageError


def save_compressed_image(file_storage):
    try:
        image = Image.open(file_storage.stream)
        image = ImageOps.exif_transpose(image).convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("La photo doit être une image valide") from exc
    image.thumbnail((1600, 1600))
    quality = 82
    data = io.BytesIO()
    while quality >= 35:
        data.seek(0)
        data.truncate()
        image.save(data, format="WEBP", quality=quality, method=6)
        if data.tell() <= current_app.config["MAX_IMAGE_BYTES"]:
            break
        quality -= 8
    if data.tell() > current_app.config["MAX_IMAGE_BYTES"]:
        raise ValueError("Impossible de compresser la photo sous 200 Ko")
    filename = f"{uuid.uuid4().hex}.webp"
    Path(current_app.config["UPLOAD_FOLDER"], filename).write_bytes(data.getvalue())
    return filename
