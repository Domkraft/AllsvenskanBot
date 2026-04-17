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

# Färgkonfiguration
COLOR_LIGHT = "#ADD8E6"
COLOR_DARK = "#00008B"
COLOR_MEDIAN = "#FFD700"
COLOR_DOTS = "red"

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

def draw_violin_on_ax(ax, data, pos, width_scale=0.4):
    """Ritar en violin (spridning, 50% IQR, median) på angiven position."""
    q1, median, q3 = np.percentile(data, [25, 50, 75])
    kde = gaussian_kde(data)
    y_range = np.linspace(data.min(), data.max(), 200)
    w = kde(y_range)
    if w.max() > 0:
        w = w / w.max() * width_scale
    else:
        w = np.full_like(w, width_scale)
        
    # Hela spridningen (Ljusblå)
    ax.fill_betweenx(y_range, pos - w, pos + w, color=COLOR_LIGHT, edgecolor='0.3', lw=1, zorder=1)
    
    # 50% av utfallen (Mörkblå)
    y_iqr = np.linspace(q1, q3, 100)
    w_iqr = kde(y_iqr) / (kde(y_range).max() if kde(y_range).max() > 0 else 1) * width_scale
    ax.fill_betweenx(y_iqr, pos - w_iqr, pos + w_iqr, color=COLOR_DARK, edgecolor='none', zorder=2)
    
    # Median (Gul)
    median_w = kde(median) / (kde(y_range).max() if kde(y_range).max() > 0 else 1) * width_scale
    ax.hlines(median, pos - median_w, pos + median_w, color=COLOR_MEDIAN, lw=3, zorder=3)

def generate_plot(current_ppg):
    """Skapar violin-grafen baserat på historik och aktuell PPG."""
    if not current_ppg or len(current_ppg) < 16:
        print("Fel: PPG-listan är ofullständig.")
        return None

    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, 'allsvenskan_data.csv')
    
    if not os.path.exists(file_path):
        print(f"Kritiskt fel: Hittade inte {file_path}")
        return None

    df_hist = pd.read_csv(file_path)
    
    years = [str(y) for y in range(2008, 2026)]
    available_years = [y for y in years if y in df_hist.columns]
    
    if not available_years:
        print(f"Fel: Hittade inga årskolumner i {file_path}. Kolumner: {df_hist.columns}")
        return None
        
    plot_df = df_hist[['Placering'] + available_years].iloc[0:16].copy()
    df_melt = plot_df.melt(id_vars='Placering', var_name='Year', value_name='Poäng').dropna()
    df_melt['PPG'] = df_melt['Poäng'].astype(float) / 30.0

    fig, ax = plt.subplots(figsize=(15, 9))
    
    # Rita violiner för placering 1-16
    for i in range(16):
        pos = i + 1
        data = df_melt[df_melt['Placering'] == pos]['PPG'].values
        if len(data) >= 2:
            draw_violin_on_ax(ax, data, i)
        
        # Aktuell PPG 2026 (Röd prick)
        if i < len(current_ppg):
            ax.scatter(i, current_ppg[i], color=COLOR_DOTS, s=120, edgecolors='white', linewidth=1.5, zorder=10)

    # Titlar och axlar
    dagens_datum = datetime.now().strftime('%Y-%m-%d')
    ax.set_title('Poäng per match (PPG) per placering i Allsvenskan (2008–2025)', fontsize=20, fontweight='bold', pad=25)
    ax.set_xlabel('Tabellplacering', fontsize=14)
    ax.set_ylabel('Points Per Game (PPG)', fontsize=14)
    ax.set_xticks(range(16))
    ax.set_xticklabels(range(1, 17), fontsize=12)
    ax.set_yticks(np.arange(0, 3.5, 0.2))
    ax.grid(axis='y', linestyle='--', alpha=0.5, zorder=0)

    # --- Förklaringsruta (Inset) ---
    ax_ins = ax.inset_axes([0.72, 0.58, 0.26, 0.38])
    ax_ins.set_facecolor('#f2f2f2')
    ax_ins.set_xticks([])
    ax_ins.set_yticks([])

    # Generisk violin för rutan
    generic_data = np.random.normal(1.5, 0.4, 2000)
    draw_violin_on_ax(ax_ins, generic_data, 0, width_scale=0.25)
    ax_ins.scatter(0, 2.2, color=COLOR_DOTS, s=100, edgecolors='white', zorder=10)

    ax_ins.set_xlim(-0.5, 1.8) 
    ax_ins.set_ylim(generic_data.min()-0.3, generic_data.max()+0.7)

    # Textbeskrivningar inuti rutan
    txt_x = 0.5
    ax_ins.text(txt_x, 1.5, "Median", fontsize=10, verticalalignment='center', fontweight='bold', color='black')
    ax_ins.text(txt_x, 1.9, "50% av säsongernas\nPPG-resultat", fontsize=9, verticalalignment='center', color='black')
    
    # Använd dynamiskt datum i legend-texten
    datum_text = datetime.now().strftime('%-d %B %Y')
    ax_ins.text(txt_x, 2.45, f"PPG den\n{datum_text}", fontsize=9, verticalalignment='center', color='red', fontweight='bold')
    ax_ins.text(txt_x, 1.0, "Hela spridningen\n(2008–2025)", fontsize=9, verticalalignment='center', color='black')

    # Pips/Arrows inuti rutan
    arrow_props = dict(arrowstyle="->", color='black', lw=0.8)
    ax_ins.annotate('', xy=(0.2, 1.5), xytext=(0.45, 1.5), arrowprops=arrow_props) # Median
    ax_ins.annotate('', xy=(0.15, 1.75), xytext=(0.45, 1.9), arrowprops=arrow_props) # 50%
    ax_ins.annotate('', xy=(0.05, 2.2), xytext=(0.45, 2.45), arrowprops=dict(arrowstyle="->", color='red', lw=0.8, connectionstyle="arc3,rad=-0.1")) 
    ax_ins.annotate('', xy=(0.15, 1.1), xytext=(0.45, 1.0), arrowprops=arrow_props) # Spread

    img_path = 'allsvenskan_ppg_update.png'
    plt.savefig(img_path, dpi=300, bbox_inches='tight')
    plt.close()
    return img_path

def post_to_bluesky(image_path):
    """Postar bilden till Bluesky."""
    client = Client()
    client.login(os.environ['BSKY_HANDLE'], os.environ['BSKY_PASSWORD'])
    
    with open(image_path, 'rb') as f:
        img_data = f.read()
    
    dagens_datum = datetime.now().strftime('%Y-%m-%d')
    text = f"Aktuell PPG i Allsvenskan 2026 jämfört med slutplaceringarnas historik (2008-2025). Uppdaterat {dagens_datum}."
    client.send_image(text=text, image=img_data, image_alt="Allsvenskan PPG Chart")
    print("Postad till Bluesky!")

if __name__ == "__main__":
    ppg_results = get_current_allsvenskan_ppg()
    if ppg_results:
        path = generate_plot(ppg_results)
        if path:
            post_to_bluesky(path)
            print(f"Graf skapad och postad: {path}. PPG: {ppg_results}")
