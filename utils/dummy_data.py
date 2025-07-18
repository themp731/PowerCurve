# Adding data to the database.
import os
import sys
# Add the other folders to the route path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models import db, User, PowerCurve
from random import randint, uniform
from flask import Flask

def create_dummy_data(app):
    with app.app_context():
        # Creating 3 dummy users
        dummy_users = [
            {"strava_id": "1001", "access_token": "token1", "user_name": "Alice Example"},
            {"strava_id": "1002", "access_token": "token2", "user_name": "Bob Example"},
            {"strava_id": "1003", "access_token": "token3", "user_name": "Charlie Example"},
        ]

    # Add the user info into the different curves
        for user_info in dummy_users:
            user = User.query.filter_by(strava_id=user_info["strava_id"]).first()
            if not user:
                user = User(**user_info)
                db.session.add(user)
                db.session.commit()
                print(f"Added user {user.user_name} with Strava ID {user.strava_id}")
        
            # Create a Power Curve for each user
            curve = {str(t): round(uniform(100, 400), 2) for t in range(1, 3601)}
            power_curve = PowerCurve(
                user_id=user.id,
                user_name=user.user_name,
                activity_id=f"dummy_activity_{randint(1, 10000)}",
                curve=curve
            )
            db.session.add(power_curve)
            print(f"Added PowerCurve for user {user.user_name}")
    db.session.commit()
    