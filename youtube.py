import os
import pickle
import urllib.request
import re
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

def get_authenticated_service():
    scopes = ["https://www.googleapis.com/auth/youtube.force-ssl"]
    creds = None
    if os.path.exists("token.json"):
        with open("token.json", "rb") as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", scopes)
            creds = flow.run_local_server(port=0)
        with open("token.json", "wb") as token:
            pickle.dump(creds, token)
    return build("youtube", "v3", credentials=creds)

def get_live_chat_id(yt_client, channel_id):
    url = f"https://www.youtube.com/channel/{channel_id}/live"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        html = urllib.request.urlopen(req).read().decode('utf-8')
        match = re.search(r'rel="canonical" href="https://www.youtube.com/watch\?v=([^"]+)"', html)
        if match:
            video_id = match.group(1)
            request = yt_client.videos().list(part="liveStreamingDetails", id=video_id)
            response = request.execute()
            items = response.get("items", [])
            if items:
                return items[0].get("liveStreamingDetails", {}).get("activeLiveChatId")
    except Exception as e:
        pass
    return None

def delete_message(yt_client, message_id):
    try: 
        yt_client.liveChatMessages().delete(id=message_id).execute()
    except Exception as e:
        print(f"[API BŁĄD] Nie usunięto wiadomości: {e}")

def apply_punishment(yt_client, chat_id, user_channel_id, duration_seconds=None):
    if duration_seconds == 'PERMA' or duration_seconds is None:
        body = {
            "snippet": {
                "liveChatId": chat_id,
                "type": "permanent",
                "bannedUserDetails": {"channelId": user_channel_id}
            }
        }
    else:
        safe_duration = min(duration_seconds, 86400)
        body = {
            "snippet": {
                "liveChatId": chat_id,
                "type": "temporary",
                "banDurationSeconds": safe_duration,
                "bannedUserDetails": {"channelId": user_channel_id}
            }
        }
        
    try: 
        yt_client.liveChatBans().insert(part="snippet", body=body).execute()
    except Exception as e: 
        print(f"[API BŁĄD BANOWANIA]: {e}")

def send_message(yt_client, chat_id, text):
    try:
        body = {"snippet": {"liveChatId": chat_id, "type": "textMessageEvent", "textMessageDetails": {"messageText": text}}}
        yt_client.liveChatMessages().insert(part="snippet", body=body).execute()
    except Exception as e:
        print(f"[API BŁĄD] Nie wysłano wiadomości na czat: {e}")