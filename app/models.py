from datetime import datetime, timezone

from .extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    telephone = db.Column(db.String(13), unique=True, nullable=False, index=True)
    pseudo = db.Column(db.String(50), nullable=True)
    quartier_defaut = db.Column(db.String(100), nullable=True)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    date_creation = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    alerts = db.relationship("Alert", back_populates="author", lazy=True)
    memberships = db.relationship("GroupMember", back_populates="user", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "telephone": self.telephone,
            "pseudo": self.pseudo,
            "quartier_defaut": self.quartier_defaut,
            "is_admin": self.is_admin,
            "groupes": [membership.to_dict(include_user=False) for membership in self.memberships],
            "date_creation": self.date_creation.isoformat(),
        }


class OtpCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    telephone = db.Column(db.String(13), nullable=False, index=True)
    code_hash = db.Column(db.String(128), nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    consumed = db.Column(db.Boolean, default=False, nullable=False)


class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    categorie = db.Column(db.String(30), nullable=False, index=True)
    quartier = db.Column(db.String(100), nullable=False, index=True)
    description = db.Column(db.String(280), nullable=False)
    photo_url = db.Column(db.String(255), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    commune = db.Column(db.String(120), nullable=True)
    region = db.Column(db.String(120), nullable=True)
    option_whatsapp = db.Column(db.Boolean, default=False, nullable=False)
    statut = db.Column(db.String(20), default="actif", nullable=False, index=True)
    compteur_confirmations = db.Column(db.Integer, default=0, nullable=False)
    date_publication = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    date_modification = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    date_resolution = db.Column(db.DateTime(timezone=True), nullable=True)
    priorite = db.Column(db.String(20), default="normale", nullable=False)
    statut_traitement = db.Column(db.String(30), default="nouveau", nullable=False)
    group_id = db.Column(db.Integer, db.ForeignKey("group.id"), nullable=True)
    author = db.relationship("User", back_populates="alerts")
    confirmations = db.relationship("Confirmation", cascade="all, delete-orphan")

    def to_dict(self, viewer_id=None, include_contact=False):
        return {
            "id": self.id,
            "auteur": {"id": self.author.id, "pseudo": self.author.pseudo or "Voisin"},
            "categorie": self.categorie,
            "quartier": self.quartier,
            "description": self.description,
            "photo_url": self.photo_url,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "commune": self.commune,
            "region": self.region,
            "option_whatsapp": self.option_whatsapp,
            "whatsapp": self.author.telephone if include_contact and self.option_whatsapp else None,
            "statut": self.statut,
            "compteur_confirmations": self.compteur_confirmations,
            "confirmee_par_moi": any(c.user_id == viewer_id for c in self.confirmations),
            "date_publication": self.date_publication.isoformat(),
            "date_modification": self.date_modification.isoformat(),
            "date_resolution": self.date_resolution.isoformat() if self.date_resolution else None,
            "priorite": self.priorite,
            "statut_traitement": self.statut_traitement,
            "groupe": self.group.to_dict() if self.group else None,
        }


class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(280), nullable=True)
    actif = db.Column(db.Boolean, default=True, nullable=False)
    date_creation = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    alerts = db.relationship("Alert", backref="group", lazy=True)
    memberships = db.relationship("GroupMember", back_populates="group", cascade="all, delete-orphan")

    def to_dict(self, include_members=False):
        data = {"id": self.id, "nom": self.nom, "description": self.description, "actif": self.actif}
        if include_members:
            data["membres"] = [membership.to_dict() for membership in self.memberships]
        return data


class GroupMember(db.Model):
    __table_args__ = (db.UniqueConstraint("group_id", "user_id"),)
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey("group.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    is_lead = db.Column(db.Boolean, default=False, nullable=False)
    date_creation = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    group = db.relationship("Group", back_populates="memberships")
    user = db.relationship("User", back_populates="memberships")

    def to_dict(self, include_user=True):
        data = {"id": self.id, "group_id": self.group_id, "groupe": self.group.nom, "is_lead": self.is_lead}
        if include_user:
            data["utilisateur"] = {"id": self.user.id, "pseudo": self.user.pseudo, "telephone": self.user.telephone}
        return data


class Confirmation(db.Model):
    __table_args__ = (db.UniqueConstraint("alert_id", "user_id"),)
    id = db.Column(db.Integer, primary_key=True)
    alert_id = db.Column(db.Integer, db.ForeignKey("alert.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    date_creation = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
