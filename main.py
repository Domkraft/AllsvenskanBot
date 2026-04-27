import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde
from atproto import Client
import requests
import os
import re
from datetime import datetime
import matplotlib
matplotlib.use('Agg')

# Färgkonfiguration
COLOR_LIGHT = "#ADD8E6"
COLOR_DARK = "#00008B"
COLOR_MEDIAN = "#FFD700"
COLOR_DOTS = "red"

def get_current_allsvenskan_ppg():
    """Hämtar data från txtv.se/343 och returnerar PPG i tabellens befintliga ordning."""
    url = "https://txtv.se/343"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        res = requests.get(url, headers=headers, timeout=15)
        res.raise_for_status()
        
        import html
        text = html.unescape(res.text)
        # Byt ut HTML-taggar mot mellanslag för att undvika hopslagna tecken
        text = re.sub(r'<[^>]+>', ' ', text)
        
        # Regex för att identifiera text-tv:s tabellrad: 
        # Placering, Lagnamn, Spelade, V, O, F, Målskillnad, Poäng
        pattern = r"(?:[0-9]{1,2})\s+([A-Za-zÅÄÖåäöéÉ.\- ]+?)\s+(\d{1,2})\s+\d{1,2}\s+\d{1,2}\s+\d{1,2}\s+\d{1,3}-\d{1,3}\s+(\d{1,2})"
        matches = re.findall(pattern, text)
        
        if not matches or len(matches) < 16:
            print(f"Fel: Hittade endast {len(matches) if matches else 0} lag. Formatet kan ha ändrats.")
            return None
            
        ppg_list = []
        # Tabellen är redan strikt sorterad enligt Allsvenskans tie-breakers
        for match in matches[:16]:
            played = int(match[1])
            points = int(match[2])
            ppg = points / played if played > 0 else 0.0
            ppg_list.append(round(ppg, 2))
            
        return ppg_list
        
    except Exception as e:
        print(f"Fel vid datainsamling från txtv.se: {e}")
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
        
    ax.fill_betweenx(y_range, pos - w, pos + w, color=COLOR_LIGHT, edgecolor='0.3', lw=1, zorder=1)
    
    y_iqr = np.linspace(q1, q3, 100)
    w_iqr = kde(y_iqr) / (kde(y_range).max() if kde(y_range).max() > 0 else 1) * width_scale
    ax.fill_betweenx(y_iqr, pos - w_iqr, pos + w_iqr, color=COLOR_DARK, edgecolor='none', zorder=2)
    
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
        print(f"Fel: Hittade inga årskolumner i {file_path}.")
        return None
        
    plot_df = df_hist[['Placering'] + available_years].iloc[0:16].copy()
    
    df_melt = plot_df.melt(id_vars='Placering', var_name='Year', value_name='Poäng').dropna()
    df_melt['Poäng'] = pd.to_numeric(df_melt['Poäng'].astype(str).str.replace(',', '.'))
    df_melt['PPG'] = df_melt['Poäng'] / 30.0

    fig, ax = plt.subplots(figsize=(15, 9))
    
    for i in range(16):
        pos = i + 1
        data = df_melt[df_melt['Placering'] == pos]['PPG'].values
        if len(data) >= 2:
            draw_violin_on_ax(ax, data, i)
        
        if i < len(current_ppg):
            ax.scatter(i, current_ppg[i], color=COLOR_DOTS, s=120, edgecolors='white', linewidth=1.5, zorder=10, clip_on=False)

    ax.set_title('Poäng per match (PPG) per placering i Allsvenskan (2008–2025)', fontsize=20, fontweight='bold', pad=25)
    ax.set_xlabel('Tabellplacering', fontsize=14)
    ax.set_ylabel('Points Per Game (PPG)', fontsize=14)
    ax.set_xticks(range(16))
    ax.set_xticklabels(range(1, 17), fontsize=12)
    
    ax.set_ylim(0.2, 2.6)
    ax.set_yticks(np.arange(0.2, 2.7, 0.2))
    ax.grid(axis='y', linestyle='--', alpha=0.5, zorder=0)

    # --- Förklaringsruta (Inset) ---
    ax_ins = ax.inset_axes([0.74, 0.62, 0.25, 0.35])
    ax_ins.set_facecolor('#f2f2f2')
    ax_ins.set_xticks([])
    ax_ins.set_yticks([])

    generic_data = np.random.normal(1.5, 0.4, 2000)
    draw_violin_on_ax(ax_ins, generic_data, 0, width_scale=0.25)
    ax_ins.scatter(0, 2.2, color=COLOR_DOTS, s=120, edgecolors='white', zorder=10)

    ax_ins.set_xlim(-0.5, 1.8) 
    ax_ins.set_ylim(generic_data.min()-0.3, generic_data.max()+0.7)

    txt_x = 0.45
    ax_ins.text(txt_x, 1.5, "Median", fontsize=10, verticalalignment='center', fontweight='bold', color='black')
    ax_ins.text(txt_x, 1.9, "50% av säsongernas\nPPG-resultat", fontsize=9, verticalalignment='center', color='black')
    
    months_sv = ["januari", "februari", "mars", "april", "maj", "juni", "juli", "augusti", "september", "oktober", "november", "december"]
    now = datetime.now()
    datum_text = f"{now.day} {months_sv[now.month-1]} {now.year}"
    
    ax_ins.text(txt_x, 2.45, f"PPG den\n{datum_text}", fontsize=9, verticalalignment='center', color='red', fontweight='bold')
    ax_ins.text(txt_x, 1.0, "Hela spridningen\n(2008–2025)", fontsize=9, verticalalignment='center', color='black')

    arrow_props = dict(arrowstyle="->", color='black', lw=0.8)
    ax_ins.annotate('', xy=(0.2, 1.5), xytext=(0.40, 1.5), arrowprops=arrow_props) # Median
    ax_ins.annotate('', xy=(0.15, 1.75), xytext=(0.40, 1.9), arrowprops=arrow_props) # 50%
    ax_ins.annotate('', xy=(0.05, 2.2), xytext=(0.40, 2.45), arrowprops=dict(arrowstyle="->", color='red', lw=0.8, connectionstyle="arc3,rad=-0.1")) 
    ax_ins.annotate('', xy=(0.15, 1.1), xytext=(0.40, 1.0), arrowprops=arrow_props) # Spread

    img_path = 'allsvenskan_ppg_update.png'
    plt.savefig(img_path, dpi=300, bbox_inches='tight')
    plt.close()
    return img_path

from atproto import Client, client_utils # Importera client_utils

def post_to_bluesky(image_path):
    client = Client()
    client.login(os.environ['BSKY_HANDLE'], os.environ['BSKY_PASSWORD'])
    
    with open(image_path, 'rb') as f:
        img_data = f.read()
    
    # Skapa texten med "RichText" för att göra taggarna klickbara/sökbara
    # Vi lägger bara till de viktigaste taggarna för att undvika spamfilter
    text_builder = client_utils.TextBuilder()
    text_builder.text(f"Aktuell PPG i Allsvenskan 2026 (2008-2025). Uppdaterat {datetime.now().strftime('%Y-%m-%d')}.\n\n")
    text_builder.tag("#Allsvenskan", "Allsvenskan")
    text_builder.text(" ")
    text_builder.tag("#ifkgbg", "ifkgbg")
    text_builder.text(" ")
    text_builder.tag("#AIK", "AIK")
    text_builder.text(" ")
    text_builder.tag("#MFF", "MFF")
    text_builder.text(" ")
    text_builder.tag("#HIF", "HIF")
    text_builder.text(" ")
    text_builder.tag("#DIF", "DIF")
    text_builder.text(" ")
    text_builder.tag("#GAIS", "GAIS")
    text_builder.text(" ")
    text_builder.tag("#ÖIS", "ÖIS")    
    # Lägg till ett fåtal lag till om det behövs, men håll det kort.

    # Skicka bild med den "rika" texten
    client.send_image(
        text=text_builder, 
        image=img_data, 
        image_alt="Diagram över Allsvenskans PPG-statistik baserat på historik."
    )
    print("Postad till Bluesky med klickbara taggar!")

if __name__ == "__main__":
    ppg_results = get_current_allsvenskan_ppg()
    if ppg_results:
        path = generate_plot(ppg_results)
        if path:
            post_to_bluesky(path)
            print(f"Graf skapad och postad: {path}. PPG: {ppg_results}")
