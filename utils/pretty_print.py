import json

def pretty_print(obj):
    """
    Print a Python object as pretty JSON to the console.
    If the object is not serializable, it will print a warning.
    """
    try:
        print(json.dumps(obj, indent=4, sort_keys=True))
    except TypeError:
        print("Object is not JSON serializable:", obj)

def print_db_state(db, User, PowerCurve, label=""):
    print(f"\n--- DATABASE STATE {label} ---")
    print("Users:")
    pretty_print([{
        "id": u.id,
        "strava_id": u.strava_id,
        "strava_name": u.strava_name
    } for u in User.query.all()])
    print("PowerCurves:")
    pretty_print([{
        "id": c.id,
        "user_id": c.user_id,
        "strava_id": c.strava_id,
        "activity_id": c.activity_id,
        "curve": c.curve
    } for c in PowerCurve.query.all()])
    print("--- END DATABASE STATE ---\n")
