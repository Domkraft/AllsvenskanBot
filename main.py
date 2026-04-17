import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde
from atproto import Client
import io
import requests
import os
from datetime import datetime
import matplotlib
matplotlib.use('Agg')

# Konfiguration för Allsvenskan 2026
ALLSVENSKAN_TEAMS = [
    "AIK", "Brommapojkarna", "Degerfors", "Djurgarden", "Elfsborg", 
    "GAIS", "Goteborg", "Hacken", "Halmstad", "Hammarby", 
    "Kalmar", "Malmo FF", "Mjallby", "Sirius", "Vasteras SK", "Orgryte"
]

def get_current_allsvenskan_ppg():
    """Hämtar data från football-data.co.uk och skapar en sorterad PPG-lista."""
    url = "https://www.football-data.co.uk/new/SWE.csv"
    try:
        res = requests.get(url, timeout=15)
        res.raise_for_status()
        df = pd.read_csv(io.StringIO(res.text), encoding='latin-1')
        df['Date'] = pd.to_datetime(df['Date'], dayfirst=True)
        
        # Filtrera för 2026 och rätt lag
        df_2026 = df[(df['Date'] >= '2026-01-01') & 
                     (df['Home'].isin(ALLSVENSKAN_TEAMS))].copy()
        
        h_col, a_col = 'HG', 'AG'
        stats = {team: {'P': 0, 'S': 0, 'GM': 0, 'IM': 0} for team in ALLSVENSKAN_TEAMS}

        for _, row in df_2026.iterrows():
            h, a = row['Home'], row['Away']
            if pd.isna(row[h_col]) or h not in stats or a not in stats:
                continue
            
            hg, ag = int(row[h_col]), int(row[a_col])
            stats[h]['S'] += 1
            stats[a]['S'] += 1
            stats[h]['GM'] += hg
            stats[h]['IM'] += ag
            stats[a]['GM'] += ag
            stats[a]['IM'] += hg
            
            if hg > ag: stats[h]['P'] += 3
            elif ag > hg: stats[a]['P'] += 3
            else:
                stats[h]['P'] += 1
                stats[a]['P'] += 1

        table = []
        for team, s in stats.items():
            ppg = s['P'] / s['S'] if s['S'] > 0 else 0.0
            ms = s['GM'] - s['IM']
            table.append({'ppg': ppg, 'p': s['P'], 'ms': ms, 'gm': s['GM']})

        # Sortering: Poäng -> Målskillnad -> Gjorda mål
        sorted_table = sorted(table, key=lambda x: (x['p'], x['ms'], x['gm']), reverse=True)
        return [round(t['ppg'], 2) for t in sorted_table]
        
    except Exception as e:
        print(f"Fel vid datainsamling: {e}")
        return None

def generate_plot(current_ppg):
    """Skapar violin-grafen baserat på historik och aktuell PPG."""
    if not current_ppg or len(current_ppg) < 16:
        print("Fel: PPG-listan är ofullständig.")
        return None

    # Läs historisk data med dynamisk sökväg
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, 'allsvenskan_data.csv')
    
    if not os.path.exists(file_path):
        print(f"Kritiskt fel: Hittade inte {file_path}")
        return None

    df_hist = pd.read_csv(file_path)
    
    # Skapa kolumnnamn för 2008-2025
    years = [str(y) for y in range(2008, 2026)]
    
    # Säkerställ att vi bara tar de kolumner som faktiskt finns i din CSV
    available_years = [y for y in years if y in df_hist.columns]
    
    if not available_years:
        print(f"Fel: Hittade inga årskolumner i {file_path}. Kolumner: {df_hist.columns}")
        return None
        
    plot_df = df_hist[['Placering'] + available_years].iloc[0:16].copy()
    
    df_melt = plot_df.melt(id_vars='Placering', var_name='Year', value_name='Poäng').dropna()
    df_melt['PPG'] = df_melt['Poäng'].astype(float) / 30.0

    fig, ax = plt.subplots(figsize=(15, 9))
    
    for i in range(16):
        pos = i + 1
        data = df_melt[df_melt['Placering'] == pos]['PPG'].values
        if len(data) >= 2:
            kde = gaussian_kde(data)
            y_range = np.linspace(data.min(), data.max(), 100)
            w = kde(y_range)
            w = w / w.max() * 0.4
            # Violin (Hela spridningen)
            ax.fill_betweenx(y_range, i - w, i + w, color="#ADD8E6", edgecolor='0.3', alpha=0.7, zorder=1)
            # Median (Gul linje)
            ax.hlines(np.median(data), i - 0.3, i + 0.3, color="#FFD700", lw=3, zorder=3)
        
        # Aktuell PPG 2026 (Röd prick)
        if i < len(current_ppg):
            ax.scatter(i, current_ppg[i], color='red', s=120, edgecolors='white', linewidth=1.5, zorder=10)

    ax.set_title(f"Allsvenskan 2026: PPG per Tabellplacering (vs 2008-2025)", fontsize=18, fontweight='bold', pad=20)
    ax.set_ylabel("Points Per Game (PPG)", fontsize=12)
    ax.set_xticks(range(16))
    ax.set_xticklabels(range(1, 17))
    ax.grid(axis='y', linestyle='--', alpha=0.4)
    
    img_path = 'allsvenskan_ppg_update.png'
    plt.savefig(img_path, dpi=300, bbox_inches='tight')
    plt.close()
    return img_path

def post_to_bluesky(image_path):
    """Postar bilden till Bluesky."""
    client = Client()
    # Uppdaterat till de exakta namnen på dina miljövariabler
    client.login(os.environ['BSKY_HANDLE'], os.environ['BSKY_PASSWORD'])
    
    with open(image_path, 'rb') as f:
        img_data = f.read()
    
    text = f"Aktuell PPG i Allsvenskan 2026 jämfört med slutplaceringarnas historik (2008-2025). Uppdaterat {datetime.now().strftime('%Y-%m-%d')}."
    client.send_image(text=text, image=img_data, image_alt="Allsvenskan PPG Chart")
    print("Postad till Bluesky!")
    
    text = f"Aktuell PPG i Allsvenskan 2026 jämfört med slutplaceringarnas historik (2008-2025). Uppdaterat {datetime.now().strftime('%Y-%m-%d')}."
    client.send_image(text=text, image=img_data, image_alt="Allsvenskan PPG Chart")
    print("Postad till Bluesky!")

if __name__ == "__main__":
    ppg_results = get_current_allsvenskan_ppg()
    if ppg_results:
        path = generate_plot(ppg_results)
        if path:
            post_to_bluesky(path)
            print(f"Graf skapad: {path}. PPG: {ppg_results}")
