from flask import Blueprint, jsonify, send_from_directory, current_app

meta_bp = Blueprint("meta", __name__)

CATEGORIES = [
    {"id": "eau", "label": "Eau", "icone": "💧"},
    {"id": "senelec", "label": "Senelec", "icone": "⚡"},
    {"id": "papiers", "label": "Papiers & objets perdus", "icone": "🆔"},
    {"id": "inondation", "label": "Inondation & route", "icone": "🌧️"},
    {"id": "autre", "label": "Sécurité / Divers", "icone": "⚠️"},
]

QUARTIERS = [
    "Mermoz", "Ouakam", "Yoff", "HLM Grand Yoff", "Parcelles Assainies Unité 15",
    "Médina", "Plateau", "Sicap Liberté", "Guédiawaye", "Pikine", "Rufisque Est"
]


@meta_bp.get("/metadata")
def metadata():
    return jsonify(categories=CATEGORIES, quartiers=QUARTIERS)


@meta_bp.get("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)

