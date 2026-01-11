from flask import Blueprint, render_template

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/")
def auth():
    return render_template("/welcome.html")

@auth_bp.route("/login")
def login():
    return render_template("/login.html")

@auth_bp.route("/register/step1")
def register_st1():
    return render_template("auth/register_step1.html")

@auth_bp.route("/register/step2")
def register_st2():
    return render_template("auth/register_step2.html")

@auth_bp.route("/register/step3")
def register_st3():
    return render_template("auth/register_step3.html")

@auth_bp.route("/personalization/step1")
def personalization_st1():
    return render_template("auth/personalization_step1.html")

@auth_bp.route("/personalization/step2")
def personalization_st2():
    return render_template("auth/personalization_step2.html")

@auth_bp.route("/personalization/step3")
def personalization_st3():
    return render_template("auth/personalization_step3.html")

@auth_bp.route("/success")
def success():
    return render_template("auth/success.html")