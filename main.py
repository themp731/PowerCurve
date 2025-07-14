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

@app.route("/")
def home():
    return '<a href="/authorize">Connect With Strava</a>'

@app.route("/authorize")
def authorize():
    auth_url = (
        f"https://www.strava.com/oauth/authorize"
        f"?client_id={CLIENT_ID}"
        f"&response_type=code"
        f"&redirect_uri={REDIRECT_URI}"
        f"&approval_prompt=force"
        f"&scope=read,activity:read"
    )
    return redirect(auth_url)

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

if __name__ == "__main__":
    app.run(debug=True)