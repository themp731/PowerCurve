# File for handling the SQLite database
import os
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from flask import Flask

# Create a SLQAlchemy instance
db = SQLAlchemy()

# User model for storing user information
class User(db.Model, UserMixin):
    """
    Represents a user in the application, mapped to the 'user' table in the database.

    Attributes:
        id (int): Primary key for the user table.
        strava_id (str): Unique Strava user ID.
        access_token (str): OAuth access token for Strava API.
        strava_name (str): Display name from Strava.

    Notes:
        Inherits from db.Model to integrate with SQLAlchemy ORM.
        Inherits from UserMixin to provide default implementations for Flask-Login user methods
        such as is_authenticated, is_active, is_anonymous, and get_id. This is required for
        user session management and authentication in Flask applications.

        UserMixin is typically imported from flask_login and is referenced in other files
        (such as your authentication or login manager setup) to identify the current user,
        manage login sessions, and restrict access to authenticated users.
    """
    __tablename__ = 'user'  # Explicit table name for clarity and compatibility
    id = db.Column(db.Integer, primary_key=True)  # Primary key for the user table
    strava_id = db.Column(db.String(50), unique=True, nullable=False)  # Strava user ID (from Strava)
    access_token = db.Column(db.String, nullable=False)  # OAuth access token for Strava API
    strava_name = db.Column(db.String(100))  # Display name from Strava (easy to read)

# Model for storing PowerCurve data
class PowerCurve(db.Model):
    __tablename__ = 'power_curve'  # Explicit table name for clarity and compatibility
    id = db.Column(db.Integer, primary_key=True)  # Primary key for the power curve table
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Reference to User table
    strava_id = db.Column(db.String(80), nullable=False)  # Strava user ID (from Strava)
    activity_id = db.Column(db.String(50), nullable=False)  # Strava activity ID
    curve = db.Column(db.JSON, nullable=False)  # Power curve data stored as JSON
    created_at = db.Column(db.DateTime, server_default=db.func.now())  # Timestamp when record was created