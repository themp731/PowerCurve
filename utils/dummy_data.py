# Adding data to the database.
import os
import sys
# Add the other folders to the route path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models import db, User, PowerCurve  # Ensure User model includes username field
from random import randint, uniform
from flask import Flask

def create_dummy_data(app):
    with app.app_context():
        # Creating 3 dummy users with user_name field (make sure User model supports user_name)
        dummy_users = [
            {"strava_id": "1001", "access_token": "token1", "username": "Alice Example", "password_hash": "dummyhash"},
            {"strava_id": "1002", "access_token": "token2", "username": "Bob Example", "password_hash": "dummyhash"},
            {"strava_id": "1003", "access_token": "token3", "username": "Charlie Example", "password_hash": "dummyhash"},
        ]

    # Add the user info into the different curves
        for user_info in dummy_users:
            user = User.query.filter_by(strava_id=user_info["strava_id"]).first()
            if not user:
                user = User(**user_info)
                db.session.add(user)
                db.session.commit()
                print(f"Added user {user.username} with Strava ID {user.strava_id}")
        
            # Create a Power Curve for each user
            curve = {str(t): round(uniform(100, 400), 2) for t in range(1, 3601)}
            power_curve = PowerCurve(
                user_id=user.id,
                username=user.username,
                activity_id=f"dummy_activity_{randint(1, 10000)}",
                curve=curve
            )
            db.session.add(power_curve)
            print(f"Added PowerCurve for user {user.username}")
    db.session.commit()
    