import pandas as pd
import io
import requests

def test_csv_table_generation():
    url = "https://www.football-data.co.uk/new/SWE.csv"
    
    print(f"Hämtar data från {url}...")
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        
        df = pd.read_csv(io.StringIO(response.text), encoding='latin-1')
        
        # Skriv ut kolumnnamnen för felsökning om det skiter sig igen
        print(f"Tillgängliga kolumner: {list(df.columns)}")
        
        df['Date'] = pd.to_datetime(df['Date'], dayfirst=True)
        df_2026 = df[df['Date'] >= '2026-01-01'].copy()
        
        if df_2026.empty:
            print("Hittade inga matcher för 2026.")
            return

        # Identifiera rätt kolumner för mål
        # De heter antingen FTHG/FTAG eller HG/AG
        h_col = 'HG' if 'HG' in df_2026.columns else 'FTHG'
        a_col = 'AG' if 'AG' in df_2026.columns else 'FTAG'

        print(f"Använder kolumner: {h_col} och {a_col}")

        stats = {}
        for _, row in df_2026.iterrows():
            h_team = row['Home']
            a_team = row['Away']
            
            # Hantera eventuella saknade värden (NaN)
            if pd.isna(row[h_col]) or pd.isna(row[a_col]):
                continue
                
            h_goals = int(row[h_col])
            a_goals = int(row[a_col])

            for team in [h_team, a_team]:
                if team not in stats:
                    stats[team] = {'P': 0, 'S': 0}
            
            stats[h_team]['S'] += 1
            stats[a_team]['S'] += 1

            if h_goals > a_goals:
                stats[h_team]['P'] += 3
            elif a_goals > h_goals:
                stats[a_team]['P'] += 3
            else:
                stats[h_team]['P'] += 1
                stats[a_team]['P'] += 1

        table = []
        for team, s in stats.items():
            ppg = s['P'] / s['S'] if s['S'] > 0 else 0.0
            table.append({'Lag': team, 'S': s['S'], 'P': s['P'], 'PPG': round(ppg, 2)})

        # Sortera på PPG (eftersom det är det vi primärt mäter)
        table = sorted(table, key=lambda x: x['PPG'], reverse=True)

        print("\n--- GENERERAD TABELL 2026 ---")
        for i, row in enumerate(table, 1):
            print(f"{i:<2}. {row['Lag']:<20} {row['S']}m {row['P']}p (PPG: {row['PPG']})")
        
        ppg_only = [r['PPG'] for r in table]
        print(f"\nPPG-lista (16 lag):")
        print(ppg_only[:16])

    except Exception as e:
        print(f"Ett fel uppstod: {e}")

if __name__ == "__main__":
    test_csv_table_generation()
