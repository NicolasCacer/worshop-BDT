# main.py
import webbrowser
import os
from ETL import ETL
from dashboard import build_dashboard
from geo_map import build_geo_dashboard

def main():
    print("=" * 60)
    print("  YOUTUBE TRENDING · PIPELINE COMPLETO")
    print("=" * 60)

    # ── Parte I + III-a: ETL completo con carga a MongoDB ──
    print("\n🚀 [1/3] Ejecutando pipeline ETL...")
    etl = ETL()
    etl.run()

    # ── Parte II: Dashboard interactivo con Plotly ──
    print("\n📊 [2/3] Generando dashboard interactivo...")
    build_dashboard()

    # ── Parte III-b: Mapa georreferenciado con Folium ──
    print("\n🗺  [3/3] Generando mapa georreferenciado...")
    build_geo_dashboard()

    # ── Abrir archivos generados en el navegador ──
    dashboard_path = os.path.abspath('dashboard.html')
    geomap_path    = os.path.abspath('geo_map.html')

    print("\n" + "=" * 60)
    print("  ✅ PIPELINE COMPLETADO")
    print("  📁 Archivos generados:")
    print(f"     · youtube_trending_global.csv")
    print(f"     · {dashboard_path}")
    print(f"     · {geomap_path}")
    print("=" * 60)

    print("\n🌐 Abriendo archivos en el navegador...")
    webbrowser.open(f"file://{dashboard_path}")
    webbrowser.open(f"file://{geomap_path}")

if __name__ == "__main__":
    main()