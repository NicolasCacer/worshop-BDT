import pandas as pd
import folium
import math

# =========================================================================================
#      Coordenadas y nombres de países del dataset
# =========================================================================================

COUNTRY_COORDS = {
    'CA': {'lat': 56.1304,  'lon': -106.3468, 'name': 'Canadá'},
    'DE': {'lat': 51.1657,  'lon': 10.4515,   'name': 'Alemania'},
    'FR': {'lat': 46.2276,  'lon': 2.2137,    'name': 'Francia'},
    'GB': {'lat': 55.3781,  'lon': -3.4360,   'name': 'Reino Unido'},
    'IN': {'lat': 20.5937,  'lon': 78.9629,   'name': 'India'},
    'JP': {'lat': 36.2048,  'lon': 138.2529,  'name': 'Japón'},
    'KR': {'lat': 35.9078,  'lon': 127.7669,  'name': 'Corea del Sur'},
    'MX': {'lat': 23.6345,  'lon': -102.5528, 'name': 'México'},
    'RU': {'lat': 61.5240,  'lon': 105.3188,  'name': 'Rusia'},
    'US': {'lat': 37.0902,  'lon': -95.7129,  'name': 'Estados Unidos'},
}


# =========================================================================================
#      Cargar datos
# =========================================================================================

def load_data():
    return pd.read_csv('youtube_trending_global.csv')


# =========================================================================================
#      Utilidades
# =========================================================================================

def fmt_number(n):
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.1f}B"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(int(n))


def truncate(text, limit=75):
    text = str(text)
    return text[:limit] + "..." if len(text) > limit else text


# =========================================================================================
#      Preparar datos por país
# =========================================================================================

def get_country_stats(df):
    stats = {}

    for country, group in df.groupby('country'):
        top_video_row = group.loc[group['views'].idxmax()]
        top_category = group.groupby('category')['views'].sum().idxmax()

        total_views = group['views'].sum()
        total_likes = group['likes'].sum()
        total_dislikes = group['dislikes'].sum()

        polarity = total_likes - total_dislikes
        polarity_pct = (
            polarity / (total_likes + total_dislikes) * 100
            if (total_likes + total_dislikes) > 0 else 0
        )

        stats[country] = {
            'top_video_title': top_video_row['title'],
            'top_video_views': int(top_video_row['views']),
            'top_video_channel': top_video_row['channel_title'],
            'top_video_id': top_video_row['video_id'],
            'top_category': top_category,
            'total_views': int(total_views),
            'total_likes': int(total_likes),
            'total_dislikes': int(total_dislikes),
            'polarity': int(polarity),
            'polarity_pct': polarity_pct,
            'videos': group['video_id'].nunique(),
        }

    return stats


# =========================================================================================
#      Construir mapa Folium
# =========================================================================================

def build_map(stats):
    m = folium.Map(
        location=[25, 10],
        zoom_start=2,
        tiles=None
    )

    folium.TileLayer(
        tiles='https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
        attr='&copy; OpenStreetMap &copy; CARTO',
        name='Dark',
        max_zoom=19
    ).add_to(m)

    layer_main = folium.FeatureGroup(name='🌍 Resumen por país', show=True)

    max_views = max(info['total_views'] for info in stats.values())

    for country, info in stats.items():
        if country not in COUNTRY_COORDS:
            continue

        coords = COUNTRY_COORDS[country]
        lat = coords['lat']
        lon = coords['lon']
        country_name = coords['name']

        polarity_color = '#00E5A0' if info['polarity_pct'] >= 0 else '#FF3B30'
        polarity_label = 'Positiva' if info['polarity_pct'] >= 0 else 'Negativa'

        radius = 9 + 18 * math.sqrt(info['total_views'] / max_views)

        popup = folium.Popup(
            f"""
            <div style="
                font-family: 'Segoe UI', sans-serif;
                min-width: 280px;
                max-width: 340px;
                background: #0D1421;
                color: #E8EDF5;
                border-radius: 12px;
                padding: 15px;
                border: 1px solid #1C2A3A;
                box-shadow: 0 8px 24px rgba(0,0,0,0.35);
            ">
                <div style="
                    font-size: 18px;
                    font-weight: 700;
                    color: #E8EDF5;
                    margin-bottom: 4px;
                ">
                    🌍 {country_name}
                </div>

                <div style="
                    font-size: 10px;
                    color: #9BAABD;
                    letter-spacing: 2px;
                    text-transform: uppercase;
                    margin-bottom: 10px;
                ">
                    {info['videos']} videos únicos · {fmt_number(info['total_views'])} vistas totales
                </div>

                <hr style="border: none; border-top: 1px solid #1C2A3A; margin: 10px 0;">

                <div style="color:#FF3B30; font-size:10px; letter-spacing:2px; text-transform:uppercase;">
                    📺 Video más visto
                </div>
                <div style="font-size:13px; font-weight:600; line-height:1.35; margin:5px 0 6px;">
                    {truncate(info['top_video_title'], 80)}
                </div>
                <div style="font-size:11px; color:#9BAABD;">
                    🎙 {truncate(info['top_video_channel'], 45)}
                </div>
                <div style="font-size:12px; color:#00F5B8; font-weight:bold; margin-top:4px;">
                    👁 {fmt_number(info['top_video_views'])} vistas
                </div>

                <hr style="border: none; border-top: 1px solid #1C2A3A; margin: 10px 0;">

                <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
                    <div>
                        <div style="color:#00F5B8; font-size:10px; letter-spacing:1px; text-transform:uppercase;">
                            Categoría dominante
                        </div>
                        <div style="font-size:14px; font-weight:bold; color:#FFD166; margin-top:4px;">
                            {info['top_category']}
                        </div>
                    </div>

                    <div>
                        <div style="color:{polarity_color}; font-size:10px; letter-spacing:1px; text-transform:uppercase;">
                            Polaridad
                        </div>
                        <div style="font-size:18px; font-weight:bold; color:{polarity_color}; margin-top:2px;">
                            {info['polarity_pct']:+.1f}%
                        </div>
                        <div style="font-size:10px; color:#9BAABD;">
                            {polarity_label}
                        </div>
                    </div>
                </div>

                <div style="
                    margin-top: 12px;
                    padding: 9px;
                    border-radius: 8px;
                    background: rgba(255,255,255,0.04);
                    font-size: 11px;
                    line-height: 1.6;
                    color: #E8EDF5;
                ">
                    👍 Likes: {fmt_number(info['total_likes'])}<br>
                    👎 Dislikes: {fmt_number(info['total_dislikes'])}<br>
                    Fórmula polaridad: (likes − dislikes) / (likes + dislikes)
                </div>

                <div style="margin-top:12px;">
                    <a href="https://www.youtube.com/watch?v={info['top_video_id']}"
                       target="_blank"
                       style="
                           display:inline-block;
                           background:#FF3B30;
                           color:white;
                           padding:7px 12px;
                           border-radius:6px;
                           font-size:10px;
                           text-decoration:none;
                           letter-spacing:1px;
                           font-weight:bold;
                       ">
                        ▶ VER VIDEO TOP
                    </a>
                </div>
            </div>
            """,
            max_width=360
        )

        folium.CircleMarker(
            location=[lat, lon],
            radius=radius,
            color=polarity_color,
            fill=True,
            fill_color=polarity_color,
            fill_opacity=0.82,
            weight=2,
            popup=popup,
            tooltip=folium.Tooltip(
                f"""
                <b>{country_name}</b><br>
                👁 {fmt_number(info['total_views'])} vistas<br>
                🎯 {info['top_category']}<br>
                💬 Polaridad: {info['polarity_pct']:+.1f}%
                """,
                sticky=True
            )
        ).add_to(layer_main)

    layer_main.add_to(m)

    return m


# =========================================================================================
#      HTML wrapper con header
# =========================================================================================

def build_geo_dashboard():
    print("⏳ Cargando datos...")
    df = load_data()
    stats = get_country_stats(df)

    print("Países en CSV:", sorted(df['country'].unique()))
    print("Países con coordenadas:", sorted(COUNTRY_COORDS.keys()))
    print("Países sin coordenadas:", set(df['country'].unique()) - set(COUNTRY_COORDS.keys()))

    print("Construyendo mapa...")
    m = build_map(stats)
    m.save('geo_map_inner.html')
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YouTube Trending · Geo Map</title>

    <link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Mono:wght@400;500&family=DM+Sans:wght@400;600;700&display=swap" rel="stylesheet">

    <style>
    * {{
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }}

    html, body {{
        width: 100%;
        height: 100%;
        overflow: hidden;
    }}

    body {{
        background: #080C14;
        color: #E8EDF5;
        font-family: 'DM Sans', sans-serif;
        display: flex;
        flex-direction: column;
    }}

    header {{
        height: 74px;
        padding: 1.1rem 2.5rem;
        border-bottom: 1px solid #1C2A3A;
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-shrink: 0;
        background: linear-gradient(90deg, #0D1421, #101A2B);
        gap: 2rem;
        z-index: 9999;
        position: relative;
    }}

    .header-left {{
        display: flex;
        align-items: baseline;
        gap: 1rem;
        flex-wrap: wrap;
    }}

    .header-left h1 {{
        font-family: 'Bebas Neue', sans-serif;
        font-size: 2.1rem;
        letter-spacing: 4px;
        color: #E8EDF5;
    }}

    .header-left h1 span {{
        color: #FF3B30;
    }}

    .header-left p {{
        font-family: 'DM Mono', monospace;
        font-size: 0.68rem;
        color: #9BAABD;
        letter-spacing: 3px;
        text-transform: uppercase;
    }}

    .legend {{
        display: flex;
        gap: 1.2rem;
        align-items: center;
        flex-wrap: wrap;
    }}

    .legend-item {{
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-family: 'DM Mono', monospace;
        font-size: 0.68rem;
        color: #9BAABD;
        letter-spacing: 1px;
        text-transform: uppercase;
    }}

    .legend-dot {{
        width: 11px;
        height: 11px;
        border-radius: 50%;
        flex-shrink: 0;
    }}

    .map-container {{
        position: relative;
        flex: 1;
        overflow: hidden;
    }}

    .map-frame {{
        width: 100%;
        height: 100%;
        border: none;
        display: block;
    }}

    .note {{
        position: absolute;
        left: 18px;
        bottom: 18px;
        z-index: 9998;
        max-width: 420px;
        background: rgba(13,20,33,0.92);
        border: 1px solid #1C2A3A;
        color: #9BAABD;
        padding: 10px 13px;
        border-radius: 8px;
        font-family: 'DM Mono', monospace;
        font-size: 0.68rem;
        letter-spacing: 1px;
    }}
    </style>
</head>

<body>

<header>
    <div class="header-left">
        <h1>YOUTUBE <span>GEO</span> MAP</h1>
        <p>Resumen georreferenciado · Video · Categoría · Polaridad</p>
    </div>

    <div class="legend">
        <div class="legend-item">
            <div class="legend-dot" style="background:#00E5A0"></div>
            Polaridad positiva
        </div>

        <div class="legend-item">
            <div class="legend-dot" style="background:#FF3B30"></div>
            Polaridad negativa
        </div>

        <div class="legend-item">
            Tamaño = vistas totales
        </div>

        <div class="legend-item">
            Clic para detalles
        </div>
    </div>
</header>

<div class="map-container">
    <iframe src="geo_map_inner.html" class="map-frame"></iframe>

    <div class="note">
        Cada marcador resume un país. El color representa la polaridad del público y el tamaño indica el volumen total de vistas.
    </div>
</div>

</body>
</html>
"""

    with open('geo_map.html', 'w', encoding='utf-8') as f:
        f.write(html)

if __name__ == "__main__":
    build_geo_dashboard()