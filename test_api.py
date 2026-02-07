import requests
import time
import sys

def test_scan():
    try:
        # Check API Status
        print("Checking API Status...")
        r_status = requests.get("http://127.0.0.1:8000/api/status")
        data = r_status.json()
        print(f"API VERSION: {data.get('version')}")
        print(f"DB STATUS: {data.get('estado_base_datos')}")
        print(f"WORKER: {data.get('trabajador')}")
        
    except Exception as e:
        print(f"Error connecting to API: {e}")

if __name__ == "__main__":
    test_scan()
