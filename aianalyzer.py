from google import genai
import json
import os

GEMINI_API_KEY = os.getenv("gen_api_key")

def analizuj_wiadomosc(message_to_analyze):
    if not GEMINI_API_KEY:
        print("[ERROR] Brak klucza API Gemini w zmiennych środowiskowych (gen_api_key).")
        return None

    instructions = (
        "Jesteś surowym moderatorem YouTube. Przeanalizuj wiadomość. "
        "Zwróć wynik WYŁĄCZNIE w czystym formacie JSON, bez żadnych znaczników markdown czy tekstu. "
        "Wymagana struktura: {\"czy_toksyczny\": boolean, \"waga_przewinienia\": integer, \"powod\": \"string\"}. "
        "Skala wagi_przewinienia (0-4): "
        "0 - wiadomość czysta (czy_toksyczny: false); "
        "1 - zwykłe, lekkie przekleństwa bez ataku; "
        "2 - bezpośrednie wyzwiska w stronę kogoś/spam; "
        "3 - bardzo ostre wyzwiska, groźby, życzenie śmierci; "
        "4 - skrajny rasizm, homofobia, łamanie prawa."
    )

    client = genai.Client(api_key=GEMINI_API_KEY)

    try:

        response = client.models.generate_content(
            model="gemini-2.5-flash", 
            contents=[instructions, message_to_analyze]
        )
        
        clean_text = response.text.strip()
        
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
            
        analysis_data = json.loads(clean_text.strip())
        return analysis_data
        
    except json.JSONDecodeError as e:
        print(f"[ERROR] Błąd parsowania JSON od AI. Odpowiedź była wadliwa: {e}")
        return {"czy_toksyczny": False, "waga_przewinienia": 0, "powod": "Błąd dekodowania API"}
    except Exception as e:
        print(f"[ERROR] Coś poszło nie tak podczas analizy AI: {e}")
        return {"czy_toksyczny": False, "waga_przewinienia": 0, "powod": "Błąd API"}