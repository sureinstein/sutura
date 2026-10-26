from pathlib import Path

from flask import Flask, jsonify, render_template
from sqlalchemy import inspect, text

from .config import Config
from .extensions import db


def create_app(config_object=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    if config_object:
        app.config.from_mapping(config_object)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    db.init_app(app)

    from .api.alerts import alerts_bp
    from .api.auth import auth_bp
    from .api.meta import meta_bp
    from .api.admin import admin_bp
    from .api.geo import geo_bp
    from .api.work import work_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(alerts_bp, url_prefix="/api/alerts")
    app.register_blueprint(meta_bp, url_prefix="/api")
    app.register_blueprint(geo_bp, url_prefix="/api/geo")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(work_bp, url_prefix="/api/work")

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/admin")
    def admin():
        return render_template("admin.html")

    @app.get("/traitement")
    def work():
        return render_template("work.html")

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.errorhandler(413)
    def too_large(_error):
        return jsonify(error="Fichier trop volumineux"), 413

    with app.app_context():
        db.create_all()
        # Migration légère du prototype SQLite existant. En production : Alembic.
        columns = {column["name"] for column in inspect(db.engine).get_columns("alert")}
        alert_additions = {"latitude": "FLOAT", "longitude": "FLOAT", "commune": "VARCHAR(120)", "region": "VARCHAR(120)", "priorite": "VARCHAR(20) DEFAULT 'normale' NOT NULL", "statut_traitement": "VARCHAR(30) DEFAULT 'nouveau' NOT NULL", "group_id": "INTEGER", "date_modification": "DATETIME"}
        for name, definition in alert_additions.items():
            if name not in columns:
                db.session.execute(text(f"ALTER TABLE alert ADD COLUMN {name} {definition}"))
        db.session.execute(text("UPDATE alert SET date_modification = date_publication WHERE date_modification IS NULL"))
        user_columns = {column["name"] for column in inspect(db.engine).get_columns("user")}
        if "is_admin" not in user_columns:
            db.session.execute(text("ALTER TABLE user ADD COLUMN is_admin BOOLEAN DEFAULT 0 NOT NULL"))
        db.session.execute(text("UPDATE user SET is_admin = 1 WHERE telephone = :telephone"), {"telephone": app.config["ADMIN_TELEPHONE"]})
        db.session.commit()

    return app
