import kaggle as kg # importar librería de Kaggle para descargar datasets
import pandas as pd # importar pandas para manipulación de datos
import os # importar os para manejo de archivos
from prefect import task, flow, get_run_logger # importar task y flow de Prefect para orquestar el proceso ETL
from functools import wraps # importar wraps para crear decoradores
import time # importar time para medir el tiempo de ejecución
from dotenv import load_dotenv # importar load_dotenv para cargar variables de entorno desde un archivo .env
import glob # importar glob para encontrar archivos con patrones específicos

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
            df = df[df['video_id'].str.len() == 11]  # los video_id de YouTube siempre tienen 11 caracteres
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
            
            dfs = [pd.read_csv(f, encoding='latin-1') for f in files]  # latin-1 por si hay caracteres especiales
            df = pd.concat(dfs, ignore_index=True)
            print(f"✅ Archivo generado con {len(df)} filas")
            return df
        except Exception as e:
            print(f"Error al concatenar los datos: {e}")
            raise

    # c) Sobre el dataset unificado, estandarizar (con apply y funciones lambda y con iterrows) el formato de fechas empleado para la fecha de carga del vídeo
    @timer
    def standardize_dates(self, df):
        try:
            df['trending_date'] = pd.to_datetime(df['trending_date'], format='%y.%d.%m')
            df['publish_time'] = pd.to_datetime(df['publish_time']).dt.tz_localize(None)  # elimina el timezone
            return df
        except Exception as e:
            print(f"Error al estandarizar las fechas: {e}")
            raise

    # d) Calcular en el dataset la duración del periodo entre la carga del vídeo y la fecha en la que se convirtió en tendencia.
    @timer
    def calculate_trending_period(self, df):
        try:
            df['trending_period'] = (df['trending_date'] - df['publish_time']).dt.days
            return df
        except Exception as e:
            print(f"Error al calcular el periodo de tendencia: {e}")
            raise

    # Orquestación del proceso ETL utilizando Prefect
    @flow(name="run", flow_run_name="ETL-YouTube")
    @timer
    def run(self):
        """Ejecuta el proceso ETL completo."""
        task(self.import_dataset, task_run_name="extract-kaggle", retries=3, retry_delay_seconds=5)()
        df = task(self.concatenate_data, task_run_name="concat-data", retries=2, retry_delay_seconds=3)()
        df = task(self.clean_data, task_run_name="clean-data", retries=2, retry_delay_seconds=3)(df)
        df = task(self.standardize_dates, task_run_name="standardize-dates", retries=2, retry_delay_seconds=3)(df)
        df = task(self.calculate_trending_period, task_run_name="calculate-trending-period", retries=2, retry_delay_seconds=3)(df)
        df.to_csv('youtube_trending_global.csv', index=False) # reescribir el archivo concatenado por versión limpia
    
if __name__ == "__main__":
    etl = ETL()
    etl.run()