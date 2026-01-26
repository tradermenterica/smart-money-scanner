import requests
import json

BASE_URL = "http://localhost:8000/api"

def test_darwinex_scan():
    print("Testing /api/scan-darwinex...")
    try:
        response = requests.get(f"{BASE_URL}/scan-darwinex?limit=5")
        if response.status_code == 200:
            data = response.json()
            print(f"Success! Found {data['conteo']} Darwinex stocks in DB.")
            for stock in data['resultados']:
                print(f" - {stock['symbol']}: {stock['score']} pts")
        else:
            print(f"Failed with status code: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Error connecting to server: {e}")

if __name__ == "__main__":
    test_darwinex_scan()
