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