from flask import Blueprint, render_template

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
def home():
    return render_template("public/index.html")

@main_bp.route("/books/most_added")
def most_added():
    return render_template("books/most_added.html")

@main_bp.route("/books/trending")
def trending():
    return render_template("books/trending.html")

@main_bp.route("/genres/<genre_name>")
def genres(genre_name):
    return render_template("books/genres.html", genre=genre_name)

@main_bp.route("/books/explore")
def searching():
    return render_template("books/explore.html")

@main_bp.route("/welcome")
def auth():
    return render_template("auth/welcome.html")