# Entry Point for the flask application

from flask import Flask, redirect, request, session, render_template, flash, url_for
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import os
import sys
import numpy as np
from dotenv import load_dotenv
import requests
import matplotlib
matplotlib.use('Agg')  # Use 'Agg' backend for non-GUI environments
import matplotlib.pyplot as plt
import io
import base64
# SQLAlchemy for database handling
import psycopg
from flask_sqlalchemy import SQLAlchemy
from models import db, User, PowerCurve
from utils.dummy_data import create_dummy_data
from utils.pretty_print import pretty_print, print_db_state

# load environment variables from .env file
load_dotenv()


app = Flask(__name__)
app.secret_key = os.urandom(24)  # Secret key for session management
# Configure SQLAlchemy to link to Flask
# Determine the mode (dev or prod) based on command-line arguments
if len(sys.argv) > 1 and sys.argv[1] == "dev":
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI_DEV')
    app.config['FLASK_ENV'] = 'development'
    print("Running in Development Mode (SQLite)")
else:
    # The OS Environment Variables should be stored within the configuration of the 
    # elastic beanstalk application
    app.config['SQLALCHEMY_DATABASE_URI'] = (
        f"postgresql+psycopg://{os.getenv('RDS_USERNAME')}:{os.getenv('RDS_PASSWORD')}"
        f"@{os.getenv('RDS_HOSTNAME')}:{os.getenv('RDS_PORT')}/{os.getenv('RDS_DB_NAME')}"
    )
    app.config['FLASK_ENV'] = 'production'
    print("Running in Production Mode (RDS)")

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Create the database tables if they don't exist
if not os.path.exists('powercurve.db'):
    with app.app_context():
        db.create_all()
        
# Get Credentials from environment variables
STRAVA_CLIENT_ID = os.getenv('STRAVA_CLIENT_ID')
STRAVA_CLIENT_SECRET = os.getenv('STRAVA_CLIENT_SECRET')
STRAVA_REDIRECT_URI = os.getenv('STRAVA_REDIRECT_URI')

# Initialize the flask login management
login_manager = LoginManager()
login_manager.login_view = 'landing'  # Redirect to landing page if not logged in
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id)) 

@app.route("/logout")
@login_required
def logout():
    logout_user()
    session.clear()  # <-- This drops all session data
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
    else:
        user_count = User.query.count()
        return render_template("landing.html", user_count=user_count)

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
    session['access_token'] = access_token  # Store access token in session for later use
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
@login_required
def powercurve():
    html = "<h1>Your Power Curve</h1>"
    # Debug statement
    print_db_state(db, User, PowerCurve, label="BEFORE /powercurve")
    
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
    if user:  # Delete old powercurve entries for user based on strava_id
        PowerCurve.query.filter_by(strava_id=strava_id).delete()
        new_power_curve = PowerCurve(
            user_id=user.id,
            activity_id=str(rides_with_power[0][0]),
            curve=powercurve,
            strava_id=strava_id
        )
        db.session.add(new_power_curve)
        db.session.commit()
        # Debug statement
        print_db_state(db, User, PowerCurve, label="AFTER /powercurve")
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
    return render_template(
        "powercurve.html",
        img_base64=img_base64
    )

# Route to compare power curves between users
@app.route("/compare", methods=["GET", "POST"])
@login_required
def compare():
    html = "<h1>Power Curve Comparison</h1>"
    # Get the current user's Strava ID from the session (set after login/callback)
    strava_id = session.get('strava_id')  # <-- session stores the logged-in user's Strava ID
    current_user = User.query.filter_by(strava_id=str(strava_id)).first()
    if not current_user:
        # If no user is found, prompt to authorize
        html = "<h1>No user found. Please authorize first.</h1>"
        return html, 404

    # Query all users (except the current user) who have at least one PowerCurve
    users_with_curves = (
        db.session.query(User)
        .join(PowerCurve, User.id == PowerCurve.user_id)
        .filter(User.id != current_user.id)
        .distinct()
        .all()
    )

    # Get the user ID selected from the dropdown in the compare form (POST request)
    # The dropdown in the HTML form has name="compare_user"
    # This value comes from the <select name="compare_user"> in the compare.html template
    other_user_id = request.form.get("compare_user")
    other_curve = None
    other_username = None
    if other_user_id:
        # If a user was selected, fetch that user by their internal user.id
        other_user = User.query.filter_by(id=int(other_user_id)).first()
        if other_user:
            # Get the latest PowerCurve for the selected user
            other_power_curve = (
                PowerCurve.query.filter_by(user_id=other_user.id)
                .order_by(PowerCurve.created_at.desc())
                .first()
            )
            if other_power_curve:
                other_curve = other_power_curve.curve
                # Use display name if available, otherwise fallback to Strava ID
                other_username = other_user.strava_name or other_user.strava_id

    # Get the current user's latest PowerCurve
    current_user_curve = (
        PowerCurve.query.filter_by(user_id=current_user.id)
        .order_by(PowerCurve.created_at.desc())
        .first()
    )
    if not current_user_curve:
        # If the current user has no PowerCurve, prompt to generate one
        html = "<h1>No power curve found for the current user. Please generate one first.</h1>"
        return html, 404

    # Extract the data from the JSON field in the PowerCurve
    current_curve = current_user_curve.curve
    current_x = sorted([int(k) for k in current_curve.keys()])
    current_y = [current_curve[str(k)] for k in current_x]

    # Prepare the other user's curve if selected
    other_x = other_y = []
    if other_curve:
        other_x = sorted([int(k) for k in other_curve.keys()])
        other_y = [other_curve[str(k)] for k in other_x]

    # Plot both curves using matplotlib
    fig, ax = plt.subplots()
    # Use display name for legend if available
    ax.plot(current_x, current_y, marker='o', label=f"{current_user.strava_name or current_user.strava_id}'s Curve", color='blue')
    if other_curve:
        ax.plot(other_x, other_y, marker='o', label=f"{other_username}'s Curve", color='orange')
    ax.set_xlabel('Duration (seconds)')
    ax.set_ylabel('Power (watts)')
    ax.set_title('Power Curve Comparison')
    ax.legend()

    # Save the plot to a buffer and encode as base64 for HTML display

    # Create an in-memory bytes buffer (no file is written to disk)
    buf = io.BytesIO()

    # Save the matplotlib figure as a PNG image into the buffer
    plt.savefig(buf, format='png')

    # Move the buffer's cursor to the beginning so we can read its contents
    buf.seek(0)

    # Read the PNG image bytes from the buffer and encode them as a base64 string
    # This allows us to embed the image directly in an HTML <img> tag
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')

    # Close the matplotlib figure to free up memory
    plt.close(fig)

    # The dropdown for selecting a user to compare is rendered in the template,
    # but here's how the value is passed:
    # <form method="POST">
    #   <select name="compare_user">...</select>
    #   <input type="submit" value="Compare">
    # </form>
    # When the form is submitted, request.form.get("compare_user") gets the selected value.

    # Render the compare.html template, passing all necessary data
    return render_template(
        "compare.html",
        users_with_curves=users_with_curves,  # List of users for the dropdown
        img_base64=img_base64,                # The plot image to display
        other_user_id=other_user_id           # The selected user (if any)
    )

# Route for deleting data of logged in users to to comply with GDPR
@app.route("/delete-data", methods=["POST"])
def delete_data():
    try:
        print_db_state(db, User, PowerCurve, label="BEFORE DELETE USER DATA")
        # Get the current user's Strava ID
        strava_id = current_user.strava_id

        # Delete all PowerCurve records associated with the user
        PowerCurve.query.filter_by(strava_id=strava_id).delete()

        # Delete the user record
        User.query.filter_by(strava_id=strava_id).delete()

        # Commit changes to the database
        db.session.commit()

        # Log the user out after deleting their data
        logout_user()

        flash("Your data has been deleted successfully.", "success")
        print_db_state(db, User, PowerCurve, label="After DELETE USER DATA")
        return redirect(url_for("home"))
    except Exception as e:
        db.session.rollback()
        flash(f"An error occurred while deleting your data: {str(e)}", "error")
        return redirect(url_for("home"))


# Route to publish the privacy policy template
@app.route("/privacy_policy")
def privacy_policy():
    return render_template("privacy_policy.html")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # <-- This creates tables if they don't exist
        # Now it's safe to query the tables
        if PowerCurve.query.count() <= 2:
            create_dummy_data(app)
    # Run on port 8080 because it should work with Elastic Beanstalk
    app.run(debug=True, port=8000, host="0.0.0.0")