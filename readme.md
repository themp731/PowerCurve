# PowerCurve: Strava Power Curve Web App

PowerCurve is a Flask-based web application that allows users to connect their Strava accounts, authorize access, and analyze their cycling power curve data. The app is designed for cyclists who want to visualize and compare their power output over different durations, using data pulled directly from Strava.

---

## Features

- **Strava OAuth2 Integration:** Securely authorize with Strava to access your activity data.
- **Power Curve Visualization:** Generate and view your power curve from recent rides.
- **User Management:** Multi-user support with unique Strava-linked accounts.
- **Dummy Data Support:** Easily populate the database with test users and power curves for development.
- **Automatic Database Handling:** The app checks for the existence of the database and creates it if missing.
- **Simple, Modern Flask Codebase:** Easy to extend and maintain.

---

## Getting Started

### Prerequisites

- Python 3.8+
- [pip](https://pip.pypa.io/en/stable/)
- A Strava API application (get your client ID, secret, and set a redirect URI at https://www.strava.com/settings/api)

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
   flask run
   ```
   Access the app at `http://127.0.0.1:5000`.

---

## Template Files Explained

The `templates` folder contains all the HTML files used by Flask to render pages. Here’s what each file does:

- **base.html**  
  The main layout template. It defines the overall HTML structure, navigation bar, and a `{% block content %}` placeholder where page-specific content is inserted. All other templates extend this file to ensure a consistent look and navigation across the site.

- **landing.html**  
  The public landing page for users who are **not logged in**. It welcomes new users and provides a single "Log in with Strava" button. If a user is already logged in, they are redirected to the home page.

- **home.html**  
  The dashboard page for **logged-in users**. It greets the user (using their Strava name or ID), and provides links to update their Strava PowerCurve, compare power curves, and log out. This page is only accessible after logging in with Strava.

- **login.html**  
  (Legacy, not used in Strava-only login) Previously used for username/password login. If you switch to Strava-only authentication, you can remove or repurpose this file to simply direct users to "Log in with Strava."

- **signup.html**  
  (Legacy, not used in Strava-only login) Previously used for account creation with username/password. With Strava-only authentication, you can remove or repurpose this file as well.

### How `base.html`, `landing.html`, and `home.html` Differ

- **base.html** is the foundation for all pages. It contains the HTML `<head>`, navigation bar, and a content block. Other templates extend it and fill in the `{% block content %}` section with their own content.
- **landing.html** is shown to users who are not logged in. It extends `base.html` and provides a welcome message and a "Log in with Strava" button.
- **home.html** is shown to users who are logged in. It also extends `base.html`, but displays personalized content and links relevant to authenticated users.

This structure keeps your site organized, makes it easy to update navigation or layout in one place (`base.html`), and ensures users see the right content based on their authentication status.