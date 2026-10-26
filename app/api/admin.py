from flask import Blueprint, g, jsonify, request
from datetime import datetime, timedelta, timezone
from sqlalchemy import or_, case

from ..extensions import db
from ..models import Alert, Group, GroupMember, User
from ..services.auth import admin_required

admin_bp = Blueprint("admin_api", __name__)
PRIORITIES = {"basse", "normale", "haute", "critique"}
WORKFLOW = {"nouveau", "qualifie", "assigne", "en_cours", "traite", "rejete"}


@admin_bp.get("/dashboard")
@admin_required
def dashboard():
    query = Alert.query
    quartier = request.args.get("quartier", "").strip()
    priorite = request.args.get("priorite", "").strip()
    statut = request.args.get("statut_traitement", "").strip()
    group_id = request.args.get("group_id", type=int)
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()
    sort = request.args.get("sort", "modified_desc")
    if quartier:
        term = f"%{quartier}%"
        query = query.filter(or_(Alert.quartier.ilike(term), Alert.commune.ilike(term), Alert.region.ilike(term)))
    if priorite:
        query = query.filter_by(priorite=priorite)
    if statut:
        query = query.filter_by(statut_traitement=statut)
    if group_id:
        query = query.filter_by(group_id=group_id)
    try:
        if date_from:
            query = query.filter(Alert.date_publication >= datetime.fromisoformat(date_from).replace(tzinfo=timezone.utc))
        if date_to:
            query = query.filter(Alert.date_publication < datetime.fromisoformat(date_to).replace(tzinfo=timezone.utc) + timedelta(days=1))
    except ValueError:
        return jsonify(error="Période de dates invalide"), 400
    priority_rank = case((Alert.priorite == "critique", 4), (Alert.priorite == "haute", 3), (Alert.priorite == "normale", 2), else_=1)
    orders = {
        "modified_desc": (Alert.date_modification.desc(),),
        "modified_asc": (Alert.date_modification.asc(),),
        "published_desc": (Alert.date_publication.desc(),),
        "published_asc": (Alert.date_publication.asc(),),
        "priority_desc": (priority_rank.desc(), Alert.date_modification.desc()),
    }
    if sort not in orders:
        return jsonify(error="Mode de tri invalide"), 400
    items = query.order_by(*orders[sort]).limit(500).all()
    quartiers = [row[0] for row in db.session.query(Alert.quartier).distinct().order_by(Alert.quartier).all()]
    return jsonify(items=[a.to_dict(g.user.id, include_contact=True) for a in items], quartiers=quartiers,
                   stats={"total": Alert.query.count(), "nouveau": Alert.query.filter_by(statut_traitement="nouveau").count(), "critique": Alert.query.filter_by(priorite="critique").count(), "traite": Alert.query.filter_by(statut_traitement="traite").count()})


@admin_bp.patch("/alerts/<int:alert_id>")
@admin_required
def update_alert(alert_id):
    alert = db.get_or_404(Alert, alert_id)
    body = request.get_json(silent=True) or {}
    if "priorite" in body:
        if body["priorite"] not in PRIORITIES:
            return jsonify(error="Priorité invalide"), 400
        alert.priorite = body["priorite"]
    if "statut_traitement" in body:
        if body["statut_traitement"] not in WORKFLOW:
            return jsonify(error="Statut de traitement invalide"), 400
        alert.statut_traitement = body["statut_traitement"]
    if "group_id" in body:
        group_id = body["group_id"]
        if group_id is not None and not db.session.get(Group, int(group_id)):
            return jsonify(error="Groupe inconnu"), 400
        alert.group_id = group_id
        if group_id and alert.statut_traitement == "nouveau":
            alert.statut_traitement = "assigne"
    alert.date_modification = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify(alert.to_dict(g.user.id, include_contact=True))


@admin_bp.route("/groups", methods=["GET", "POST"])
@admin_required
def groups():
    if request.method == "GET":
        return jsonify(items=[group.to_dict(include_members=True) for group in Group.query.order_by(Group.nom).all()])
    body = request.get_json(silent=True) or {}
    nom = str(body.get("nom", "")).strip()
    if not 2 <= len(nom) <= 100:
        return jsonify(error="Nom de groupe invalide"), 400
    if Group.query.filter(db.func.lower(Group.nom) == nom.lower()).first():
        return jsonify(error="Ce groupe existe déjà"), 409
    group = Group(nom=nom, description=str(body.get("description", "")).strip()[:280])
    db.session.add(group); db.session.commit()
    return jsonify(group.to_dict()), 201


@admin_bp.route("/groups/<int:group_id>", methods=["PATCH", "DELETE"])
@admin_required
def group_detail(group_id):
    group = db.get_or_404(Group, group_id)
    if request.method == "DELETE":
        group.actif = False
    else:
        body = request.get_json(silent=True) or {}
        if "nom" in body and 2 <= len(str(body["nom"]).strip()) <= 100:
            group.nom = str(body["nom"]).strip()
        if "description" in body:
            group.description = str(body["description"]).strip()[:280]
        if "actif" in body:
            group.actif = bool(body["actif"])
    db.session.commit()
    return jsonify(group.to_dict())


@admin_bp.get("/users")
@admin_required
def users():
    search = request.args.get("q", "").strip()
    query = User.query
    if search:
        term = f"%{search}%"
        query = query.filter(or_(User.pseudo.ilike(term), User.telephone.ilike(term)))
    return jsonify(items=[user.to_dict() for user in query.order_by(User.date_creation.desc()).limit(300).all()])


@admin_bp.post("/groups/<int:group_id>/members")
@admin_required
def add_group_member(group_id):
    group = db.get_or_404(Group, group_id)
    body = request.get_json(silent=True) or {}
    user = db.session.get(User, body.get("user_id"))
    if not user:
        return jsonify(error="Utilisateur inconnu"), 400
    membership = GroupMember.query.filter_by(group_id=group.id, user_id=user.id).first()
    if not membership:
        membership = GroupMember(group_id=group.id, user_id=user.id)
        db.session.add(membership)
    if bool(body.get("is_lead")):
        GroupMember.query.filter_by(group_id=group.id, is_lead=True).update({"is_lead": False})
        membership.is_lead = True
    db.session.commit()
    return jsonify(membership.to_dict()), 201


@admin_bp.patch("/groups/<int:group_id>/members/<int:user_id>")
@admin_required
def update_group_member(group_id, user_id):
    membership = GroupMember.query.filter_by(group_id=group_id, user_id=user_id).first_or_404()
    body = request.get_json(silent=True) or {}
    if "is_lead" in body:
        if bool(body["is_lead"]):
            GroupMember.query.filter_by(group_id=group_id, is_lead=True).update({"is_lead": False})
        membership.is_lead = bool(body["is_lead"])
    db.session.commit()
    return jsonify(membership.to_dict())


@admin_bp.delete("/groups/<int:group_id>/members/<int:user_id>")
@admin_required
def remove_group_member(group_id, user_id):
    membership = GroupMember.query.filter_by(group_id=group_id, user_id=user_id).first_or_404()
    db.session.delete(membership); db.session.commit()
    return "", 204
