# EcoFlow AI - Sustav za monitoring i predikciju vodostaja Neretve

EcoFlow AI je aplikacija za praćenje i prognozu razine rijeke Neretve na lokaciji Carinski most u Mostaru. Sustav prikuplja podatke u realnom vremenu i koristi model strojnog učenja za predviđanje promjena vodostaja.

## Pregled sustava
Projekt se sastoji od tri glavna dijela:
1. Web scraper: Automatski prikuplja podatke s mjerne postaje Agencije svakih 10 minuta.
2. AI Model: Random Forest regresijski model koji predviđa razinu vode na temelju dotoka, stanja akumulacija i oborina.
3. Web sučelje: Prikaz podataka uživo i sustav alarma.

## Analiza podataka i razvoj modela
Svi koraci razvoja modela dokumentirani su u datoteci analiza_podataka.ipynb, što uključuje:
- Čišćenje i sinkronizaciju podataka iz he_mostar_final_dataset.csv.
- Skaliranje značajki korištenjem StandardScalera.
- Usporedbu performansi više modela (Linear Regression, Decision Tree, Random Forest, Gradient Boosting).
- Odabir Random Forest modela zbog visoke točnosti (R2 > 0.99).

## Sigurnosni alarmi
Sustav automatski prati i signalizira tri kritična stanja:
- Biološki minimum: Alarm ako protok padne ispod 50 m3/s.
- Vodna dozvola: Provjera odstupanja vodostaja unutar dozvoljenih +/- 2 metra.
- Civilna zaštita: Upozorenja kod opasnosti od poplava pri visokim razinama.

## Upute za pokretanje
1. Instalacija potrebnih biblioteka:
   pip install -r requirements.txt

2. Pokretanje Flask servera:
   python app.py

3. Pregled podataka:
   Otvoriti index.html u web pregledniku.

---
Autor: Antonio
Kolegij: Umjetna Inteligencija