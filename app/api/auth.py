from flask import Blueprint, jsonify, request

from ..extensions import db
from ..models import User
from ..services.auth import create_token, issue_otp, normalize_phone, token_required, verify_otp, PHONE_RE

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/request-otp")
def request_otp():
    telephone = normalize_phone((request.get_json(silent=True) or {}).get("telephone"))
    if not PHONE_RE.match(telephone):
        return jsonify(error="Numéro mobile sénégalais invalide"), 400
    code = issue_otp(telephone)
    response = {"message": "Code envoyé", "expires_in": 300}
    if auth_bp._got_registered_once and (__import__("flask").current_app.debug or __import__("flask").current_app.testing):
        response["dev_code"] = code
    return jsonify(response), 201


@auth_bp.post("/verify-otp")
def verify():
    body = request.get_json(silent=True) or {}
    telephone = normalize_phone(body.get("telephone"))
    if not verify_otp(telephone, str(body.get("code", ""))):
        return jsonify(error="Code invalide ou expiré"), 401
    user = User.query.filter_by(telephone=telephone).first()
    is_new = user is None
    if is_new:
        from flask import current_app
        user = User(telephone=telephone, is_admin=telephone == current_app.config["ADMIN_TELEPHONE"])
        db.session.add(user)
        db.session.commit()
    return jsonify(token=create_token(user), user=user.to_dict(), nouveau_profil=is_new)


@auth_bp.route("/profile", methods=["GET", "PATCH"])
@token_required
def profile():
    from flask import g
    if request.method == "GET":
        return jsonify(g.user.to_dict())
    body = request.get_json(silent=True) or {}
    pseudo = str(body.get("pseudo", "")).strip()
    quartier = str(body.get("quartier_defaut", "")).strip()
    if not 2 <= len(pseudo) <= 50 or not 2 <= len(quartier) <= 100:
        return jsonify(error="Pseudo et quartier invalides"), 400
    g.user.pseudo = pseudo
    g.user.quartier_defaut = quartier
    db.session.commit()
    return jsonify(g.user.to_dict())
