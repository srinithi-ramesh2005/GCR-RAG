import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Updated scopes - simpler and more reliable
SCOPES = [
    'https://www.googleapis.com/auth/classroom.courses.readonly',
    'https://www.googleapis.com/auth/classroom.courseworkmaterials.readonly',
    'https://www.googleapis.com/auth/drive.readonly'
    # Removed: classroom.coursework.students.readonly (you don't need this yet)
]

def authenticate_google():
    """Authenticate user and return credentials."""
    creds = None
    token_path = 'credentials/token.json'
    credentials_path = 'credentials/credentials.json'
    
    # Check if token.json already exists
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    # If no valid credentials, prompt user to log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_path, SCOPES
            )
            # Use a specific port for better reliability
            creds = flow.run_local_server(port=8080, open_browser=True)
        
        # Save credentials for next run
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
        print(f"✅ Authentication successful! Token saved to {token_path}")
    
    return creds

if __name__ == "__main__":
    # Test the authentication
    print("🔐 Starting Google authentication...")
    creds = authenticate_google()
    print("✅ Authentication completed successfully!")
    print(f"   Token expires at: {creds.expiry}")
    