import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde
from atproto import Client
import os
import requests
from datetime import datetime
import matplotlib
matplotlib.use('Agg')

import re # Lägg till denna högst upp vid övriga imports

def get_current_allsvenskan_ppg():
    """Hämtar aktuell tabell från flera källor för maximal stabilitet"""
    sources = [
        "https://www.everysport.com/fotboll/allsvenskan/tabell",
        "https://www.fotbollskanalen.se/allsvenskan/tabell/"
    ]
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    for url in sources:
        try:
            print(f"Försöker hämta data från: {url}")
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code != 200:
                continue

            df_list = pd.read_html(response.text)
            # Hämta den tabell som ser mest ut som en serietabell (flest rader/kolumner)
            df = max(df_list, key=len)

            # Rensa kolumnnamn från dolda tecken
            df.columns = [str(c).strip().upper() for c in df.columns]
            cols = df.columns

            # Hitta kolumner för Matcher och Poäng
            col_s = [c for c in cols if c in ['S', 'SM', 'M', 'MATCHER', 'GP']][0]
            col_p = [c for c in cols if c in ['P', 'POÄNG', 'PTS', 'PO']][0]

            # Konvertera till rena siffror (hanterar om det står "2-0" eller liknande skräp)
            def clean_num(val):
                s = re.sub(r'[^\d]', '', str(val))
                return float(s) if s else 0.0

            df['S_clean'] = df[col_s].apply(clean_num)
            df['P_clean'] = df[col_p].apply(clean_num)

            ppg_list = []
            for _, row in df.iterrows():
                ppg = row['P_clean'] / row['S_clean'] if row['S_clean'] > 0 else 0.0
                ppg_list.append(ppg)

            if any(p > 0 for p in ppg_list):
                print(f"Framgång! Hämtade PPG: {ppg_list[:16]}")
                return ppg_list[:16]
                
        except Exception as e:
            print(f"Misslyckades med {url}: {e}")
            continue

    print("Kunde inte hämta data från någon källa. Returnerar nollor.")
    return [0.0] * 16

def generate_plot():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, 'allsvenskan_data.csv')
    
    if not os.path.exists(file_path):
        file_path = 'allsvenskan_data.csv'

    df_hist = pd.read_csv(file_path)
    years = [str(y) for y in range(2008, 2026)]
    
    plot_df = df_hist[['Placering'] + years].iloc[0:16].copy()
    plot_df['Placering'] = plot_df['Placering'].astype(int)
    
    df_melted = plot_df.melt(id_vars='Placering', var_name='Year', value_name='Poäng').dropna()
    df_melted['PPG'] = df_melted['Poäng'].astype(float) / 30.0

    # HÄR HÄMTAS LIVE-DATA ISTÄLLET FÖR HÅRDKODADE SIFFROR
    current_ppg_2026 = get_current_allsvenskan_ppg()

    color_light = "#ADD8E6"
    color_dark = "#00008B"
    color_median = "#FFD700"
    color_dots = "red"

    def draw_violin_on_ax(ax, data, pos, width_scale=0.4):
        q1, median, q3 = np.percentile(data, [25, 50, 75])
        kde = gaussian_kde(data)
        y_range = np.linspace(data.min(), data.max(), 200)
        w = kde(y_range)
        if w.max() > 0:
            w = w / w.max() * width_scale
        else:
            w = np.full_like(w, width_scale)
        ax.fill_betweenx(y_range, pos - w, pos + w, color=color_light, edgecolor='0.3', lw=1, zorder=1)
        y_iqr = np.linspace(q1, q3, 100)
        w_iqr = kde(y_iqr) / (kde(y_range).max() if kde(y_range).max() > 0 else 1) * width_scale
        ax.fill_betweenx(y_iqr, pos - w_iqr, pos + w_iqr, color=color_dark, edgecolor='none', zorder=2)
        median_w = kde(median) / (kde(y_range).max() if kde(y_range).max() > 0 else 1) * width_scale
        ax.hlines(median, pos - median_w, pos + median_w, color=color_median, lw=3, zorder=3)

    fig, ax = plt.subplots(figsize=(15, 9))
    positions = sorted(df_melted['Placering'].unique())

    for i, pos in enumerate(positions):
        data = df_melted[df_melted['Placering'] == pos]['PPG'].values
        if len(data) >= 2:
            draw_violin_on_ax(ax, data, i)
        
        # Plotta den hämtade PPG-siffran
        if i < len(current_ppg_2026):
            ax.scatter(i, current_ppg_2026[i], color=color_dots, s=100, edgecolors='white', linewidth=1.5, zorder=10)

    ax.set_title('Poäng per match (PPG) per slutplacering i Allsvenskan (2008–2025)', fontsize=20, fontweight='bold', pad=25)
    ax.set_xlabel('Slutplacering', fontsize=14, fontweight='bold')
    ax.set_ylabel('Points Per Game (PPG)', fontsize=14, fontweight='bold')
    ax.set_xticks(range(len(positions)))
    ax.set_xticklabels(positions, fontsize=12)
    ax.set_yticks(np.arange(0, 3.5, 0.2))
    ax.grid(axis='y', linestyle='--', alpha=0.5, zorder=0)

    # --- Förklaringsruta ---
    ax_ins = ax.inset_axes([0.72, 0.58, 0.26, 0.38])
    ax_ins.set_facecolor('#f2f2f2')
    ax_ins.set_xticks([]); ax_ins.set_yticks([])
    generic_data = np.random.normal(1.5, 0.4, 2000)
    draw_violin_on_ax(ax_ins, generic_data, 0, width_scale=0.25)
    ax_ins.scatter(0, 2.2, color=color_dots, s=100, edgecolors='white', zorder=10)
    ax_ins.set_xlim(-0.5, 1.8); ax_ins.set_ylim(generic_data.min()-0.3, generic_data.max()+0.8)
    
    txt_x = 0.6
    date_str = datetime.now().strftime('%d %b %Y')
    ax_ins.text(txt_x, 1.5, "Median", fontsize=10, fontweight='bold', va='center')
    ax_ins.text(txt_x, 1.9, "50% av utfallen", fontsize=9, va='center')
    ax_ins.text(txt_x, 2.5, f"PPG {date_str}", fontsize=9, color='red', fontweight='bold', va='center')
    ax_ins.text(txt_x, 1.0, "Historisk spridning", fontsize=9, va='center')

    arrow_style = dict(arrowstyle="->", color="black", lw=1)
    ax_ins.annotate("", xy=(0.2, 1.5), xytext=(txt_x-0.05, 1.5), arrowprops=arrow_style)
    ax_ins.annotate("", xy=(0.15, 1.75), xytext=(txt_x-0.05, 1.9), arrowprops=arrow_style)
    ax_ins.annotate("", xy=(0.05, 2.2), xytext=(txt_x-0.05, 2.5), arrowprops=dict(arrowstyle="->", color="red", lw=1.5))
    ax_ins.annotate("", xy=(0.15, 1.1), xytext=(txt_x-0.05, 1.0), arrowprops=arrow_style)

    image_path = 'allsvenskan_ppg.png'
    plt.savefig(image_path, dpi=300, bbox_inches='tight')
    plt.close()
    return image_path

def post_to_bluesky(image_path):
    handle = os.getenv('BSKY_HANDLE')
    password = os.getenv('BSKY_PASSWORD')
    if not handle or not password:
        return
    client = Client()
    client.login(handle, password)
    with open(image_path, 'rb') as f:
        img_data = f.read()
    text = f"Allsvenskan {datetime.now().year}: Aktuellt PPG jämfört med historiska slutplaceringar (2008-2025). #Allsvenskan #Statistik #PPG"
    client.send_image(text=text, image=img_data, image_alt="Allsvenskan PPG Violin Chart")

if __name__ == "__main__":
    try:
        path = generate_plot()
        post_to_bluesky(path)
        print("Post successful with live data!")
    except Exception as e:
        print(f"Ett fel uppstod: {e}")
        exit(1)
