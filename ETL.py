import kaggle as kg # importar librería de Kaggle para descargar datasets
import pandas as pd # importar pandas para manipulación de datos
import os # importar os para manejo de archivos
from prefect import task, flow, get_run_logger # importar task y flow de Prefect para orquestar el proceso ETL
from functools import wraps # importar wraps para crear decoradores
import time # importar time para medir el tiempo de ejecución
from dotenv import load_dotenv # importar load_dotenv para cargar variables de entorno desde un archivo .env
import glob # importar glob para encontrar archivos con patrones específicos
from pymongo import MongoClient # importar MongoClient para conectar con MongoDB
from scipy import stats # importar stats para pruebas estadísticas (normalidad y correlación)
import json # importar json para manejar archivos JSON (categorías de YouTube)

# =========================================================================================
#      Decorador para medir el tiempo de ejecución de las funciones
# =========================================================================================

def timer(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_run_logger()
        start = time.time()
        result = func(*args, **kwargs)
        logger.info(f"{func.__name__}: {time.time() - start:.2f}s")
        return result
    return wrapper

# =========================================================================================
#      ETL (Extract, Transform, Load) para descargar y preparar el dataset de YouTube
# =========================================================================================

class ETL:
    def __init__(self):
        """Inicializa la clase ETL y carga las variables de entorno."""
        load_dotenv()
        self.dataset = 'datasnaek/youtube-new'
        self.path = 'data'

    # Limpieza de datos: eliminar filas vacías, duplicadas y con formatos incorrectos
    @timer
    def clean_data(self, df):
        try:
            print(f"🔍 Filas antes de limpiar: {len(df)}")
            df = df.dropna(how='all') # Elimina filas completamente vacías
            df = df.dropna(subset=['video_id', 'trending_date', 'publish_time']) # Elimina filas donde las columnas clave son nulas
            df = df.drop_duplicates() # Elimina filas duplicadas
            df = df.reset_index(drop=True) # Resetea el índice después de limpiar
            print(f"✅ Filas después de limpiar: {len(df)}")
            return df
        except Exception as e:
            print(f"Error al limpiar los datos: {e}")
            raise

    # a) Descargar los datos de tendencias (archivos CSV) a una zona local de staging
    @timer
    def import_dataset(self):
        """Descarga el dataset de Kaggle utilizando la API de Kaggle."""
        try:
            kg.api.authenticate()
            kg.api.dataset_download_files(self.dataset, path=self.path, unzip=True)
        except Exception as e:
            print(f"Error al extraer datos de Kaggle: {e}")
            raise

    # b) Unificar los datos separados por los países del dataset a un solo dataset para los 100 vídeos más vistos a escala global
    @timer
    def concatenate_data(self):
        try:
            files = glob.glob(f'{self.path}/*.csv')
            print(f"📂 Archivos encontrados: {len(files)}")
            
            if not files:
                print("❌ No se encontraron archivos CSV")
                return
            
            dfs = []
            for f in files:
                df_temp = pd.read_csv(f, encoding='utf-8', encoding_errors='replace')
                df_temp['country'] = os.path.basename(f)[:2].upper()
                dfs.append(df_temp)

            df = pd.concat(dfs, ignore_index=True)
            print(f"✅ Datos concatenados: {len(df)} filas")

            # Top 100 videos globales por vistas
            top100_ids = (
                df.groupby('video_id')['views']
                .sum()
                .sort_values(ascending=False)
                .head(100)
                .index
            )
            df = df[df['video_id'].isin(top100_ids)]
            df = df.reset_index(drop=True)
            print(f"✅ Top 100 videos globales: {len(df)} filas, videos únicos: {df['video_id'].nunique()}")

            # ── Enriquecer con nombre de categoría desde JSON ──
            categories = {}
            for json_file in glob.glob(f'{self.path}/*_category_id.json'):
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for item in data['items']:
                        if item['snippet']['assignable']:
                            categories[int(item['id'])] = item['snippet']['title']

            df['category'] = df['category_id'].map(categories).fillna('Unknown')
            print(f"✅ Categorías mapeadas: {df['category'].nunique()} categorías únicas")
            print(f"   {df['category'].value_counts().to_dict()}")

            return df
        except Exception as e:
            print(f"Error al concatenar los datos: {e}")
            raise

    # c) Sobre el dataset unificado, estandarizar (con apply y funciones lambda y con iterrows) el formato de fechas empleado para la fecha de carga del vídeo
    @timer
    def standardize_dates(self, df):
        try:
            df['trending_date'] = df['trending_date'].apply(
                lambda x: pd.to_datetime(x, format='%y.%d.%m') + pd.Timedelta(hours=23, minutes=59, seconds=59)
            )
            publish_times = []
            for _, row in df.iterrows():
                ts = pd.to_datetime(row['publish_time'], format='ISO8601')
                if ts.tzinfo is not None:
                    ts = ts.tz_localize(None)
                publish_times.append(ts)
            df['publish_time'] = publish_times

            return df
        except Exception as e:
            print(f"Error al estandarizar las fechas: {e}")
            raise

    # d) Calcular en el dataset la duración del periodo entre la carga del vídeo y la fecha en la que se convirtió en tendencia.
    @timer
    def calculate_trending_period(self, df):
        try:
            diff = df['trending_date'] - df['publish_time']
            df['trending_period'] = (diff.dt.total_seconds() / 86400).clip(lower=0).round(2) # 86400 segundos en un día, clip para evitar valores negativos, round para limitar decimales
            print(f"Muestra trending_period:\n{df[['trending_date', 'publish_time', 'trending_period']].head()}")
            return df
        except Exception as e:
            print(f"Error al calcular el periodo de tendencia: {e}")
            raise
    
    # Parte 3 a): Llevar a MongoDB el dataset unificado resultante
    @timer
    def load_to_mongodb(self, df):
        try:
            mongo_uri = os.getenv('MONGO_URI')
            mongo_db  = os.getenv('MONGO_DB', 'youtube_trending')

            print(f"\n🔌 Conectando a MongoDB...")
            print(f"   URI: {mongo_uri[:30]}..." if mongo_uri and len(mongo_uri) > 30 else f"   URI: {mongo_uri}")
            print(f"   Base de datos: {mongo_db}")

            client = MongoClient(mongo_uri)
            client.admin.command('ping')
            print(f"   ✅ Conexión exitosa")

            db = client[mongo_db]
            collection = db['trending_videos']

            # Estado antes de insertar
            docs_antes = collection.count_documents({})
            print(f"\n📦 Colección 'trending_videos':")
            print(f"   Documentos existentes antes: {docs_antes}")
            print(f"   🗑  Limpiando colección...")
            collection.drop()
            print(f"   ✅ Colección limpiada")

            # Convertir fechas a string para evitar problemas de serialización
            df_mongo = df.copy()
            df_mongo['trending_date'] = df_mongo['trending_date'].astype(str)
            df_mongo['publish_time']  = df_mongo['publish_time'].astype(str)

            # Insertar registros como documentos
            records = df_mongo.to_dict(orient='records')
            print(f"\n📤 Insertando {len(records)} documentos...")
            result = collection.insert_many(records)
            print(f"   ✅ {len(result.inserted_ids)} documentos insertados")

            # Verificación post-inserción
            docs_despues = collection.count_documents({})
            print(f"   📊 Documentos en colección ahora: {docs_despues}")

            # Muestra de un documento insertado
            sample_doc = collection.find_one({}, {'_id': 0, 'title': 1, 'views': 1, 'country': 1, 'category': 1})
            print(f"\n🔍 Muestra de documento insertado:")
            for k, v in sample_doc.items():
                print(f"   {k}: {v}")

            # Resumen por país
            print(f"\n🌍 Documentos por país:")
            for country in sorted(df['country'].unique()):
                count = collection.count_documents({'country': country})
                print(f"   {country}: {count} documentos")

            client.close()
            print(f"\n🔒 Conexión cerrada")
            return len(result.inserted_ids)

        except Exception as e:
            print(f"Error al cargar datos en MongoDB: {e}")
            raise

    # Parte 3 c): Correlación entre trending_period y views
    @timer
    def calculate_correlation(self, df):
        try:
            sample = df[['trending_period', 'views']].dropna()

            # --- Verificar normalidad con Shapiro-Wilk ---
            # Si n > 5000 usar D'Agostino-Pearson (más robusto para muestras grandes)
            n = len(sample)
            if n <= 5000:
                _, p_trending = stats.shapiro(sample['trending_period'])
                _, p_views    = stats.shapiro(sample['views'])
                test_used = "Shapiro-Wilk"
            else:
                _, p_trending = stats.normaltest(sample['trending_period'])
                _, p_views    = stats.normaltest(sample['views'])
                test_used = "D'Agostino-Pearson"

            both_normal = p_trending > 0.05 and p_views > 0.05

            # --- Elegir método según normalidad ---
            if both_normal:
                corr, p_value = stats.pearsonr(sample['trending_period'], sample['views'])
                method = "Pearson"
                reason = "ambas variables siguen distribución normal"
            else:
                corr, p_value = stats.spearmanr(sample['trending_period'], sample['views'])
                method = "Spearman"
                reason = "al menos una variable no sigue distribución normal (sesgo típico en vistas)"

            # --- Log de resultados ---
            print(f"\n📊 TEST DE NORMALIDAD ({test_used}):")
            print(f"   trending_period → p={p_trending:.4f} {'✅ normal' if p_trending > 0.05 else '❌ no normal'}")
            print(f"   views           → p={p_views:.4f} {'✅ normal' if p_views > 0.05 else '❌ no normal'}")
            print(f"\n🔗 CORRELACIÓN ({method}) — {reason}:")
            print(f"   r = {corr:.4f} | p-value = {p_value:.4f}")
            print(f"   {'✅ Significativa' if p_value < 0.05 else '⚠️ No significativa'} (α=0.05)")

            # Guardar resultados para usarlos en la visualización
            self.correlation_results = {
                'method': method,
                'corr': round(corr, 4),
                'p_value': round(p_value, 4),
                'significant': p_value < 0.05,
                'n': n,
                'reason': reason,
                'test_used': test_used,
                'p_trending': round(p_trending, 4),
                'p_views': round(p_views, 4),
            }

            return df  # retorna df sin modificar para mantener compatibilidad con el pipeline

        except Exception as e:
            print(f"Error al calcular la correlación: {e}")
            raise

    # Orquestación del proceso ETL utilizando Prefect
    @flow(name="run", flow_run_name="ETL-YouTube")
    @timer
    def run(self):
        """Ejecuta el proceso ETL completo."""
        try:
            # task(self.import_dataset, task_run_name="extract-kaggle", retries=3, retry_delay_seconds=5)()
            df = task(self.concatenate_data, task_run_name="concat-data", retries=2, retry_delay_seconds=3)()
            df = task(self.clean_data, task_run_name="clean-data", retries=2, retry_delay_seconds=3)(df)
            df = task(self.standardize_dates, task_run_name="standardize-dates", retries=2, retry_delay_seconds=3)(df)
            df = task(self.calculate_trending_period, task_run_name="calculate-trending-period", retries=2, retry_delay_seconds=3)(df)
            df = task(self.calculate_correlation, task_run_name="calculate-correlation", retries=2, retry_delay_seconds=3)(df)
            df.to_csv('youtube_trending_global.csv', index=False) # reescribir el archivo concatenado por versión limpia
            print("✅ Proceso ETL completado. Archivo guardado como 'youtube_trending_global.csv'")
            # task(self.load_to_mongodb, task_run_name="load-mongodb", retries=2, retry_delay_seconds=5)(df)
        except Exception as e:
            print(f"Error en el proceso ETL: {e}")
            raise

if __name__ == "__main__":
    etl = ETL()
    etl.run()