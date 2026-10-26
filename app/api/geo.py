from flask import Blueprint, current_app, jsonify, request
import requests

geo_bp = Blueprint("geo", __name__)


def nominatim(path, params):
    url = f"{current_app.config['NOMINATIM_URL']}/{path}"
    try:
        response = requests.get(url, params=params, timeout=8, headers={"User-Agent": "Sutura-MVP/1.0 (contact: admin@sutura.sn)", "Accept-Language": "fr"})
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError):
        return None


def locality(address):
    return next((address.get(key) for key in ("quarter", "suburb", "neighbourhood", "village", "town", "city_district", "city", "municipality") if address.get(key)), None)


@geo_bp.get("/reverse")
def reverse():
    try:
        lat, lon = float(request.args["lat"]), float(request.args["lon"])
    except (KeyError, TypeError, ValueError):
        return jsonify(error="Coordonnées invalides"), 400
    data = nominatim("reverse", {"format":"jsonv2", "lat":lat, "lon":lon, "zoom":18, "addressdetails":1})
    if not data:
        return jsonify(error="Service géographique temporairement indisponible"), 503
    address = data.get("address", {})
    if address.get("country_code", "").lower() != "sn":
        return jsonify(error="La position doit être située au Sénégal"), 422
    return jsonify(latitude=lat, longitude=lon, quartier=locality(address), commune=address.get("municipality") or address.get("city") or address.get("town"), region=address.get("state"), display_name=data.get("display_name"))


@geo_bp.get("/search")
def search():
    query = request.args.get("q", "").strip()
    if len(query) < 2:
        return jsonify(items=[])
    data = nominatim("search", {"format":"jsonv2", "q":query, "countrycodes":"sn", "addressdetails":1, "limit":12})
    if data is None:
        return jsonify(error="Service géographique temporairement indisponible"), 503
    items = []
    for place in data:
        address = place.get("address", {})
        if address.get("country_code", "").lower() == "sn":
            items.append({"label":place.get("display_name"), "quartier":locality(address), "commune":address.get("municipality") or address.get("city") or address.get("town"), "region":address.get("state"), "latitude":float(place["lat"]), "longitude":float(place["lon"])})
    return jsonify(items=items)
