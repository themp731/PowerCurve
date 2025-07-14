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
    print("Home Route Hit")
    return '<h1>Hello from PowerCurve!</h1><p><a href="/authorize">Authorize with Strava</a></p>'

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


if __name__ == "__main__":
    app.run(debug=True, port=5050)