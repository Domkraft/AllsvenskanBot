import pandas as pd
import io
import requests
from datetime import datetime

def test_csv_table_generation():
    url = "https://www.football-data.co.uk/new/SWE.csv"
    
    print(f"Hämtar data från {url}...")
    try:
        # 1. Hämta filen
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        
        # 2. Läs in med pandas (använder latin-1 för att hantera svenska tecken om de finns)
        df = pd.read_csv(io.StringIO(response.text), encoding='latin-1')
        
        # 3. Konvertera datum
        # football-data använder ofta formatet dd/mm/yyyy
        df['Date'] = pd.to_datetime(df['Date'], dayfirst=True)
        
        # 4. Filtrera för 2026
        df_2026 = df[df['Date'] >= '2026-01-01'].copy()
        
        if df_2026.empty:
            print("Hittade inga matcher för 2026 i filen ännu.")
            # Visar de senaste 5 matcherna i filen för att se vad som finns
            print("\nSenaste matcherna i filen totalt:")
            print(df.tail(5)[['Date', 'Home', 'Away', 'FTHG', 'FTAG']])
            return

        print(f"Hittade {len(df_2026)} spelade matcher för 2026.")
        
        # 5. Generera tabellen
        stats = {}

        for _, row in df_2026.iterrows():
            h_team = row['Home']
            a_team = row['Away']
            h_goals = row['FTHG']
            a_goals = row['FTAG']

            for team in [h_team, a_team]:
                if team not in stats:
                    stats[team] = {'P': 0, 'S': 0, 'V': 0, 'O': 0, 'F': 0}
            
            stats[h_team]['S'] += 1
            stats[a_team]['S'] += 1

            if h_goals > a_goals:
                stats[h_team]['P'] += 3
                stats[h_team]['V'] += 1
                stats[a_team]['F'] += 1
            elif a_goals > h_goals:
                stats[a_team]['P'] += 3
                stats[a_team]['V'] += 1
                stats[h_team]['F'] += 1
            else:
                stats[h_team]['P'] += 1
                stats[a_team]['P'] += 1
                stats[h_team]['O'] += 1
                stats[a_team]['O'] += 1

        # 6. Skapa lista och räkna ut PPG
        table = []
        for team, s in stats.items():
            ppg = s['P'] / s['S'] if s['S'] > 0 else 0.0
            table.append({
                'Lag': team,
                'S': s['S'],
                'P': s['P'],
                'PPG': round(ppg, 2)
            })

        # Sortera på Poäng (fallande)
        table = sorted(table, key=lambda x: x['P'], reverse=True)

        # 7. Skriv ut resultatet
        print("\n--- GENERERAD TABELL 2026 ---")
        print(f"{'Plac':<5} {'Lag':<20} {'S':<3} {'P':<3} {'PPG':<5}")
        for i, row in enumerate(table, 1):
            print(f"{i:<5} {row['Lag']:<20} {row['S']:<3} {row['P']:<3} {row['PPG']:<5}")
        
        ppg_only = [r['PPG'] for r in table]
        print(f"\nPPG-lista för grafen (16 lag):")
        print(ppg_only[:16])

    except Exception as e:
        print(f"Ett fel uppstod: {e}")

if __name__ == "__main__":
    test_csv_table_generation()
