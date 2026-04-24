import pandas as pd
import plotly.graph_objects as go
import numpy as np
from plotly.subplots import make_subplots

# =========================================================================================
#      Paleta y estilo global
# =========================================================================================

COLORS = {
    'bg':        '#080C14',
    'surface':   '#0D1421',
    'border':    '#1C2A3A',
    'accent':    '#FF3B30',
    'accent2':   '#0AF5B0',
    'accent3':   '#FFC200',
    'text':      '#E8EDF5',
    'muted':     '#5A6A7E',
    'positive':  '#00E5A0',
    'negative':  '#FF3B30',
    'neutral':   '#FFB800',
}

CHART_LAYOUT = dict(
    plot_bgcolor=COLORS['surface'],
    paper_bgcolor='rgba(0,0,0,0)',
    font=dict(family='DM Mono, monospace', color=COLORS['text'], size=14),
    title_font=dict(family='Bebas Neue, sans-serif', size=26, color=COLORS['text']),
    margin=dict(l=40, r=40, t=80, b=40),
    legend=dict(
        bgcolor='rgba(13,20,33,0.8)',
        bordercolor=COLORS['border'],
        borderwidth=1,
        font=dict(size=13)
    ),
)

AXIS_STYLE = dict(
    gridcolor=COLORS['border'],
    zerolinecolor=COLORS['border'],
    tickfont=dict(size=16),
    ticklabelposition="outside",
    ticklabelstandoff=10,
    automargin=True
)

CATEGORY_COLORS = [
    '#FF3B30', '#0AF5B0', '#FFC200', '#00A8FF', '#FF6B6B',
    '#7C5CBF', '#00D4FF', '#FF8C00', '#39FF14', '#FF1493',
    '#00FFFF', '#FFD700', '#FF69B4', '#32CD32', '#FF4500',
]

# =========================================================================================
#      Cargar datos
# =========================================================================================

def load_data():
    df = pd.read_csv('youtube_trending_global.csv')
    df['views_M']    = (df['views']    / 1_000_000).round(2)
    df['likes_M']    = (df['likes']    / 1_000_000).round(2)
    df['dislikes_M'] = (df['dislikes'] / 1_000_000).round(2)
    return df

# =========================================================================================
#      KPI cards (HTML puro)
# =========================================================================================

def kpi_cards(df):
    total_views    = df['views'].sum()
    total_likes    = df['likes'].sum()
    total_dislikes = df['dislikes'].sum()
    polarity       = total_likes - total_dislikes
    polarity_pct   = (polarity / (total_likes + total_dislikes) * 100) if (total_likes + total_dislikes) > 0 else 0
    top_video      = df.loc[df['views'].idxmax(), 'title']
    top_country    = df.groupby('country')['views'].sum().idxmax()

    def fmt(n):
        if n >= 1_000_000_000: return f"{n/1_000_000_000:.1f}B"
        if n >= 1_000_000:     return f"{n/1_000_000:.1f}M"
        if n >= 1_000:         return f"{n/1_000:.1f}K"
        return str(n)

    pol_color = COLORS['positive'] if polarity >= 0 else COLORS['negative']
    pol_icon  = "▲" if polarity >= 0 else "▼"

    return f"""
    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-label">VISTAS TOTALES</div>
            <div class="kpi-value" style="color:{COLORS['accent2']}">{fmt(total_views)}</div>
            <div class="kpi-sub">Top 100 videos globales</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">LIKES TOTALES</div>
            <div class="kpi-value" style="color:{COLORS['accent3']}">{fmt(total_likes)}</div>
            <div class="kpi-sub">Interacciones positivas</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">POLARIDAD GLOBAL</div>
            <div class="kpi-value" style="color:{pol_color}">{pol_icon} {polarity_pct:.1f}%</div>
            <div class="kpi-sub">Balance likes / dislikes</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">PAÍS DOMINANTE</div>
            <div class="kpi-value" style="color:{COLORS['accent']}">{top_country}</div>
            <div class="kpi-sub">Mayor volumen de vistas</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">VIDEO #1 GLOBAL</div>
            <div class="kpi-value kpi-title">{top_video[:60]}{'...' if len(top_video)>60 else ''}</div>
        </div>
    </div>
    """

# =========================================================================================
#      Gráfica 1: Videos más vistos por país
# =========================================================================================

def fig_top_videos_by_country(df):
    top = (
        df.sort_values('views', ascending=False)
        .groupby('country')
        .first()
        .reset_index()
    )
    top = top.sort_values('views', ascending=True)

    fig = go.Figure()
    unique_cats = top['category'].unique()
    color_map = {cat: CATEGORY_COLORS[i % len(CATEGORY_COLORS)] for i, cat in enumerate(unique_cats)}

    for _, row in top.iterrows():
        fig.add_trace(go.Bar(
            x=[row['views_M']],
            y=[row['country']],
            orientation='h',
            name=row['category'],
            marker=dict(color=color_map[row['category']], opacity=0.9, line=dict(width=0)),
            text=f"  {row['title'][:35]}{'...' if len(row['title'])>35 else ''}",
            textposition='inside',
            textfont=dict(size=12, color='white'),
            hovertemplate=(
                f"<b>{row['title']}</b><br>"
                f"País: {row['country']}<br>"
                f"Vistas: {row['views']:,}<br>"
                f"Categoría: {row['category']}<br>"
                f"Canal: {row['channel_title']}"
                "<extra></extra>"
            ),
            showlegend=False
        ))

    for cat, color in color_map.items():
        fig.add_trace(go.Bar(
            x=[None], y=[None],
            orientation='h',
            name=cat,
            marker_color=color,
            showlegend=True
        ))

    fig.update_layout(
        **CHART_LAYOUT,
        title='▶  VIDEO MÁS VISTO POR PAÍS',
        barmode='stack',
        height=540,
        xaxis=dict(**AXIS_STYLE, title='Vistas (Millones)'),
        yaxis=dict(**AXIS_STYLE, title=''),
        bargap=0.25,
    )
    return fig

# =========================================================================================
#      Gráfica 2: Categorías por país (heatmap)
# =========================================================================================

def fig_categories_by_country(df):
    pivot       = df.groupby(['country', 'category'])['views'].sum().reset_index()
    pivot_table = pivot.pivot(index='country', columns='category', values='views').fillna(0)
    pivot_M     = pivot_table / 1_000_000

    # Fijar escala de color en percentil 95 para que el outlier no aplaste el gradiente
    valores = pivot_M.values.flatten()

    z_real = pivot_M.values
    z_log = np.log1p(z_real)

    fig = go.Figure(data=go.Heatmap(
        z=z_log,
        x=pivot_M.columns.tolist(),
        y=pivot_M.index.tolist(),
        colorscale=[
            [0.0,  COLORS['surface']],
            [0.2,  '#1A2A4A'],
            [0.5,  '#0066CC'],
            [0.75, '#FF8C00'],
            [1.0,  COLORS['accent']],
        ],
        text=pivot_M.round(1).values,
        texttemplate='%{text}M',
        hovertemplate='País: %{y}<br>Categoría: %{x}<br>Vistas: %{text}M<extra></extra>',
        colorbar=dict(
            title=dict(text='Escala log<br>vistas', font=dict(size=13)),
            tickfont=dict(size=12),
            bgcolor=COLORS['surface'],
            bordercolor=COLORS['border'],
        )
    ))

    fig.update_layout(
        **CHART_LAYOUT,
        title='🗂  CATEGORÍAS POR PAÍS',
        height=540,
        xaxis=dict(**AXIS_STYLE, tickangle=-35),
        yaxis=dict(**AXIS_STYLE),
    )
    return fig

# =========================================================================================
#      Gráfica 3: Interacción por zona
# =========================================================================================

def fig_interaction_by_zone(df):
    agg = df.groupby('country').agg(
        views=('views', 'sum'),
        likes=('likes', 'sum'),
        dislikes=('dislikes', 'sum')
    ).reset_index()
    agg['polarity']   = agg['likes'] - agg['dislikes']
    agg['polarity_M'] = agg['polarity'] / 1_000_000
    agg['views_M']    = agg['views']    / 1_000_000
    agg['likes_M']    = agg['likes']    / 1_000_000
    agg['dislikes_M'] = agg['dislikes'] / 1_000_000
    agg = agg.sort_values('views_M', ascending=False)

    fig = make_subplots(
        rows=1, cols=2,
        column_widths=[0.62, 0.38],
        subplot_titles=['VISTAS · LIKES · DISLIKES POR ZONA', 'POLARIDAD NETA (Likes − Dislikes)'],
        horizontal_spacing=0.08
    )

    metrics = [
        ('views_M',    COLORS['accent2'], 'Vistas (M)'),
        ('likes_M',    COLORS['accent3'], 'Likes (M)'),
        ('dislikes_M', COLORS['accent'],  'Dislikes (M)'),
    ]

    for col_name, color, label in metrics:
        fig.add_trace(go.Bar(
            name=label,
            x=agg['country'],
            y=agg[col_name],
            marker=dict(color=color, opacity=0.85, line=dict(width=0)),
            hovertemplate=f'{label}: %{{y:.2f}}M<extra></extra>'
        ), row=1, col=1)

    pol_colors = [COLORS['positive'] if v >= 0 else COLORS['negative'] for v in agg['polarity_M']]
    fig.add_trace(go.Bar(
        name='Polaridad',
        x=agg['country'],
        y=agg['polarity_M'],
        marker=dict(color=pol_colors, opacity=0.9, line=dict(width=0)),
        hovertemplate='Polaridad: %{y:.2f}M<extra></extra>',
        showlegend=False
    ), row=1, col=2)

    fig.add_hline(y=0, line_dash='dot', line_color=COLORS['muted'], opacity=0.6, row=1, col=2)

    fig.update_layout(
        **CHART_LAYOUT,
        title='📡  GRADO DE INTERACCIÓN POR ZONA',
        barmode='group',
        height=520,
    )
    fig.update_xaxes(**AXIS_STYLE)
    fig.update_yaxes(**AXIS_STYLE)
    for ann in fig.layout.annotations:
        ann.font = dict(family='Bebas Neue, sans-serif', size=16, color=COLORS['muted'])

    return fig

# =========================================================================================
#      Gráfica 4: Interacción + polaridad por categoría
# =========================================================================================

def fig_interaction_by_category(df):
    agg = df.groupby('category').agg(
        views=('views', 'sum'),
        likes=('likes', 'sum'),
        dislikes=('dislikes', 'sum'),
        videos=('video_id', 'nunique')
    ).reset_index()
    agg['polarity']     = agg['likes'] - agg['dislikes']
    agg['polarity_pct'] = ((agg['polarity'] / (agg['likes'] + agg['dislikes'])) * 100).round(1)
    agg['views_M']      = agg['views'] / 1_000_000

    fig = make_subplots(
        rows=1, cols=2,
        column_widths=[0.40, 0.40],
        subplot_titles=['VISTAS POR CATEGORÍA', 'POLARIDAD % POR CATEGORÍA'],
        horizontal_spacing=0.15
    )

    agg_sorted = agg.sort_values('views_M', ascending=True)
    fig.add_trace(go.Bar(
        x=agg_sorted['views_M'],
        y=agg_sorted['category'],
        orientation='h',
        marker=dict(
            color=agg_sorted['views_M'],
            colorscale=[[0, '#1A2A4A'], [0.5, '#0066CC'], [1, COLORS['accent2']]],
            showscale=False,
            line=dict(width=0)
        ),
        hovertemplate='%{y}<br>Vistas: %{x:.1f}M<extra></extra>',
        showlegend=False
    ), row=1, col=1)

    agg_pol    = agg.sort_values('polarity_pct', ascending=True)
    pol_colors2 = [COLORS['positive'] if v >= 0 else COLORS['negative'] for v in agg_pol['polarity_pct']]
    fig.add_trace(go.Bar(
        x=agg_pol['polarity_pct'],
        y=agg_pol['category'],
        orientation='h',
        marker=dict(color=pol_colors2, opacity=0.9, line=dict(width=0)),
        text=[f"{v:+.1f}%" for v in agg_pol['polarity_pct']],
        textposition='auto',
        cliponaxis=False,
        textfont=dict(size=11),
        hovertemplate='%{y}<br>Polaridad: %{x:+.1f}%<extra></extra>',
        showlegend=False
    ), row=1, col=2)

    fig.add_vline(x=0, line_dash='dot', line_color=COLORS['muted'], opacity=0.6, row=1, col=2)

    fig.update_layout(
        **CHART_LAYOUT,
        title='🎯  INTERACCIÓN Y POLARIDAD POR CATEGORÍA',
        height=540,
    )
    fig.update_xaxes(**AXIS_STYLE)
    fig.update_yaxes(**AXIS_STYLE)
    for ann in fig.layout.annotations:
        ann.font = dict(family='Bebas Neue, sans-serif', size=16, color=COLORS['muted'])

    return fig

# =========================================================================================
#      Gráfica 5: Correlación trending_period vs views
# =========================================================================================

def fig_correlation(df):
    from scipy import stats

    # ── Agregar por video único para evitar solapamiento ──
    sample = (
        df.groupby('video_id').agg(
            trending_period=('trending_period', 'mean'),
            views=('views',          'max'),
            category=('category',    'first'),
            title=('title',          'first'),
        ).reset_index()
        .dropna()
    )
    sample = sample[sample['trending_period'] >= 0]
    sample['views_M'] = (sample['views'] / 1_000_000).round(2)

    n = len(sample)
    if n <= 5000:
        _, p_trending = stats.shapiro(sample['trending_period'])
        _, p_views    = stats.shapiro(sample['views'])
    else:
        _, p_trending = stats.normaltest(sample['trending_period'])
        _, p_views    = stats.normaltest(sample['views'])

    both_normal = p_trending > 0.05 and p_views > 0.05
    if both_normal:
        corr, p_value = stats.pearsonr(sample['trending_period'], sample['views'])
        method = "Pearson"
    else:
        corr, p_value = stats.spearmanr(sample['trending_period'], sample['views'])
        method = "Spearman"

    sig_text  = "significativa" if p_value < 0.05 else "no significativa"
    direction = "negativa" if corr < 0 else "positiva"

    unique_cats = sample['category'].unique()
    color_map   = {cat: CATEGORY_COLORS[i % len(CATEGORY_COLORS)] for i, cat in enumerate(unique_cats)}

    fig = go.Figure()

    for cat in unique_cats:
        sub = sample[sample['category'] == cat]
        fig.add_trace(go.Scatter(
            x=sub['trending_period'],
            y=sub['views_M'],
            mode='markers',
            name=cat,
            marker=dict(
                color=color_map[cat],
                size=11,           # más grande porque hay menos puntos
                opacity=0.85,      # más opaco porque no se solapan
                line=dict(width=1, color='rgba(255,255,255,0.3)')
            ),
            hovertemplate=(
                "<b>%{customdata}</b><br>"
                "Días hasta tendencia: %{x:.1f}<br>"
                "Vistas: %{y:.2f}M<br>"
                f"Categoría: {cat}"
                "<extra></extra>"
            ),
            customdata=sub['title'].str[:50]
        ))

    # Línea de tendencia
    slope, intercept, _, _, _ = stats.linregress(sample['trending_period'], sample['views_M'])
    x_line = pd.Series([sample['trending_period'].min(), sample['trending_period'].max()])
    y_line  = slope * x_line + intercept

    fig.add_trace(go.Scatter(
        x=x_line,
        y=y_line,
        mode='lines',
        name='Tendencia lineal',
        line=dict(color=COLORS['accent2'], dash='dash', width=2),  # más visible
        showlegend=True
    ))

    fig.add_annotation(
        x=0.98, y=0.97,
        xref='paper', yref='paper',
        xanchor='right', yanchor='top',
        text=(
            f"<b>Correlación {method}</b><br>"
            f"r = {corr:+.4f}<br>"
            f"p-value = {p_value:.4f}<br>"
            f"n = {n} videos únicos<br>"
            f"Correlación {direction} y {sig_text}"
        ),
        showarrow=False,
        font=dict(family='DM Mono, monospace', size=13, color=COLORS['accent2']),
        bgcolor=COLORS['surface'],
        bordercolor=COLORS['accent2'],
        borderwidth=1,
        borderpad=10,
        align='right'
    )

    fig.update_layout(
        **CHART_LAYOUT,
        title=f'📈  CORRELACIÓN TRENDING PERIOD vs VISTAS — Método: {method} · {n} videos únicos',
        height=540,
        xaxis=dict(**AXIS_STYLE, title='Días promedio hasta convertirse en tendencia'),
        yaxis=dict(**AXIS_STYLE, title='Vistas máximas (Millones)'),
    )
    return fig

# =========================================================================================
#      Ensamblar dashboard HTML
# =========================================================================================

def build_dashboard():
    print("⏳ Cargando datos...")
    df = load_data()
    print(f"✅ {len(df)} registros cargados · {df['country'].nunique()} países · {df['category'].nunique()} categorías")

    print("📊 Generando visualizaciones...")
    figs = [
        fig_top_videos_by_country(df),
        fig_categories_by_country(df),
        fig_interaction_by_zone(df),
        fig_interaction_by_category(df),
        fig_correlation(df),
    ]

    charts_html = []
    for i, fig in enumerate(figs):
        include_js = (i == 0)
        charts_html.append(fig.to_html(full_html=False, include_plotlyjs='cdn' if include_js else False))

    kpis = kpi_cards(df)

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YouTube Trending · Global Dashboard</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Mono:wght@300;400;500&family=DM+Sans:wght@300;400;600&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg:       {COLORS['bg']};
            --surface:  {COLORS['surface']};
            --border:   {COLORS['border']};
            --accent:   {COLORS['accent']};
            --accent2:  {COLORS['accent2']};
            --accent3:  {COLORS['accent3']};
            --text:     {COLORS['text']};
            --muted:    {COLORS['muted']};
        }}

        *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
        html {{ scroll-behavior: smooth; }}

        body {{
            background: var(--bg);
            color: var(--text);
            font-family: 'DM Sans', sans-serif;
            min-height: 100vh;
            overflow-x: hidden;
        }}

        body::before {{
            content: '';
            position: fixed;
            inset: 0;
            background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.04'/%3E%3C/svg%3E");
            pointer-events: none;
            z-index: 9999;
            opacity: 0.5;
        }}

        header {{
            position: relative;
            padding: 3rem 3rem 2rem;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: flex-end;
            justify-content: space-between;
            gap: 2rem;
            overflow: hidden;
        }}

        header::after {{
            content: '▶';
            position: absolute;
            right: -0.5rem;
            top: -1rem;
            font-size: 18rem;
            color: var(--accent);
            opacity: 0.03;
            line-height: 1;
            pointer-events: none;
            font-family: 'Bebas Neue', sans-serif;
        }}

        .header-left h1 {{
            font-family: 'Bebas Neue', sans-serif;
            font-size: clamp(3rem, 6vw, 5.5rem);
            letter-spacing: 4px;
            line-height: 0.9;
            color: var(--text);
        }}

        .header-left h1 span {{ color: var(--accent); }}

        .header-left p {{
            font-family: 'DM Mono', monospace;
            font-size: 0.82rem;
            color: var(--muted);
            letter-spacing: 3px;
            text-transform: uppercase;
            margin-top: 1rem;
        }}

        .header-right {{ display: flex; gap: 2rem; align-items: center; }}

        .stat-pill {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 4px;
            padding: 0.8rem 1.4rem;
            text-align: center;
        }}

        .stat-pill .pill-val {{
            font-family: 'Bebas Neue', sans-serif;
            font-size: 2rem;
            letter-spacing: 2px;
            color: var(--accent2);
            line-height: 1;
        }}

        .stat-pill .pill-label {{
            font-family: 'DM Mono', monospace;
            font-size: 0.68rem;
            color: var(--muted);
            letter-spacing: 2px;
            text-transform: uppercase;
            margin-top: 0.2rem;
        }}

        main {{
            padding: 2.5rem 3rem;
            display: flex;
            flex-direction: column;
            gap: 2.5rem;
        }}

        .section-label {{
            font-family: 'DM Mono', monospace;
            font-size: 0.72rem;
            letter-spacing: 4px;
            text-transform: uppercase;
            color: var(--muted);
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }}
        .section-label::after {{
            content: '';
            flex: 1;
            height: 1px;
            background: var(--border);
        }}

        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 1rem;
        }}

        .kpi-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 1.6rem 1.8rem;
            transition: border-color 0.2s, transform 0.2s;
            animation: fadeUp 0.5s ease both;
        }}

        .kpi-card:hover {{ border-color: var(--accent2); transform: translateY(-2px); }}

        .kpi-label {{
            font-family: 'DM Mono', monospace;
            font-size: 0.72rem;
            letter-spacing: 3px;
            text-transform: uppercase;
            color: var(--muted);
            margin-bottom: 0.6rem;
        }}

        .kpi-value {{
            font-family: 'Bebas Neue', sans-serif;
            font-size: 2.8rem;
            letter-spacing: 2px;
            line-height: 1;
        }}

        .kpi-title {{
            font-family: 'DM Sans', sans-serif;
            font-size: 1.1rem;
            font-weight: 600;
            letter-spacing: 0;
            line-height: 1.35;
        }}

        .kpi-sub {{
            font-family: 'DM Mono', monospace;
            font-size: 0.68rem;
            color: var(--muted);
            margin-top: 0.5rem;
        }}

        .chart-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 1rem;
            transition: border-color 0.3s;
            animation: fadeUp 0.6s ease both;
        }}

        .chart-card::before {{
            content: '';
            display: block;
            height: 2px;
            background: linear-gradient(90deg, var(--accent), transparent);
            margin-bottom: 0.75rem;
            border-radius: 1px;
        }}

        .chart-card.green::before {{ background: linear-gradient(90deg, var(--accent2), transparent); }}
        .chart-card.gold::before  {{ background: linear-gradient(90deg, var(--accent3), transparent); }}

        @keyframes fadeUp {{
            from {{ opacity: 0; transform: translateY(16px); }}
            to   {{ opacity: 1; transform: translateY(0); }}
        }}

        .kpi-card:nth-child(1) {{ animation-delay: 0.05s; }}
        .kpi-card:nth-child(2) {{ animation-delay: 0.10s; }}
        .kpi-card:nth-child(3) {{ animation-delay: 0.15s; }}
        .kpi-card:nth-child(4) {{ animation-delay: 0.20s; }}
        .kpi-card:nth-child(5) {{ animation-delay: 0.25s; }}

        footer {{
            border-top: 1px solid var(--border);
            padding: 1.5rem 3rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        footer p {{
            font-family: 'DM Mono', monospace;
            font-size: 0.72rem;
            color: var(--muted);
            letter-spacing: 2px;
            text-transform: uppercase;
        }}

        footer .dot {{
            width: 6px; height: 6px;
            background: var(--accent2);
            border-radius: 50%;
            animation: pulse 2s infinite;
        }}

        @keyframes pulse {{
            0%, 100% {{ opacity: 1; transform: scale(1); }}
            50%       {{ opacity: 0.4; transform: scale(0.7); }}
        }}
    </style>
</head>
<body>

<header>
    <div class="header-left">
        <h1>YOUTUBE<br><span>TRENDING</span></h1>
        <p>Global Intelligence Dashboard · Top 100 Videos · Multi-Country Analysis</p>
    </div>
    <div class="header-right">
        <div class="stat-pill">
            <div class="pill-val">{df['country'].nunique()}</div>
            <div class="pill-label">Países</div>
        </div>
        <div class="stat-pill">
            <div class="pill-val">100</div>
            <div class="pill-label">Videos</div>
        </div>
        <div class="stat-pill">
            <div class="pill-val">{df['category'].nunique()}</div>
            <div class="pill-label">Categorías</div>
        </div>
        <div class="stat-pill">
            <div class="pill-val">{len(df):,}</div>
            <div class="pill-label">Registros</div>
        </div>
    </div>
</header>

<main>

    <div>
        <div class="section-label">01 — Indicadores clave</div>
        {kpis}
    </div>

    <div>
        <div class="section-label">02 — Videos más vistos por país</div>
        <div class="chart-card">
            {charts_html[0]}
        </div>
    </div>

    <div>
        <div class="section-label">03 — Comparación de categorías por país</div>
        <div class="chart-card green">
            {charts_html[1]}
        </div>
    </div>

    <div>
        <div class="section-label">04 — Grado de interacción por zona</div>
        <div class="chart-card gold">
            {charts_html[2]}
        </div>
    </div>

    <div>
        <div class="section-label">05 — Interacción y polaridad por categoría</div>
        <div class="chart-card">
            {charts_html[3]}
        </div>
    </div>

    <div>
        <div class="section-label">06 — Correlación tiempo de tendencia vs vistas</div>
        <div class="chart-card green">
            {charts_html[4]}
        </div>
    </div>

</main>

<footer>
    <p>Fuente: Kaggle · datasnaek/youtube-new · Workshop Final Big Data</p>
    <div class="dot"></div>
    <p>Generado con Plotly · Python</p>
</footer>

</body>
</html>"""

    output_path = 'dashboard.html'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"✅ Dashboard guardado en '{output_path}'")
    print("💡 Ábrelo en tu navegador para ver el dashboard interactivo")

if __name__ == "__main__":
    build_dashboard()