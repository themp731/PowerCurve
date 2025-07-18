# Entry Point for the flask application

from flask import Flask, redirect, request, session
import os
import numpy as np
from dotenv import load_dotenv
import requests
import matplotlib.pyplot as plt
import io
import base64
# SQLAlchemy for database handling
from models import db, User, PowerCurve

# load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Secret key for session management
# Configure SQLAlchemy to link to Flask
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///powercurve.db'
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

# Saving PowerCurves in memory for now
user_powercurves = {}

# Starts the OATH2.0 flow with Strava
@app.route("/")
def home():
    return '''
        <h1>Welcome to the Strava Data App</h1>
        <p><a href="/authorize">Click here to authorize with Strava</a></p>
        '''

# Authorizing the Application to work with your strava
@app.route("/authorize")
def authorize():
    auth_url = (
        f"https://www.strava.com/oauth/authorize"
        f"?client_id={STRAVA_CLIENT_ID}"
        f"&response_type=code"
        f"&redirect_uri={STRAVA_REDIRECT_URI}"
        f"&approval_prompt=force"
        f"&scope=read,activity:read"
    )
    return redirect(auth_url)

# Sends you to the callback page and lets go to the next step
@app.route("/strava/callback")
def callback():
    code = request.args.get('code')
    if not code:
        return "Authorization failed. No code provided.", 400
    token_response = requests.post("https://www.strava.com/oauth/token", data={
        'client_id': STRAVA_CLIENT_ID,
        'client_secret': STRAVA_CLIENT_SECRET,
        'code': code,
        'grant_type': 'authorization_code'},
        verify=False) # DISABLES TESTING WILL NEED TO BE REMOVED FOR PRODUCTION)
    
    token_json = token_response.json()
    access_token = token_json.get('access_token')

    if access_token:
        session['access_token'] = access_token
        # Get athlete ID
        athlete_response = requests.get("https://www.strava.com/api/v3/athlete",
                                        headers={"Authorization": f"Bearer {access_token}"},
                                        verify=False)
        # If we get a good response, save the athlete ID in session
        if athlete_response.status_code == 200:
            # Save the response data as a JSON string and extract each item
            athlete_json = athlete_response.json()
            athlete_id = athlete_json.get('id')
            session['athlete_id'] = athlete_id
            user_name = f"{athlete_json.get('firstname','')} {athlete_json.get('lastname','')}".strip()     
            
            # Save user in database if not already present 
            # Takes the user table/cass from models.py and does a filter query
            user = User.query.filter_by(strava_id=str(athlete_id)).first()
            # If not found, added it
            if not user:
                user = User(strava_id=str(athlete_id), access_token=access_token, 
                            user_name=user_name)
                db.session.add(user)
            else:
                user.access_token = access_token # Update access token if changed
            db.session.commit()
        else:
            return "Failed to fetch athlete information.", 500
        
        # If you get a good token, let the user know and give options for next steps
        return '''
            <h1>Authorization successful!</h1>
            <p><a href="/activities">View your recent cycling activities</a></p>
            <p><a href="/powercurve">Generate your PowerCurve</a></p>
        '''
    else:
        return "Authorization failed. No access token received.", 400


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

        
    # Set up duractions for PowerCurve
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
    athlete_id = session.get('athlete_id') # Get athlete ID from session
    user = User.query.filter_by(strava_id=str(athlete_id)).first()
    # Look up the user name based on athlete ID to save into PowerCurve DB
    user_name = user.user_name if user else "Unknown"
    if user: # Delete old powercurve entries for user
        PowerCurve.query.filter_by(user_id=user.id).delete()
        new_power_curve = PowerCurve(
            user_id=user.id,
            activity_id=str(rides_with_power[0][0]), # Use the first ride's ID as a reference
            curve=powercurve, # Save the generated power curve as JSON
            user_name=user_name
        )
        db.session.add(new_power_curve)
        db.session.commit()
    else: # Handle case where user is not found
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

@app.route("/compare")
def compare():
    
    # Take the current session ID and query the DB for the user
    current_user_id = session.get('athlete_id')
    current_user = User.query.filter_by(strava_id=str(current_user_id)).first()
    if not current_user:
        html = "<h1>No user found. Please authorize first.</h1>"
        return html, 404
    
if __name__ == "__main__":
    app.run(debug=True, port=5050)