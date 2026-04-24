import pandas as pd
import folium

# =========================================================================================
#      Coordenadas y nombres de países del dataset
# =========================================================================================

COUNTRY_COORDS = {
    'CA': {'lat': 56.1304,  'lon': -106.3468, 'name': 'Canada'},
    'DE': {'lat': 51.1657,  'lon': 10.4515,   'name': 'Germany'},
    'FR': {'lat': 46.2276,  'lon': 2.2137,    'name': 'France'},
    'GB': {'lat': 55.3781,  'lon': -3.4360,   'name': 'United Kingdom'},
    'IN': {'lat': 20.5937,  'lon': 78.9629,   'name': 'India'},
    'JP': {'lat': 36.2048,  'lon': 138.2529,  'name': 'Japan'},
    'KR': {'lat': 35.9078,  'lon': 127.7669,  'name': 'South Korea'},
    'MX': {'lat': 23.6345,  'lon': -102.5528, 'name': 'Mexico'},
    'RU': {'lat': 61.5240,  'lon': 105.3188,  'name': 'Russia'},
    'US': {'lat': 37.0902,  'lon': -95.7129,  'name': 'United States'},
}

# =========================================================================================
#      Cargar datos
# =========================================================================================

def load_data():
    df = pd.read_csv('youtube_trending_global.csv')
    return df

# =========================================================================================
#      Preparar datos por país
# =========================================================================================

def get_country_stats(df):
    stats = {}
    for country, group in df.groupby('country'):
        # Video más visto
        top_video_row = group.loc[group['views'].idxmax()]
        # Categoría más vista
        top_category = group.groupby('category')['views'].sum().idxmax()

        stats[country] = {
            'top_video_title': top_video_row['title'],
            'top_video_views': int(top_video_row['views']),
            'top_video_channel': top_video_row['channel_title'],
            'top_video_id': top_video_row['video_id'],
            'top_category': top_category,
        }
    return stats

# =========================================================================================
#      Construir mapa Folium
# =========================================================================================

def build_map(df, stats):
    # Mapa base centrado en el mundo
    m = folium.Map(
        location=[20, 0],
        zoom_start=2,
        tiles=None  # sin tiles por defecto, los agregamos manualmente
    )

    # Tile oscuro estilo CartoDB
    folium.TileLayer(
        tiles='https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
        attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/">CARTO</a>',
        name='Dark',
        max_zoom=19
    ).add_to(m)

    # Capas separadas para video y categoría
    layer_video = folium.FeatureGroup(name='📺 Video más visto', show=True)
    layer_category = folium.FeatureGroup(name='🎯 Categoría más vista', show=True)

    for country, info in stats.items():
        if country not in COUNTRY_COORDS:
            continue

        coords = COUNTRY_COORDS[country]
        lat, lon = coords['lat'], coords['lon']
        country_name = coords['name']
        views_fmt = f"{info['top_video_views']:,}"

        # --- Marcador: Video más visto ---
        popup_video = folium.Popup(
            f"""
            <div style="
                font-family: 'Segoe UI', sans-serif;
                min-width: 220px;
                max-width: 280px;
                background: #0D1421;
                color: #E8EDF5;
                border-radius: 8px;
                padding: 12px;
                border: 1px solid #1C2A3A;
            ">
                <div style="color:#FF3B30; font-size:10px; letter-spacing:2px; text-transform:uppercase; margin-bottom:6px;">
                    📺 VIDEO MÁS VISTO · {country_name}
                </div>
                <div style="font-size:13px; font-weight:bold; margin-bottom:8px; line-height:1.3; color:#E8EDF5;">
                    {info['top_video_title'][:60]}{'...' if len(info['top_video_title'])>60 else ''}
                </div>
                <div style="font-size:11px; color:#5A6A7E; margin-bottom:4px;">
                    🎙 {info['top_video_channel']}
                </div>
                <div style="font-size:12px; color:#0AF5B0; font-weight:bold;">
                    👁 {views_fmt} vistas
                </div>
                <div style="margin-top:8px;">
                    <a href="https://www.youtube.com/watch?v={info['top_video_id']}"
                       target="_blank"
                       style="
                           display:inline-block;
                           background:#FF3B30;
                           color:white;
                           padding:4px 10px;
                           border-radius:4px;
                           font-size:10px;
                           text-decoration:none;
                           letter-spacing:1px;
                       ">
                        ▶ VER EN YOUTUBE
                    </a>
                </div>
            </div>
            """,
            max_width=300
        )

        folium.CircleMarker(
            location=[lat, lon],
            radius=14,
            color='#FF3B30',
            fill=True,
            fill_color='#FF3B30',
            fill_opacity=0.85,
            weight=2,
            popup=popup_video,
            tooltip=folium.Tooltip(
                f"<b style='color:#FF3B30'>{country_name}</b><br>📺 {info['top_video_title'][:40]}...",
                sticky=True
            )
        ).add_to(layer_video)

        # --- Marcador: Categoría más vista ---
        popup_category = folium.Popup(
            f"""
            <div style="
                font-family: 'Segoe UI', sans-serif;
                min-width: 200px;
                background: #0D1421;
                color: #E8EDF5;
                border-radius: 8px;
                padding: 12px;
                border: 1px solid #1C2A3A;
            ">
                <div style="color:#0AF5B0; font-size:10px; letter-spacing:2px; text-transform:uppercase; margin-bottom:6px;">
                    🎯 CATEGORÍA MÁS VISTA · {country_name}
                </div>
                <div style="font-size:18px; font-weight:bold; color:#FFC200;">
                    {info['top_category']}
                </div>
            </div>
            """,
            max_width=250
        )

        folium.CircleMarker(
            location=[lat + 1.5, lon + 1.5],  # offset leve para no solapar
            radius=10,
            color='#0AF5B0',
            fill=True,
            fill_color='#0AF5B0',
            fill_opacity=0.85,
            weight=2,
            popup=popup_category,
            tooltip=folium.Tooltip(
                f"<b style='color:#0AF5B0'>{country_name}</b><br>🎯 {info['top_category']}",
                sticky=True
            )
        ).add_to(layer_category)

    layer_video.add_to(m)
    layer_category.add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)

    return m

# =========================================================================================
#      HTML wrapper con header
# =========================================================================================

def build_geo_dashboard():
    print("⏳ Cargando datos...")
    df = load_data()
    stats = get_country_stats(df)

    print("🗺 Construyendo mapa...")
    m = build_map(df, stats)
    map_html = m._repr_html_()

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YouTube Trending · Geo Map</title>
    <link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Mono:wght@400;500&family=DM+Sans:wght@400;600&display=swap" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            background: #080C14;
            color: #E8EDF5;
            font-family: 'DM Sans', sans-serif;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }}

        header {{
            padding: 1.2rem 2.5rem;
            border-bottom: 1px solid #1C2A3A;
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-shrink: 0;
            background: #0D1421;
        }}

        .header-left {{
            display: flex;
            align-items: baseline;
            gap: 1rem;
        }}

        .header-left h1 {{
            font-family: 'Bebas Neue', sans-serif;
            font-size: 2rem;
            letter-spacing: 4px;
            color: #E8EDF5;
        }}

        .header-left h1 span {{ color: #FF3B30; }}

        .header-left p {{
            font-family: 'DM Mono', monospace;
            font-size: 0.65rem;
            color: #5A6A7E;
            letter-spacing: 3px;
            text-transform: uppercase;
        }}

        .legend {{
            display: flex;
            gap: 1.5rem;
            align-items: center;
        }}

        .legend-item {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-family: 'DM Mono', monospace;
            font-size: 0.7rem;
            color: #5A6A7E;
            letter-spacing: 1px;
            text-transform: uppercase;
        }}

        .legend-dot {{
            width: 10px;
            height: 10px;
            border-radius: 50%;
            flex-shrink: 0;
        }}

        .map-container {{
            flex: 1;
            position: relative;
        }}

        .map-container iframe,
        .map-container > div {{
            width: 100% !important;
            height: 100% !important;
            position: absolute;
            inset: 0;
        }}
    </style>
</head>
<body>

<header>
    <div class="header-left">
        <h1>YOUTUBE <span>GEO</span> MAP</h1>
        <p>Video más visto · Categoría más vista · Por país</p>
    </div>
    <div class="legend">
        <div class="legend-item">
            <div class="legend-dot" style="background:#FF3B30"></div>
            Video más visto
        </div>
        <div class="legend-item">
            <div class="legend-dot" style="background:#0AF5B0"></div>
            Categoría más vista
        </div>
        <div class="legend-item" style="color:#5A6A7E; font-size:0.6rem;">
            Clic en marcador para detalles
        </div>
    </div>
</header>

<div class="map-container">
    {map_html}
</div>

</body>
</html>"""

    output_path = 'geo_map.html'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"✅ Mapa guardado en '{output_path}'")
    print("💡 Ábrelo en tu navegador para ver el mapa interactivo")

if __name__ == "__main__":
    build_geo_dashboard()