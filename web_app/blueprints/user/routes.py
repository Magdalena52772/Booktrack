from flask import Blueprint, render_template, redirect, url_for, session

user_bp = Blueprint("user", __name__)

@user_bp.route("/dashboard")
def dashboard():
    stats = {"total_hours": "12h", "books_read": 7}
    return render_template("user/user_dashboard.html", stats=stats)

@user_bp.route("/reading_list")
def reading_list():
    books = ["Duna", "Wiedźmin", "Harry Potter"]
    return render_template("user/reading_list.html", books=books)

@user_bp.route("/favourite_books")
def favourite_books():
    favs = ["Duna", "Imię róży"]
    return render_template("user/favourite_books.html", favs=favs)

@user_bp.route("/lists")
def lists():
    lists = ["Moje 10", "Do przeczytania 2025"]
    return render_template("user/lists.html", lists=lists)

@user_bp.route("/stats")
def stats():
    stats = {"total_hours": "12h", "books_read": 7}
    return render_template("user/stats.html", stats=stats)

@user_bp.route("/recommendations")
def recommendations():
    recs = ["Książka A", "Książka B"]
    return render_template("user/recommendations.html", recs=recs)

@user_bp.route("/profile")
def profile():
    return render_template("user/profile.html")

@user_bp.route("/logout")
def logout():
    #session.clear()
    return redirect(url_for("main.home"))