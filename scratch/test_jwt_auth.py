import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_auth():
    print("1. Checking root endpoint...")
    try:
        r = requests.get(f"{BASE_URL}/")
        print(f"Status: {r.status_code}, Response: {r.json()}")
    except Exception as e:
        print(f"Could not connect to {BASE_URL}: {e}")
        return

    # Generate a unique email to avoid "already registered" error if run multiple times
    import time
    test_email = f"test_{int(time.time())}@example.com"
    test_password = "securepassword123"

    print("\n2. Testing POST /Auth/register...")
    register_payload = {
        "email": test_email,
        "password": test_password,
        "role": "employee",
        "emp_id": None
    }
    r = requests.post(f"{BASE_URL}/Auth/register", json=register_payload)
    print(f"Status: {r.status_code}")
    if r.status_code == 201:
        print(f"Response: {json.dumps(r.json(), indent=2)}")
    else:
        print(f"Failed: {r.text}")
        return

    print("\n3. Testing POST /Auth/login...")
    login_payload = {
        "email": test_email,
        "password": test_password
    }
    r = requests.post(f"{BASE_URL}/Auth/login", json=login_payload)
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        login_res = r.json()
        print(f"Response: {json.dumps(login_res, indent=2)}")
        access_token = login_res["access_token"]
        refresh_token = login_res["refresh_token"]
    else:
        print(f"Failed: {r.text}")
        return

    print("\n4. Testing GET /Auth/me with access token...")
    headers = {"Authorization": f"Bearer {access_token}"}
    r = requests.get(f"{BASE_URL}/Auth/me", headers=headers)
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        print(f"Response: {json.dumps(r.json(), indent=2)}")
    else:
        print(f"Failed: {r.text}")

    print("\n5. Testing POST /Auth/refresh...")
    refresh_payload = {
        "refresh_token": refresh_token
    }
    r = requests.post(f"{BASE_URL}/Auth/refresh", json=refresh_payload)
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        refresh_res = r.json()
        print(f"Response: {json.dumps(refresh_res, indent=2)}")
        new_access_token = refresh_res["access_token"]
    else:
        print(f"Failed: {r.text}")
        return

    print("\n6. Testing GET /Auth/me with NEW access token...")
    headers = {"Authorization": f"Bearer {new_access_token}"}
    r = requests.get(f"{BASE_URL}/Auth/me", headers=headers)
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        print(f"Response: {json.dumps(r.json(), indent=2)}")
        print("\nAll Auth tests completed successfully! 🎉")
    else:
        print(f"Failed: {r.text}")

if __name__ == "__main__":
    test_auth()
