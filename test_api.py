import requests
import time
import sys

def test_scan():
    try:
        # Check Home for DB Count
        print("Checking DB Status...")
        r_home = requests.get("http://127.0.0.1:8000/")
        data = r_home.json()
        print(f"DB STATUS: {data.get('db_status')}")
        
    except Exception as e:
        print(f"Error connecting to API: {e}")

if __name__ == "__main__":
    test_scan()
