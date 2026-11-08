from flask import Blueprint, render_template

main_bp = Blueprint('main', __name__)

@main_bp.route("/", methods=["GET"])
def home_publica():
    return render_template("home_publica.html")
