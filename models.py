# File for handling the SQLite database
from flask_sqlalchemy import SQLAlchemy

# Create a SLQAlchemy instance
db = SQLAlchemy()

# User model for storing user information
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    strava_id = db.Column(db.String(50), unique=True, nullable=False)
    access_token = db.Column(db.String, nullable=False)

# Model for storing PowerCurve data
class PowerCurve(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    activity_id = db.Column(db.String(50), nullable=False)
    curve = db.Column(db.JSON, nullable=False)  
    created_at = db.Column(db.DateTime, server_default=db.func.now())