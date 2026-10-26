from datetime import datetime, timedelta, timezone

from flask import Blueprint, g, jsonify, request
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import Alert, Confirmation
from ..services.auth import token_required
from ..services.images import save_compressed_image
from .meta import CATEGORIES

alerts_bp = Blueprint("alerts", __name__)
VALID_CATEGORIES = {item["id"] for item in CATEGORIES}


def refresh_statuses():
    now = datetime.now(timezone.utc)
    active_limit = now - timedelta(hours=48)
    resolved_limit = now - timedelta(hours=24)
    alerts = Alert.query.filter(Alert.statut.in_(["actif", "resolu"])).all()
    changed = False
    for alert in alerts:
        published = alert.date_publication.replace(tzinfo=timezone.utc) if alert.date_publication.tzinfo is None else alert.date_publication
        resolved = alert.date_resolution
        if resolved and resolved.tzinfo is None:
            resolved = resolved.replace(tzinfo=timezone.utc)
        if (alert.statut == "actif" and published < active_limit) or (alert.statut == "resolu" and resolved and resolved < resolved_limit):
            alert.statut = "expire"
            changed = True
    if changed:
        db.session.commit()


@alerts_bp.get("")
@token_required
def list_alerts():
    refresh_statuses()
    scope = request.args.get("scope", "quartier")
    category = request.args.get("categorie")
    include_resolved = request.args.get("inclure_resolues") == "true"
    query = Alert.query
    if scope == "mine":
        query = query.filter_by(user_id=g.user.id)
    else:
        if not include_resolved:
            query = query.filter_by(statut="actif")
        else:
            query = query.filter(Alert.statut.in_(["actif", "resolu"]))
        query = query.filter(~Alert.statut_traitement.in_(["traite", "rejete"]))
    if scope == "quartier":
        quartier = request.args.get("quartier") or g.user.quartier_defaut
        if quartier:
            query = query.filter_by(quartier=quartier)
    elif scope not in {"global", "mine"}:
        return jsonify(error="Scope invalide"), 400
    if category:
        if category not in VALID_CATEGORIES:
            return jsonify(error="Catégorie invalide"), 400
        query = query.filter_by(categorie=category)
    alerts = query.order_by(Alert.date_modification.desc(), Alert.date_publication.desc()).limit(100).all()
    return jsonify(items=[alert.to_dict(g.user.id) for alert in alerts])


@alerts_bp.post("")
@token_required
def create_alert():
    data = request.form if request.content_type and request.content_type.startswith("multipart/form-data") else (request.get_json(silent=True) or {})
    categorie = str(data.get("categorie", "")).strip().lower()
    quartier = str(data.get("quartier", "")).strip()
    description = str(data.get("description", "")).strip()
    if categorie not in VALID_CATEGORIES:
        return jsonify(error="Catégorie invalide"), 400
    if not 2 <= len(quartier) <= 100:
        return jsonify(error="Quartier invalide"), 400
    if not 1 <= len(description) <= 280:
        return jsonify(error="La description doit contenir entre 1 et 280 caractères"), 400
    photo_url = None
    photo = request.files.get("photo")
    if photo and photo.filename:
        try:
            photo_url = f"/api/uploads/{save_compressed_image(photo)}"
        except ValueError as exc:
            return jsonify(error=str(exc)), 400
    whatsapp_raw = data.get("option_whatsapp", False)
    option_whatsapp = whatsapp_raw is True or str(whatsapp_raw).lower() in {"true", "1", "on"}
    latitude = data.get("latitude")
    longitude = data.get("longitude")
    try:
        latitude = float(latitude) if latitude not in (None, "") else None
        longitude = float(longitude) if longitude not in (None, "") else None
    except (TypeError, ValueError):
        return jsonify(error="Coordonnées géographiques invalides"), 400
    if (latitude is None) != (longitude is None):
        return jsonify(error="Latitude et longitude doivent être fournies ensemble"), 400
    if latitude is not None and not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return jsonify(error="Coordonnées géographiques hors limites"), 400
    if latitude is not None and str(data.get("country_code", "")).lower() != "sn":
        return jsonify(error="La position doit être validée comme étant au Sénégal"), 422
    alert = Alert(user_id=g.user.id, categorie=categorie, quartier=quartier,
                  description=description, photo_url=photo_url, option_whatsapp=option_whatsapp,
                  latitude=latitude, longitude=longitude,
                  commune=str(data.get("commune", "")).strip()[:120] or None,
                  region=str(data.get("region", "")).strip()[:120] or None)
    db.session.add(alert)
    db.session.commit()
    return jsonify(alert.to_dict(g.user.id)), 201


@alerts_bp.post("/<int:alert_id>/confirm")
@token_required
def confirm(alert_id):
    alert = db.get_or_404(Alert, alert_id)
    if alert.statut != "actif":
        return jsonify(error="Cette alerte n'est plus active"), 409
    db.session.add(Confirmation(alert_id=alert.id, user_id=g.user.id))
    try:
        alert.compteur_confirmations += 1
        alert.date_modification = datetime.now(timezone.utc)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(error="Alerte déjà confirmée"), 409
    return jsonify(alert.to_dict(g.user.id))


@alerts_bp.post("/<int:alert_id>/resolve")
@token_required
def resolve(alert_id):
    alert = db.get_or_404(Alert, alert_id)
    if alert.user_id != g.user.id:
        return jsonify(error="Seul l'auteur peut résoudre cette alerte"), 403
    if alert.statut != "actif":
        return jsonify(error="Cette alerte n'est plus active"), 409
    alert.statut = "resolu"
    alert.date_resolution = datetime.now(timezone.utc)
    alert.date_modification = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify(alert.to_dict(g.user.id))
