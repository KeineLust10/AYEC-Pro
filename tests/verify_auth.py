
import requests
import sys
import time

BASE_URL = "http://localhost:8000"

def test_login_and_access():
    print("--- TEST 1: Login & Access ---")
    # 1. Login
    try:
        # Try legacy password first
        login_data = {"password": "AYEC3008"}
        response = requests.post(f"{BASE_URL}/api/login", json=login_data)
        
        if response.status_code != 200:
            print(f"Login Failed: {response.text}")
            return False
            
        data = response.json()
        token = data.get("token")
        print(f"Login Success. Token: {token[:15]}...")
        
        # 2. Access Protected Route
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(f"{BASE_URL}/api/dashboard", headers=headers)
        
        if resp.status_code == 200:
            print("Dashboard Access: SUCCESS")
        else:
            print(f"Dashboard Access FAILED: {resp.status_code} - {resp.text}")
            return False
            
    except Exception as e:
        print(f"Test 1 Error: {e}")
        return False
    return True

def test_invalid_token():
    print("\n--- TEST 2: Invalid Token ---")
    headers = {"Authorization": "Bearer INVALID_TOKEN_123"}
    resp = requests.get(f"{BASE_URL}/api/dashboard", headers=headers)
    
    if resp.status_code == 401:
        print("Invalid Token Rejected: SUCCESS")
    else:
        print(f"Invalid Token FAILED (Expected 401): {resp.status_code}")
        return False
    return True

def test_legacy_backdoor():
    print("\n--- TEST 3: Legacy Backdoor Token ---")
    headers = {"Authorization": "Bearer ayecpro_secure_token_v3"}
    resp = requests.get(f"{BASE_URL}/api/dashboard", headers=headers)

    if resp.status_code == 401:
        print("Legacy Token Rejected: SUCCESS")
    else:
        print(f"Legacy Token FAILED (Expected 401): {resp.status_code}")
        return False
    return True

if __name__ == "__main__":
    print(f"Testing Server at {BASE_URL}")
    try:
        requests.get(BASE_URL, timeout=2)
    except:
        print("Server not reachable. Please start the server.")
        sys.exit(1)
        
    t1 = test_login_and_access()
    t2 = test_invalid_token()
    t3 = test_legacy_backdoor()
    
    if t1 and t2 and t3:
        print("\nALL TESTS PASSED ✅")
    else:
        print("\nSOME TESTS FAILED ❌")
