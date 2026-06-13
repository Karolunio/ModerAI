import sys
import time
import sqlite3
import json
from datetime import datetime
import youtube
import aianalyzer  

if len(sys.argv) < 2:
    print("[ERROR] Krytyczny błąd: Bot nie wie, czyje konto obsługuje. Brak argumentu user_id.")
    sys.exit(1)

USER_ID = int(sys.argv[1])

BOT_CHANNEL_ID = "UCOCVh2VCkGDW-tgZVmeum3w"

def get_user_channel_id():
    con = sqlite3.connect("database.db")
    cur = con.cursor()
    cur.execute("SELECT youtube_channel_id FROM users WHERE id = ?", (USER_ID,))
    res = cur.fetchone()
    con.close()
    return res[0] if res else None

def log_to_terminal(username, tresc, poziom):
    """Zapisuje zdarzenie do bazy, skąd przyjazny terminal webowy od razu je wyświetli"""
    con = sqlite3.connect("database.db")
    cur = con.cursor()
    teraz = datetime.now().strftime("%H:%M:%S")
    cur.execute("INSERT INTO terminal_logs (user_id, godzina, username, tresc, poziom) VALUES (?, ?, ?, ?, ?)",
                (USER_ID, teraz, username, tresc, poziom))
    con.commit()
    con.close()

def main():
    channel_id = get_user_channel_id()
    if not channel_id:
        print(f"[ERROR] Użytkownik {USER_ID} nie podpiął konta YouTube na stronie WWW!")
        sys.exit(1)
        
    yt_client = youtube.get_authenticated_service()
    chat_id = None
    
    while not chat_id:
        chat_id = youtube.get_live_chat_id(yt_client, channel_id)
        if not chat_id:
            time.sleep(10)
            
    try:
        init_res = yt_client.liveChatMessages().list(liveChatId=chat_id, part="snippet").execute()
        next_token = init_res.get("nextPageToken")
    except:
        next_token = None
        
    while True:
        try:
            res = yt_client.liveChatMessages().list(liveChatId=chat_id, part="snippet,authorDetails", pageToken=next_token).execute()
            polling_interval = res.get("pollingIntervalMillis", 5000) / 1000.0
            next_token = res.get("nextPageToken")
            
            for item in res.get("items", []):
                if item["snippet"]["type"] != "textMessageEvent": continue
                
                tekst = item["snippet"]["textMessageDetails"]["messageText"]
                nick = item["authorDetails"]["displayName"]
                uid = item["snippet"]["authorChannelId"]
                msg_id = item["id"]
                
                if uid == BOT_CHANNEL_ID: continue
                
                try:
                    wynik_ai = aianalyzer.analizuj_wiadomosc(tekst)
                    if not wynik_ai: continue
                    ai_data = json.loads(wynik_ai) if isinstance(wynik_ai, str) else wynik_ai
                except:
                    continue
                    
                czy_toksyczny = ai_data.get("czy_toksyczny", False)
                waga = ai_data.get("waga_przewinienia", 0)
                
                if czy_toksyczny:
                    youtube.delete_message(yt_client, msg_id)
                    
                    if waga == 1: youtube.apply_punishment(yt_client, chat_id, uid, 60)
                    elif waga == 2: youtube.apply_punishment(yt_client, chat_id, uid, 300)
                    elif waga == 3: youtube.apply_punishment(yt_client, chat_id, uid, 86400)
                    else: youtube.apply_punishment(yt_client, chat_id, uid, 'PERMA')
                    
                    log_to_terminal(nick, tekst, waga)
                else:
                    log_to_terminal(nick, tekst, 0)
                    
            time.sleep(polling_interval)
        except:
            time.sleep(5)

if __name__ == '__main__':
    main()