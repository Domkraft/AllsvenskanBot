import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde
from atproto import Client
import os
from datetime import datetime
import matplotlib
matplotlib.use('Agg') # Ser till att skriptet fungerar i molnet utan skärm

def generate_plot():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, 'allsvenskan_data.csv')
    
    if not os.path.exists(file_path):
        file_path = 'allsvenskan_data.csv'

    df = pd.read_csv(file_path)
    years = [str(y) for y in range(2008, 2026)]
    
    plot_df = df[['Placering'] + years].iloc[0:16].copy()
    plot_df['Placering'] = plot_df['Placering'].astype(int)
    
    df_melted = plot_df.melt(id_vars='Placering', var_name='Year', value_name='Poäng').dropna()
    df_melted['PPG'] = df_melted['Poäng'].astype(float) / 30.0

    # Aktuell PPG 2026 (Exempelvärden - uppdatera dessa löpande)
    current_ppg_2026 = [3.0, 3.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 1.5, 1.5, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0]

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
        ax.scatter(i, current_ppg_2026[i], color=color_dots, s=100, edgecolors='white', linewidth=1.5, zorder=10)

    ax.set_title('Poäng per match (PPG) per slutplacering i Allsvenskan (2008–2025)', fontsize=20, fontweight='bold', pad=25)
    ax.set_xlabel('Slutplacering', fontsize=14, fontweight='bold')
    ax.set_ylabel('Points Per Game (PPG)', fontsize=14, fontweight='bold')
    ax.set_xticks(range(len(positions)))
    ax.set_xticklabels(positions, fontsize=12)
    ax.set_yticks(np.arange(0, 3.5, 0.2))
    ax.grid(axis='y', linestyle='--', alpha=0.5, zorder=0)

    # --- Förklaringsruta (Inset) ---
    ax_ins = ax.inset_axes([0.72, 0.58, 0.26, 0.38])
    ax_ins.set_facecolor('#f2f2f2')
    ax_ins.set_xticks([]); ax_ins.set_yticks([])
    generic_data = np.random.normal(1.5, 0.4, 2000)
    draw_violin_on_ax(ax_ins, generic_data, 0, width_scale=0.25)
    ax_ins.scatter(0, 2.2, color=color_dots, s=100, edgecolors='white', zorder=10)
    ax_ins.set_xlim(-0.5, 1.8); ax_ins.set_ylim(generic_data.min()-0.3, generic_data.max()+0.8)
    
    txt_x = 0.6
    date_str = datetime.now().strftime('%d %b %Y')
    
    # Texter utan \n felet
    ax_ins.text(txt_x, 1.5, "Median", fontsize=10, fontweight='bold', va='center')
    ax_ins.text(txt_x, 1.9, "50% av utfallen", fontsize=9, va='center')
    ax_ins.text(txt_x, 2.5, f"PPG {date_str}", fontsize=9, color='red', fontweight='bold', va='center')
    ax_ins.text(txt_x, 1.0, "Historisk spridning", fontsize=9, va='center')

    # PILAR (Strecken som saknades)
    arrow_style = dict(arrowstyle="->", color="black", lw=1)
    ax_ins.annotate("", xy=(0.2, 1.5), xytext=(txt_x-0.05, 1.5), arrowprops=arrow_style) # Till median
    ax_ins.annotate("", xy=(0.15, 1.75), xytext=(txt_x-0.05, 1.9), arrowprops=arrow_style) # Till mörkblå
    ax_ins.annotate("", xy=(0.05, 2.2), xytext=(txt_x-0.05, 2.5), arrowprops=dict(arrowstyle="->", color="red", lw=1.5)) # Till röd prick
    ax_ins.annotate("", xy=(0.15, 1.1), xytext=(txt_x-0.05, 1.0), arrowprops=arrow_style) # Till ljusblå

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
    
    text = "Dagens Allsvenska PPG jämfört med historiska slutplaceringar (2008-2025). #Allsvenskan #Statistik  #aik #bkhäcken #bpfotboll #djurgården #dif #degerforsif #elfsborg #gais #halmstadsbk #hammarby #ifkgbg #iksirius #malmöff #mjällbyaif #öis #kff #vsk"
    client.send_image(text=text, image=img_data, image_alt="Allsvenskan PPG Violin Chart")

if __name__ == "__main__":
    try:
        path = generate_plot()
        post_to_bluesky(path)
        print("Post successful!")
    except Exception as e:
        print(f"Ett fel uppstod: {e}")
        exit(1)
