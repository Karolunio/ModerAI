import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']

def authenticate_youtube():
    creds = None
    
    
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
           
            print("Odœwie¿am wygas³y token...")
            creds.refresh(Request())
        else:
            print("Brak tokenu. Otwieram przegl¹darkê do logowania...")
            flow = InstalledAppFlow.from_client_secrets_file(
                'client_secret.json', SCOPES)
            creds = flow.run_local_server(port=0)
            
        with open('token.json', 'w') as token_file:
            token_file.write(creds.to_json())
            print("nowy token do pliku token.json")

    return build('youtube', 'v3', credentials=creds)

if __name__ == '__main__':
    print("Testowanie autoryzacji...")
    youtube = authenticate_youtube()
    print("Mamy to!")