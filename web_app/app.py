from flask import Flask
#from flask_sqlalchemy import SQLAlchemy
from blueprints.user import user_bp
from blueprints.books import books_bp
from blueprints.main import main_bp 
from blueprints.auth import auth_bp

#db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
#    app.secret_key = "52772"
#    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
#    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

#    db.init_app(app)

    app.register_blueprint(main_bp)
    app.register_blueprint(user_bp, url_prefix="/user")
    app.register_blueprint(books_bp, url_prefix="/books")
    app.register_blueprint(auth_bp, url_prefix="/auth")
    
#    with app.app_context():
#        db.create_all()
    
    
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)