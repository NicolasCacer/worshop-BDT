# main.py
import os
import webbrowser
from urllib.parse import quote

from ETL import ETL
from dashboard import build_dashboard
from geo_map import build_geo_dashboard


def file_url(path: str) -> str:
    """Convierte una ruta local en un enlace file:// válido para el navegador."""
    abs_path = os.path.abspath(path)
    return "file:///" + quote(abs_path.replace(os.sep, "/"), safe=":/")


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

    dashboard_url = file_url("dashboard.html")
    geomap_url = file_url("geo_map.html")

    print("\n" + "=" * 60)
    print("  ✅ PIPELINE COMPLETADO")
    print("  📁 Archivos generados:")
    print("     · youtube_trending_global.csv")
    print("     · dashboard.html")
    print("     · geo_map.html")
    print("     · geo_map_inner.html")
    print("\n  🌐 Enlaces:")
    print(f"     · Dashboard: {dashboard_url}")
    print(f"     · Geo Map:   {geomap_url}")
    print("=" * 60)

    print("\n🌐 Abriendo archivos en el navegador...")
    webbrowser.open(dashboard_url)
    webbrowser.open(geomap_url)


if __name__ == "__main__":
    main()