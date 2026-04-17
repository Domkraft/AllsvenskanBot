import pandas as pd
import io
import requests

def test_csv_table_generation():
    url = "https://www.football-data.co.uk/new/SWE.csv"
    
    # Allsvenskan 2026 (inkl. Degerfors och Örgryte)
    ALLSVENSKAN_TEAMS = [
        "AIK", "Brommapojkarna", "Degerfors", "Djurgarden", "Elfsborg", 
        "GAIS", "Goteborg", "Hacken", "Halmstad", "Hammarby", 
        "Kalmar", "Malmo FF", "Mjallby", "Sirius", "Vasteras SK", "Orgryte"
    ]

    print(f"Hämtar data från {url}...")
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        
        df = pd.read_csv(io.StringIO(response.text), encoding='latin-1')
        df['Date'] = pd.to_datetime(df['Date'], dayfirst=True)
        
        # Filtrera för 2026 och de 16 Allsvenska lagen
        df_2026 = df[(df['Date'] >= '2026-01-01') & 
                     (df['Home'].isin(ALLSVENSKAN_TEAMS))].copy()
        
        h_col, a_col = 'HG', 'AG'
        stats = {team: {'P': 0, 'S': 0, 'GM': 0, 'IM': 0} for team in ALLSVENSKAN_TEAMS}

        for _, row in df_2026.iterrows():
            h, a = row['Home'], row['Away']
            if pd.isna(row[h_col]) or h not in stats or a not in stats:
                continue
                
            hg, ag = int(row[h_col]), int(row[a_col])

            # Uppdatera statistik
            stats[h]['S'] += 1
            stats[a]['S'] += 1
            stats[h]['GM'] += hg
            stats[h]['IM'] += ag
            stats[a]['GM'] += ag
            stats[a]['IM'] += hg

            # Poäng
            if hg > ag:
                stats[h]['P'] += 3
            elif ag > hg:
                stats[a]['P'] += 3
            else:
                stats[h]['P'] += 1
                stats[a]['P'] += 1

        # Skapa tabell-lista med målskillnad (MS)
        table = []
        for team, s in stats.items():
            ms = s['GM'] - s['IM']
            ppg = s['P'] / s['S'] if s['S'] > 0 else 0.0
            table.append({
                'Lag': team,
                'S': s['S'],
                'P': s['P'],
                'MS': ms,
                'GM': s['GM'],
                'PPG': round(ppg, 2)
            })

        # Sortering: 1. Poäng, 2. Målskillnad, 3. Gjorda mål
        table = sorted(table, key=lambda x: (x['P'], x['MS'], x['GM']), reverse=True)

        print("\n--- GENERERAD TABELL 2026 (Verifiering av tie-breaks) ---")
        print(f"{'Plac':<5} {'Lag':<18} {'S':<3} {'P':<3} {'MS':<4} {'GM':<3} {'PPG':<5}")
        for i, row in enumerate(table, 1):
            print(f"{i:<5} {row['Lag']:<18} {row['S']:<3} {row['P']:<3} {row['MS']:<4} {row['GM']:<3} {row['PPG']:<5}")
        
        ppg_only = [r['PPG'] for r in table]
        print(f"\nPPG-lista för grafen (placering 1-16):")
        print(ppg_only)

    except Exception as e:
        print(f"Ett fel uppstod: {e}")

if __name__ == "__main__":
    test_csv_table_generation()
