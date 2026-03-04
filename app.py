import pandas as pd
from flask import Flask, jsonify
from flask_cors import CORS
import requests
import os
import joblib
import re
import warnings
import urllib3
import time

# --- KONFIGURACIJA SUSTAVA ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore", category=UserWarning)

app = Flask(__name__)
CORS(app)

# --- KONSTANTE ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KOTA_NULA = 40.29          # Nadmorska visina mjerne postaje (0 na letvi)
BIOLOSKI_MINIMUM = 50.0    # m3/s (Ekološka granica)
NORMALNI_VODOSTAJ = 430.0  # Referentna točka za Vodnu dozvolu
GRANICA_DOZVOLE = 200.0    # Dozvoljeno odstupanje +- 2 metra

# Memorija za očitavanja (Cache - 10 minuta da nas ne blokiraju)
zadnji_podaci = {
    "v": 409.0,
    "t": -10.0,
    "vrijeme_zadnjeg_citanja": 0
}

# --- UČITAVANJE AI MODELA ---
try:
    model = joblib.load(os.path.join(BASE_DIR, 'ecoflow_model_final.pkl'))
    scaler = joblib.load(os.path.join(BASE_DIR, 'scaler_final.pkl'))
    print("[INFO] EcoFlow AI model uspješno učitan i spreman.")
except Exception as e:
    model, scaler = None, None
    print(f"[UPOZORENJE] Model nije pronađen: {e}")

def scraper_carinski_most():
    """Očitava podatke s mjerne postaje jednom u 10 minuta."""
    global zadnji_podaci
    trenutno_vrijeme = time.time()
    
    # Ako nije prošlo 10 min (600 sekundi), koristi spremljeno
    if trenutno_vrijeme - zadnji_podaci["vrijeme_zadnjeg_citanja"] < 600:
        return zadnji_podaci["v"], zadnji_podaci["t"]

    print("[WEB] Očitavam svježe podatke s Carinskog mosta...")
    url = "https://avpjm.jadran.ba/vodomjerne_stanice/1/Mostar"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        r = requests.get(url, headers=headers, timeout=15, verify=False)
        html = r.text
        # Tražimo vodostaj i trend pomoću fleksibilnog pretraživanja
        v_match = re.search(r"vodostaj[^\d]*(\d+)", html, re.IGNORECASE)
        t_match = re.search(r"Trend[^\d]*([+-]?\d+)", html, re.IGNORECASE)
        
        if v_match:
            zadnji_podaci["v"] = float(v_match.group(1))
            zadnji_podaci["t"] = float(t_match.group(1)) if t_match else 0.0
            zadnji_podaci["vrijeme_zadnjeg_citanja"] = trenutno_vrijeme
            print(f"[USPJEH] Novo očitavanje: {zadnji_podaci['v']} cm")
    except Exception as e:
        print(f"[GREŠKA] Veza s web stranicom nije uspjela. Koristim zadnje stanje.")
    
    return zadnji_podaci["v"], zadnji_podaci["t"]

def procjena_protoka_q(h, t):
    """Izračun protoka na temelju vodostaja (409cm ~ 181m3/s)"""
    # Aproksimacija: na 400 cm protok je cca 180 m3/s, svaki cm nosi 1.8 m3/s
    q_bazni = 180.0 + (h - 400.0) * 1.8
    # Korekcija za brzinu rasta/pada (Trend)
    q_korigiran = q_bazni + (t * 1.5)
    return max(0, q_korigiran)

@app.route('/predict_autonomo')
def predict():
    try:
        v_live, t_live = scraper_carinski_most()
        
        # 1. Izračun dotoka
        q_ukupno = procjena_protoka_q(v_live, t_live)
        
        # 2. Provjera Alarma i Statusa
        status_msg = "CIVILNA ZAŠTITA: STANJE REDOVITO"
        alarm_type = "normal"
        
        # Provjera biološkog minimuma
        if q_ukupno < BIOLOSKI_MINIMUM:
            status_msg = "ALARM: BIOLOŠKI MINIMUM UGROŽEN!"
            alarm_type = "critical"
            
        # Provjera Vodne dozvole (+- 2 metra od 430 cm)
        if abs(v_live - NORMALNI_VODOSTAJ) > GRANICA_DOZVOLE:
            status_msg = "ALARM: IZVAN VODNE DOZVOLE (ODSTUPANJE > 2m)!"
            alarm_type = "critical"

        # 3. AI PROGNOZA (P) - KALIBRIRANA
        p_vrijednost = 0.0
        if model and scaler:
            # Pretvaranje u nadmorsku visinu za AI ulaz
            h_mnm_trenutna = KOTA_NULA + (v_live / 100)
            
            # Priprema parametara za AI: Dotok, Kota jezera, KG, KS, Preljevi, Kiša
            input_features = [q_ukupno, 78.5, 0, 0, 0.0, 0.0]
            skalirano = scaler.transform([input_features])
            h_mnm_pred = model.predict(skalirano)[0]
            
            # Razlika predviđene i trenutne razine u centimetrima
            p_sirova = (h_mnm_pred - h_mnm_trenutna) * 100
            
            # Trend-limitator: Ako AI pretjera, osloni se na trend mjerne postaje
            if abs(p_sirova) > 15.0:
                p_vrijednost = round(t_live, 1)
            else:
                p_vrijednost = round(p_sirova, 1)

        return jsonify({
            'q': round(q_ukupno, 1),
            'v': v_live,
            'p': p_vrijednost,
            'b': BIOLOSKI_MINIMUM,
            'status': status_msg,
            'alarm': alarm_type
        })
    except Exception as e:
        print(f"Sistemska greška: {e}")
        return jsonify({'status': "GREŠKA", 'v': 409, 'q': 181, 'p': -10})

if __name__ == '__main__':
    # Pokretanje na portu 5000 (glavni server)
    app.run(debug=True, port=5000)