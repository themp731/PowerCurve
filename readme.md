# PowerCurve: Strava Power Curve Web App
PowerCurve is a Flask-based web application that lets cyclists connect their Strava accounts, analyze their cycling power curve data, and compare performance with other users. The app securely pulls activity data from Strava, computes power curves, and visualizes results for easy analysis.

---

## Features

- **Strava OAuth2 Integration:** Secure login and authorization with Strava to access your activity data.
- **Power Curve Visualization:** Generate and view your power curve from your last 5 rides.
- **Compare Power Curves:** Compare your power curve with other users who have authorized the app.
- **User Management:** Multi-user support with unique Strava-linked accounts.
- **Dummy Data Support:** Easily populate the database with test users and power curves for development.
- **Automatic Database Handling:** The app checks for the existence of the database and creates it if missing.
- **GDPR-Compliant Data Deletion:** Users can delete their data and log out at any time.
- **Simple, Modern Flask Codebase:** Easy to extend and maintain.

---

## Getting Started

### Prerequisites

- Python 3.8+
- [pip](https://pip.pypa.io/en/stable/)
- A Strava API application (get your client ID, secret, and set a redirect URI at [Strava API Settings](https://www.strava.com/settings/api))

### Installation

1. **Clone the repository:**
  ```sh
  git clone https://github.com/themp731/PowerCurve.git
  cd PowerCurve
  ```
2. **Create and activate a virtual environment:**
  ```sh
  python -m venv venv
  # Windows
  venv\Scripts\activate
  # macOS/Linux
  source venv/bin/activate
  ```
3. **Install the required packages:**
  ```sh
  pip install -r requirements.txt
  ```
4. **Set up your Strava API credentials:**
  - Copy `example.env` to `.env`
  - Fill in your Strava `CLIENT_ID`, `CLIENT_SECRET`, and `REDIRECT_URI`

5. **Run the application:**
  ```sh
  python main.py
  ```
  Access the app at [http://127.0.0.1:8000](http://127.0.0.1:8000).

---

## Project Structure

Here’s an overview of the folder structure and the purpose of each file:

```
PowerCurve/
├── instance/           # Contains the SQLite database file (powercurve.db)
├── templates/          # HTML templates for Flask pages
│   ├── base.html            # Base template with shared layout and blocks for other pages to extend
│   ├── compare.html         # Page for comparing power curves between users
│   ├── home.html            # Main dashboard after login, showing user stats and power curve
│   ├── landing.html         # Landing page for unauthenticated users, app intro and login prompt
│   ├── powercurve.html      # Detailed visualization of the user's power curve data
│   └── privacy_policy.html  # Privacy policy and GDPR compliance information
├── static/             # Static assets (CSS, JS, images) — *not used yet*
│   ├── css/
│   ├── js/
│   └── images/
├── utils/              # Utility scripts
│   ├── dummy_data.py       # Script to populate the database with test users and power curves
│   ├── pretty_print.py     # Helper functions for formatting and displaying data
│   └── rebuild_db.py       # Script to reset and rebuild the database
├── models.py           # SQLAlchemy models (User, PowerCurve)
├── routes.py           # Flask routes (login, logout, data deletion, etc.)
├── main.py             # Entry point for the Flask app
├── requirements.txt    # Python dependencies
└── Procfile            # Elastic Beanstalk process file

```

---

## Deployment to Elastic Beanstalk

1. Ensure the `beanstalk1` branch is up-to-date with your changes.
2. Push the branch to the remote repository.
3. Deploy the branch to Elastic Beanstalk using the AWS Management Console or CLI.
