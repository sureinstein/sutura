from flask import Blueprint, g, jsonify, request
from datetime import datetime, timezone

from ..extensions import db
from ..models import Alert, GroupMember
from ..services.auth import token_required
from .admin import WORKFLOW

work_bp = Blueprint("work", __name__)


def member_group_ids():
    return [row[0] for row in db.session.query(GroupMember.group_id).filter_by(user_id=g.user.id).all()]


@work_bp.get("/alerts")
@token_required
def assigned_alerts():
    group_ids = member_group_ids()
    if not group_ids:
        return jsonify(items=[], groupes=[])
    query = Alert.query.filter(Alert.group_id.in_(group_ids))
    statut = request.args.get("statut_traitement")
    if statut:
        query = query.filter_by(statut_traitement=statut)
    memberships = GroupMember.query.filter_by(user_id=g.user.id).all()
    return jsonify(items=[alert.to_dict(g.user.id, include_contact=True) for alert in query.order_by(Alert.date_modification.desc(), Alert.date_publication.desc()).all()], groupes=[m.to_dict(include_user=False) for m in memberships])


@work_bp.patch("/alerts/<int:alert_id>")
@token_required
def update_assigned_alert(alert_id):
    alert = db.get_or_404(Alert, alert_id)
    membership = GroupMember.query.filter_by(user_id=g.user.id, group_id=alert.group_id).first()
    if not membership:
        return jsonify(error="Cette alerte n'est pas affectée à votre groupe"), 403
    body = request.get_json(silent=True) or {}
    statut = body.get("statut_traitement")
    if statut not in WORKFLOW - {"nouveau", "rejete"}:
        return jsonify(error="Statut de traitement invalide"), 400
    alert.statut_traitement = statut
    alert.date_modification = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify(alert.to_dict(g.user.id, include_contact=True))
