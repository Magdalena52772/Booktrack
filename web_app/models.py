class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200))
    username = db.Column(db.String(50))
    books = db.relationship('UserBook', back_populates='user')
    
class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(100), unique=True, nullable=False)
    title = db.Column(db.String(300))
    authors = db.Column(db.String(300))
    thumbnail = db.Column(db.String(500))
    description = db.Column(db.Text)
    published_date = db.Column(db.String(20))
    categories = db.Column(db.String(200))
    
    users = db.relationship('UserBook', back_populates='book')
    