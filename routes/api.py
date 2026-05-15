from flask       import Blueprint, jsonify, request
from flask_login import login_required
from services.rail_api import get_station_suggestions

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/stations")
@login_required
def stations():
    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return jsonify([])
    results = get_station_suggestions(q)
    return jsonify(results)
