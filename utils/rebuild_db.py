# utility script to rebuild the database after changes.
import os
import sys

# Add the project root to the path so we can import models and app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models import db
from main import app

def rebuild_database():
    db_path = os.path.join(os.path.dirname(__file__), '..', 'powercurve.db')
    # Delete the existing database file if it exists
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"Removed existing database at {db_path}")    
    
    # Recreate the tables.
    with app.app_context():
        db.create_all()
        print("Recreated the database tables.")
    
    from utils.dummy_data import create_dummy_data
    create_dummy_data(app)
    print("Dummy data created.")

if __name__ == "__main__":
    rebuild_database()
    print("Database rebuild complete.")