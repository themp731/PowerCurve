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