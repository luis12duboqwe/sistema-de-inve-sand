import requests
import sys

def test_login():
    url = "http://localhost:8000/api/auth/token"
    data = {
        "username": "admin",
        "password": "admin123"
    }
    try:
        response = requests.post(url, data=data)
        print(f"Status Code: {response.status_code}")
        if response.status_code != 200:
            print("Response Text:")
            print(response.text)
        else:
            print("Login Successful")
            print(response.json())
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_login()
