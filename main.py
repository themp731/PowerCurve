# Entry Point for the flask application

from flask import Flask, redirect, request, session, render_template
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import os
import numpy as np
from dotenv import load_dotenv
import requests
import matplotlib.pyplot as plt
import io
import base64
# SQLAlchemy for database handling
from models import db, User, PowerCurve
from utils.dummy_data import create_dummy_data
from utils.pretty_print import pretty_print

# load environment variables from .env file
load_dotenv()


app = Flask(__name__)
app.secret_key = os.urandom(24)  # Secret key for session management
# Configure SQLAlchemy to link to Flask
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///powercurve.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# --- Automatic DB schema check and rebuild ---
# NOTE: This code is commented out due to a looping error. Needs fixing later.
# def check_and_rebuild_db():
#     from sqlalchemy.exc import OperationalError
#     import sys
#     try:
#         with app.app_context():
#             from sqlalchemy import text
#             # Check user table columns
#             db.session.execute(text("SELECT id, username, password_hash, strava_id, access_token, username FROM user LIMIT 1"))
#             # Check power_curve table columns
#             db.session.execute(text("SELECT id, user_id, username, activity_id, curve, created_at FROM power_curve LIMIT 1"))
#     except OperationalError:
#         print("Database schema mismatch detected. Rebuilding database...")
#         # We use subprocess here because rebuilding the database (deleting and recreating the file)
#         # while the Flask app is running can cause issues with open connections and cached models.
#         # Running the rebuild as a separate process ensures a clean rebuild and avoids side effects.
#         import subprocess
#         subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), 'utils', 'rebuild_db.py')])
#         print("Database rebuild complete.")
# check_and_rebuild_db()

# Create the database tables if they don't exist
if not os.path.exists('powercurve.db'):
    with app.app_context():
        db.create_all()

# Add dummy data if now information
with app.app_context():
    if PowerCurve.query.count() <= 2:
        create_dummy_data(app)
        
# Get Credentials from environment variables
STRAVA_CLIENT_ID = os.getenv('STRAVA_CLIENT_ID')
STRAVA_CLIENT_SECRET = os.getenv('STRAVA_CLIENT_SECRET')
STRAVA_REDIRECT_URI = os.getenv('STRAVA_REDIRECT_URI')

# Initialize the flask login management
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id)) 

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/")

@app.route("/home")
@login_required
def home():
    return render_template("home.html", user=current_user)

# Brings up the main page and asks if you have an account. 
@app.route("/")
def landing():
    # If user is logged in, redirect to /home. Otherwise, show landing page.
    if current_user.is_authenticated:
        return redirect("/home")
    return render_template("landing.html")

# Authorizing the Application to work with your strava
@app.route("/authorize")
def authorize():
    # Redirect to Strava's OAuth page
    auth_url = (
        f"https://www.strava.com/oauth/authorize"
        f"?client_id={STRAVA_CLIENT_ID}"
        f"&response_type=code"
        f"&redirect_uri={STRAVA_REDIRECT_URI}"
        f"&approval_prompt=force"
        f"&scope=read,activity:read"
    )
    return redirect(auth_url)

# Strava OAuth callback route
@app.route("/strava/callback")
def callback():
    # Get the authorization code returned by Strava after user approval
    code = request.args.get("code")
    
    # Exchange the authorization code for an access token
    token_response = requests.post(
        "https://www.strava.com/oauth/token",
        data={
            "client_id": STRAVA_CLIENT_ID,
            "client_secret": STRAVA_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
        }, verify=False # Added verify=False to avoid SSL issues during local testing
    )
    # Parse the response JSON to extract the access token and athlete info
    token_json = token_response.json()
    pretty_print(token_json)  # Debug: print the full JSON response
    access_token = token_json["access_token"]
    athlete = token_json["athlete"]
    strava_id = str(athlete["id"])
    strava_name = athlete.get("username", "")

    # Look up the user in the database by Strava ID
    user = User.query.filter_by(strava_id=strava_id).first()
    if not user:
        # If user does not exist, create a new user record
        user = User(strava_id=strava_id, access_token=access_token, strava_name=strava_name)
        db.session.add(user)
    else:
        # If user exists, update their access token and Strava username
        user.access_token = access_token
        user.strava_name = strava_name
    db.session.commit()
    
    # Log the user in using Flask-Login
    session['strava_id'] = strava_id  # <-- Changed from 'athlete_id' to 'strava_id'
    login_user(user)
    # Redirect to the home page after successful login
    return redirect("/home")


# Grabbing data from specific activities to start
@app.route("/activities")
def activities():
    # Get the access token from session
    access_token = session.get('access_token')
    if not access_token:
        return redirect('/authorize')

    # Headers to send for your request
    headers = {"Authorization": f"Bearer {access_token}"}

    # Get the most recent 5 activities
    activities_response = requests.get("https://www.strava.com/api/v3/athlete/activities",
                                       headers=headers,
                                       params={"per_page":10},
                                       verify=False)

    if activities_response.status_code != 200:
        return "Failed to fetch activities from Strava.", 500

    # Filter to the activities that are bike rides
    data = activities_response.json()
    html = "<h1>Your Recent Cycling Activities</h1><ul>"
    count = 0
    for activity in data:
        if activity.get("type") == 'Ride':
            name = activity.get("name")
            distance_km = activity.get("distance", 0)/1000
            html += f"<li>{name} - {distance_km:.2f} km </li>"
            count += 1
            if count >= 5:
                break
    html += "</ul>"

    if count == 0:
        html = "<h1>No recent cycling activities found.</h1>"

    return html

# Generate Power Curve from last 5 rides
@app.route("/powercurve")
def powercurve():
    # Creating the HTML return text
    html = "<h1>You Power Curve From Your Last 5 Rides</h1>"
    
    # Get the access token from session and if not reauthorize
    access_token = session.get('access_token')
    if not access_token:
        return redirect('/authorize')
    
    headers = {"Authorization": f"Bearer {access_token}"}
    # Get last 10 activities and filter to the last 5 rides, return 500 if error
    activities_response = requests.get("https://www.strava.com/api/v3/athlete/activities",
                                       headers=headers,
                                       params={"per_page":20, "page":1},
                                       verify=False)
    if activities_response.status_code != 200:
        return "Failed to fetch activities from Strava.", 500

        
    # Set up durations for PowerCurve
    durations = [5, 10, 20, 30, 60, 120, 180, 300, 600, 900, 1200, 1800, 3600]  # in seconds
    powercurve = {duration: 0 for duration in durations}

    
    # Get the power stream and get a rolling average. 
    rides_with_power = []
    for ride in activities_response.json():
        # Skip if activity isn't a ride and doesn't have power data
        if ride.get("type") != 'Ride':
            continue
        
        # Send an API request to get the power stream from the ride ID
        ride_id = ride['id']
        stream_response = requests.get(f'https://www.strava.com/api/v3/activities/{ride_id}/streams',
                                       headers=headers,
                                       params={"keys":"watts", "key_by_type":True},
                                       verify=False)
        if stream_response.status_code != 200:
            continue # Skip if unable to fetch power data
        
        # Parse the JSON and save power data
        stream_data = stream_response.json()
        watts_data = stream_data.get('watts')
        watts_array = watts_data.get('data') if watts_data else None
        if not isinstance(watts_array, list) or not watts_array:
            continue
        rides_with_power.append((ride_id, watts_array))
        # Only take most recent 5 rides with power data
        if len(rides_with_power) >= 5:
            break

    # Indicate if no rides with power data found        
    if not rides_with_power:
        return "<h1>No rides with power data found.</h1>", 500
    
    # Go through each ride with power and create the power curve
    for ride_id, watts in rides_with_power:
        for duration in durations:
            if len(watts) >= duration:
            # Calculate rolling average for the duration
                cumulative_sum = np.cumsum(watts, dtype=float)
                cumulative_sum[duration:] = cumulative_sum[duration:] - cumulative_sum[:-duration]
                rolling_avg = max(cumulative_sum[duration - 1:] / duration)
                powercurve[duration] = round(max(powercurve[duration], rolling_avg),2)


    # Save PowerCurve to database
    strava_id = session.get('strava_id')  # <-- Changed from 'athlete_id'
    user = User.query.filter_by(strava_id=str(strava_id)).first()
    # Look up the user name based on athlete ID to save into PowerCurve DB
    strava_id = user.strava_id if user else "Unknown"
    if user: # Delete old powercurve entries for user
        PowerCurve.query.filter_by(user_id=user.id).delete()
        new_power_curve = PowerCurve(
            user_id=user.id,
            activity_id=str(rides_with_power[0][0]),
            curve=powercurve,
            strava_id=strava_id
        )
        db.session.add(new_power_curve)
        db.session.commit()
    else:
        return "<h1>User not found. Please authorize the application first.</h1>", 400

    # Create a Power Curve plot 
    fig, ax = plt.subplots()
    ax.plot(list(powercurve.keys()), list(powercurve.values()), marker='o')
    ax.set_xlabel('Duration (seconds)')
    ax.set_ylabel('Power (watts)')
    ax.set_title('Power Curve')

    # Convert the plot to a base64 image
    # This is because flask doesn't know how to save an image as a file
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8') # Read the PNG bytes and encode as base64
    plt.close(fig)
    html += f'<img src="data:image/png;base64,{img_base64}"/>'
    
    # Display HTML in the site
    return html

# Route to compare power curves between users
@app.route("/compare", methods=["GET", "POST"])
def compare():
    strava_id = session.get('strava_id')  # <-- Changed from 'athlete_id'
    current_user = User.query.filter_by(strava_id=str(strava_id)).first()
    if not current_user:
        html = "<h1>No user found. Please authorize first.</h1>"
        return html, 404
    
    # Get the list of users with at least one curve except current user
    users_with_curves = (
        db.session.query(User)
        .join(PowerCurve, User.id == PowerCurve.user_id)
        .filter(User.id != current_user.id)
        .distinct()
        .all()
    )

    # Now compare the different users with the different curves.
    other_user_id = request.form.get("compare_user")
    other_curve = None
    other_username = None
    if other_user_id:
        other_user = User.query.filter_by(id=int(other_user_id)).first()
        if other_user:
            # Get the latest power curve for the selected user
            other_power_curve = (
                PowerCurve.query.filter_by(user_id=other_user.id)
                .order_by(PowerCurve.created_at.desc())
                .first()
            )
            if other_power_curve:
                other_curve = other_power_curve.curve
                other_username = other_user.strava_id

    # Get the current user's curve
    current_user_curve = (
        PowerCurve.query.filter_by(user_id=current_user.id)
        .order_by(PowerCurve.created_at.desc())
        .first()
    )
    if not current_user_curve:
        html = "<h1>No power curve found for the current user. Please generate one first.</h1>"
        return html, 404
    

    # Extract the data from the JSON
    current_curve = current_user_curve.curve
    current_x = sorted([int(k) for k in current_curve.keys()])
    current_y = [current_curve[str(k)] for k in current_x]
    
    # Plot the curves
    other_x = other_y = []
    if other_curve:
        other_x = sorted([int(k) for k in other_curve.keys()])
        other_y = [other_curve[str(k)] for k in other_x]

    # Making the plot window
    fig, ax = plt.subplots()
    ax.plot(current_x, current_y, marker='o', label=f"{current_user.strava_id}'s Curve", color='blue')
    if other_curve:
        ax.plot(other_x, other_y, marker='o', label=f"{other_username}'s Curve", color='orange')
    ax.set_xlabel('Duration (seconds)')
    ax.set_ylabel('Power (watts)')
    ax.set_title('Power Curve Comparison')
    ax.legend()

    # Handle the buffering
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')   # Read the PNG bytes and encode as base64
    plt.close(fig)

    # Make the dropdown for the HMTL
    dropdown_html = '<form method="POST"><select name="compare_user">'
    dropdown_html += '<option value="">Select a user to compare</option>'
    for user in users_with_curves:
        selected = 'selected' if other_user_id and str(user.id) == other_user_id else ''
        dropdown_html += f'<option value="{user.id}" {selected}>{user.strava_id}</option>'  
    dropdown_html += '</select><input type="submit" value="Compare"></form>'

    html = "<h1>Compare Power Curves</h1>"
    html += dropdown_html
    html += f'<img src="data:image/png;base64,{img_base64}"/>'

    return html



if __name__ == "__main__":
    app.run(debug=True, port=5050)