from flask import Blueprint, jsonify

main_bp = Blueprint("main",__name__)

@main_bp.route("/")
def home():
    return jsonify({
        "message": "Sales Management API is running"
    })


@main_bp.route("/api/health")
def health_check():
        return jsonify({
            "status": "success",
            "message": "Backend is running"
        })