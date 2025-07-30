# Adding data to the database.
import os
import sys
# Add the other folders to the route path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models import db, User, PowerCurve  # Ensure User model includes username field
from random import randint, uniform
from flask import Flask
from utils.pretty_print import print_db_state

def create_dummy_data(app):
    with app.app_context():
        # Creating 3 dummy users with user_name field (make sure User model supports user_name)
        dummy_users = [
            {"strava_id": "1001", "access_token": "token1", "strava_name": "Alice Example"},
            {"strava_id": "1002", "access_token": "token2", "strava_name": "Bob Example"},
            {"strava_id": "1003", "access_token": "token3", "strava_name": "Charlie Example"},
        ]

    # Add the user info into the different curves
        for user_info in dummy_users:
            user = User.query.filter_by(strava_id=user_info["strava_id"]).first()
            if not user:
                user = User(**user_info)
                db.session.add(user)
                db.session.commit()
                print(f"Added user {user.strava_name} with Strava ID {user.strava_id}")
        
            # Create a Power Curve for each user
            durations = [5, 10, 20, 30, 60, 120, 180, 300, 600, 900, 1200, 1800, 3600]
            max_power = round(uniform(100, 1000), 2)
            curve = {}
            prev_power = max_power
            for duration in durations:
                # For the first duration, use max_power; for others, decrease by a random amount
                if duration == durations[0]:
                    power = prev_power
                else:
                    # Decrease by a random value between 5 and 20, but not below 100
                    decrease = round(uniform(5, 20), 2)
                    power = max(100, prev_power - decrease)
                curve[str(duration)] = power
                prev_power = power
            power_curve = PowerCurve(
                user_id=user.id,
                strava_id=user.strava_id,
                activity_id=f"dummy_activity_{randint(1, 10000)}",
                curve=curve
            )
            db.session.add(power_curve)
            print(f"Added PowerCurve for user {user.strava_name}")
    db.session.commit()
    print_db_state(db, User, PowerCurve, label="User State after Dummy Data added")