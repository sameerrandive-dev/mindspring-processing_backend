"""
Script to create a notebook using the MindSpring FastAPI backend.

This script will:
1. Check if the server is running
2. Sign up a test user (or login if exists)
3. Create a notebook using the API
"""

import requests
import sys
import time
from typing import Optional

BASE_URL = "http://localhost:8000/api/v1"

def check_server() -> bool:
    """Check if the FastAPI server is running."""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=2)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

def signup(email: str, password: str) -> Optional[dict]:
    """Sign up a new user."""
    try:
        response = requests.post(
            f"{BASE_URL}/auth/signup",
            json={"email": email, "password": password}
        )
        if response.status_code == 201:
            print(f"✅ User signed up: {email}")
            return response.json()
        elif response.status_code == 400:
            print(f"ℹ️  User may already exist: {email}")
            return None
        else:
            print(f"❌ Signup failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Signup error: {e}")
        return None

def verify_otp(email: str, otp_code: str) -> bool:
    """Verify OTP code."""
    try:
        response = requests.post(
            f"{BASE_URL}/auth/verify-otp",
            json={"email": email, "code": otp_code}
        )
        if response.status_code == 200:
            print(f"✅ OTP verified for: {email}")
            return True
        else:
            print(f"❌ OTP verification failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ OTP verification error: {e}")
        return False

def login(email: str, password: str) -> Optional[str]:
    """Login and get access token."""
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"email": email, "password": password}
        )
        if response.status_code == 200:
            data = response.json()
            access_token = data.get("access_token")
            if access_token:
                print(f"✅ Logged in: {email}")
                return access_token
            else:
                print(f"❌ No access token in response: {data}")
                return None
        else:
            print(f"❌ Login failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Login error: {e}")
        return None

def create_notebook(access_token: str, title: str = "Test Notebook", 
                   description: str = "Created via API script",
                   language: str = "en", 
                   tone: str = "educational",
                   max_context_tokens: int = 8000) -> Optional[dict]:
    """Create a notebook using the API."""
    try:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        data = {
            "title": title,
            "description": description,
            "language": language,
            "tone": tone,
            "max_context_tokens": max_context_tokens
        }
        response = requests.post(
            f"{BASE_URL}/notebooks/",
            headers=headers,
            json=data
        )
        if response.status_code == 201:
            notebook = response.json()
            print(f"✅ Notebook created successfully!")
            print(f"   ID: {notebook.get('id')}")
            print(f"   Title: {notebook.get('title')}")
            print(f"   Description: {notebook.get('description')}")
            return notebook
        else:
            print(f"❌ Notebook creation failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Notebook creation error: {e}")
        return None

def main():
    """Main function to create a notebook."""
    print("🚀 MindSpring FastAPI - Create Notebook Script\n")
    
    # Check if server is running
    print("1. Checking if server is running...")
    if not check_server():
        print("❌ Server is not running!")
        print("\nPlease start the server with:")
        print("   uvicorn app.main:app --reload --port 8000")
        sys.exit(1)
    print("✅ Server is running\n")
    
    # User credentials
    email = input("Enter email (or press Enter for test@example.com): ").strip() or "test@example.com"
    password = input("Enter password (or press Enter for TestPassword123!): ").strip() or "TestPassword123!"
    
    print(f"\n2. Attempting to sign up/login: {email}")
    
    # Try to sign up first
    signup_result = signup(email, password)
    
    # If signup was successful, we need to verify OTP
    # For now, let's try to login (user might already exist)
    access_token = login(email, password)
    
    if not access_token:
        print("\n❌ Could not get access token. Please check:")
        print("   1. User exists and is verified")
        print("   2. Password is correct")
        print("   3. Server is running correctly")
        sys.exit(1)
    
    print(f"\n3. Creating notebook...")
    notebook = create_notebook(
        access_token=access_token,
        title="My First Notebook",
        description="Created using the FastAPI backend",
        language="en",
        tone="educational"
    )
    
    if notebook:
        print("\n✅ Success! Notebook created via FastAPI backend.")
        return 0
    else:
        print("\n❌ Failed to create notebook.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
