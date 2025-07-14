# Entry Point for the flask application

from flask import Flask, redirect, request, session
import os
from dotenv import load_dotenv
import requests

# load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Secret key for session management

# Get Credentials from environment variables
STRAVA_CLIENT_ID = os.getenv('STRAVA_CLIENT_ID')
STRAVA_CLIENT_SECRET = os.getenv('STRAVA_CLIENT_SECRET')
STRAVA_REDIRECT_URI = os.getenv('STRAVA_REDIRECT_URI')

# Starts the OATH2.0 flow with Strava
@app.route("/")
def home():
    return '''
        <h1>Welcome to the Strava Data App</h1>
        <p><a href="/authorize">Click here to authorize with Strava</a></p>
        <p><a href="/activities">View your recent cycling activities</a></p>
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

# Sends you back home and lets you know what happend with your code request
@app.route("/callback")
def callback():
    code = request.args.get('code')
    if not code:
        return "Authorization failed. No code provided.", 400
    token_response = requests.post("https://www.strava.com/oauth/token", data={
        'client_id': STRAVA_CLIENT_ID,
        'client_secret': STRAVA_CLIENT_SECRET,
        'code': code,
        'grant_type': 'authorization_code'})
    
    token_json = token_response.json()
    access_token = token_json.get('access_token')

    if access_token:
        session['access_token'] = access_token
        return "Authorization successful! You can now access your Strava data." 
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
                                       params={"per_page":10})

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

if __name__ == "__main__":
    app.run(debug=True, port=5050)