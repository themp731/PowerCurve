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
├── app/                     # Application logic (Strava API, power curve math)
│   ├── powercurve.py        # Math for creating the PowerCurve and charts
│   └── strava.py            # API logic for getting Strava data
├── instance/                # SQLite database file (powercurve.db)
├── templates/               # HTML templates for Flask pages
│   ├── base.html                # Base template with shared layout and blocks
│   ├── compare.html             # Page for comparing power curves between users
│   ├── home.html                # Main dashboard after login, showing user stats and power curve
│   ├── landing.html             # Landing page for unauthenticated users, app intro and login prompt
│   ├── powercurve.html          # Visualization of the user's power curve data
│   └── privacy_policy.html      # Privacy policy and GDPR compliance information
├── static/                  # Static assets (CSS, JS, images)
│   ├── css/
│   │   └── style.css            # Custom styles for the app
│   ├── js/
│   └── images/                  # Strava branding and other images
├── utils/                   # Utility scripts
│   ├── dummy_data.py            # Populate the database with test users and power curves
│   ├── pretty_print.py          # Helper functions for formatting and displaying data
│   └── rebuild_db.py            # Script to reset and rebuild the database
├── .github/
│   └── workflows/
│       └── deploy.yaml          # GitHub Actions workflow for Elastic Beanstalk deployment
├── ebextensions/
│   └── 01_clean_build.config    # Elastic Beanstalk build configuration
├── models.py                # SQLAlchemy models (User, PowerCurve)
├── main.py                  # Entry point for the Flask app
├── requirements.txt         # Python dependencies
├── Procfile                 # Elastic Beanstalk process file
├── .env                     # Environment variables for local/dev
├── .gitignore               # Git ignore rules
└── readme.md                # Project documentation

```

---

## Deployment to Elastic Beanstalk via GitHub Actions

You can automate deployment to AWS Elastic Beanstalk using a GitHub Actions workflow. This approach pushes your code directly from GitHub to Elastic Beanstalk whenever you update your repository.

### Setting Up GitHub Actions for EB Deployment

1. **Create a Workflow File:**  
  Add a file like `.github/workflows/deploy.yml` to your repository. 

2. **Add AWS Credentials as GitHub Secrets:**  
  Go to your repository’s **Settings > Secrets and variables > Actions** and add:
  - `AWS_ACCESS_KEY_ID`
  - `AWS_SECRET_ACCESS_KEY`

  These credentials allow the workflow to authenticate and deploy to AWS.

3. **Trigger Deployment:**  
  Pushing changes to the `beanstalk1` branch will trigger the workflow and deploy your app.

---

## Fixing RDS Connectivity via Route Table

If your Elastic Beanstalk app cannot access the RDS database, update your VPC route table:

1. Go to the **VPC Console** in AWS.
2. Select **Route Tables** and find `rtb-9033a5fb` (main route table).
3. Click the **Subnet Associations** tab.
4. Click **Edit subnet associations**.
5. Select your RDS subnet: `subnet-015db541e5c16598b`.
6. Save changes.

This ensures your RDS instance is properly associated with the main route table, allowing network connectivity from your Elastic Beanstalk environment.

---

## Other Things to Know

### Environment Variables on Elastic Beanstalk

When deploying to Elastic Beanstalk, set the following environment variables in the AWS EB Console (**Configuration > Software > Environment properties**):

- `STRAVA_CLIENT_ID`  
- `STRAVA_CLIENT_SECRET`  
- `STRAVA_REDIRECT_URI`  
- `RDS_USERNAME`  
- `RDS_PASSWORD`  
- `RDS_HOSTNAME`  
- `RDS_PORT`  
- `RDS_DB_NAME`  
- `SQLALCHEMY_DATABASE_URI_DEV` (for local development, optional)

These variables are used by the Flask app for Strava API integration and database connectivity. Make sure they match your RDS and Strava app settings.

### psycopg3 and Binary Dependencies

Elastic Beanstalk Python environments may have issues building database drivers from source due to missing system libraries. For PostgreSQL, use the `psycopg` (psycopg3) binary package:

```sh
pip install psycopg[binary]
```

Update your `requirements.txt` to use `psycopg[binary]` instead of `psycopg2` or `psycopg2-binary`. This ensures compatibility and avoids compilation problems during deployment.

If you need other system-level binaries, use an `.ebextensions` config file to install them at build time.

--- 