import re
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import current_app, g, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db
from ..models import OtpCode, User


PHONE_RE = re.compile(r"^\+221(70|75|76|77|78)\d{7}$")


def normalize_phone(value):
    phone = re.sub(r"[\s.-]", "", value or "")
    if phone.startswith("00221"):
        phone = "+221" + phone[5:]
    elif len(phone) == 9:
        phone = "+221" + phone
    return phone


def issue_otp(telephone):
    code = "1234" if current_app.config.get("TESTING") or current_app.debug else f"{__import__('secrets').randbelow(10000):04d}"
    expiry = datetime.now(timezone.utc) + timedelta(seconds=current_app.config["OTP_TTL_SECONDS"])
    OtpCode.query.filter_by(telephone=telephone, consumed=False).update({"consumed": True})
    db.session.add(OtpCode(telephone=telephone, code_hash=generate_password_hash(code), expires_at=expiry))
    db.session.commit()
    # TODO production: remettre le code à un fournisseur SMS. Il n'est exposé qu'en dev/test.
    return code


def verify_otp(telephone, code):
    record = OtpCode.query.filter_by(telephone=telephone, consumed=False).order_by(OtpCode.id.desc()).first()
    if not record:
        return False
    expiry = record.expires_at
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    if expiry < datetime.now(timezone.utc) or not check_password_hash(record.code_hash, code or ""):
        return False
    record.consumed = True
    db.session.commit()
    return True


def create_token(user):
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {"sub": str(user.id), "iat": now, "exp": now + timedelta(hours=current_app.config["TOKEN_TTL_HOURS"])},
        current_app.config["SECRET_KEY"], algorithm="HS256"
    )


def token_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return jsonify(error="Authentification requise"), 401
        try:
            payload = jwt.decode(header[7:], current_app.config["SECRET_KEY"], algorithms=["HS256"])
            g.user = db.session.get(User, int(payload["sub"]))
            if not g.user:
                raise ValueError
        except (jwt.PyJWTError, ValueError, TypeError):
            return jsonify(error="Jeton invalide ou expiré"), 401
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @token_required
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not g.user.is_admin:
            return jsonify(error="Accès administrateur requis"), 403
        return view(*args, **kwargs)
    return wrapped
