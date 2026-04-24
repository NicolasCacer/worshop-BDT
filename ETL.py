from pathlib import Path        # Manejo moderno de rutas y archivos (crear carpetas, paths, etc.)
import shutil                   # Utilidades de sistema de archivos (ej: espacio en disco)
from typing import Callable     # Tipado para funciones (usado en decoradores como timer)
import kaggle as kg             # API de Kaggle para descargar datasets automáticamente
import pandas as pd             # Manipulación y análisis de datos (DataFrames)
import os                       # Operaciones del sistema operativo (rutas, permisos, etc.)
from functools import wraps     # Preserva metadata en decoradores personalizados
import time                     # Medición de tiempos de ejecución
from dotenv import load_dotenv  # Carga variables de entorno desde archivo .env
import glob                     # Búsqueda de archivos por patrones (ej: *.csv, *.json)
from pymongo import MongoClient # Conexión y operaciones con MongoDB
from scipy import stats         # Métodos estadísticos (normalidad, correlación)
import json                     # Lectura de archivos JSON (categorías de YouTube)
from prefect import task, flow, get_run_logger  
# Prefect:
# - task → convierte funciones en tareas del pipeline
# - flow → define el flujo ETL
# - get_run_logger → logging integrado con Prefect


# =========================================================================================
#      Utilidades de logging (mejoran la lectura del flujo en Prefect)
# =========================================================================================

def log_section(title: str) -> None:
    """
    Imprime un encabezado visual para separar secciones del pipeline.
    Se usa para dividir el flujo ETL en bloques claros (Extracción, Transformación, etc.),
    facilitando la lectura en consola y en logs de Prefect.
    """
    print("\n" + "=" * 75)   # Línea superior decorativa
    print(f" {title}")       # Título de la sección
    print("=" * 75)          # Línea inferior decorativa


def log_step(message: str) -> None:
    """
    Imprime un paso intermedio dentro de una sección.
    Se usa para describir acciones en curso (lectura de archivos, transformaciones, etc.).
    """
    print(f"   → {message}")


def log_success(message: str) -> None:
    """
    Imprime un mensaje de éxito.
    Se utiliza cuando una operación finaliza correctamente.
    """
    print(f"   ✅ {message}")


def log_warning(message: str) -> None:
    """
    Imprime una advertencia.
    Se usa para indicar situaciones no críticas (ej: archivos faltantes, valores inesperados).
    """
    print(f"   ⚠️ {message}")


def log_error(message: str) -> None:
    """
    Imprime un mensaje de error.
    Se usa antes de lanzar una excepción o cuando ocurre un fallo en el pipeline.
    """
    print(f"   ❌ {message}")


# =========================================================================================
# Decorador para medir el tiempo de ejecución de funciones/tareas
# =========================================================================================

def timer(func: Callable) -> Callable:
    """
    Decorador que mide y registra el tiempo de ejecución de una función.
    Se integra con el logger de Prefect para monitorear el rendimiento del pipeline ETL.
    Parámetros:
    ----------
    func : Callable
        Función que será envuelta por el decorador.
    Retorna:
    -------
    Callable
        Función modificada que incluye medición de tiempo.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        """Ejecuta la función original, mide su duración y la registra en Prefect."""
        logger = get_run_logger()  # Logger de Prefect
        start = time.time()        # Tiempo inicial
        result = func(*args, **kwargs)  # Ejecución de la función
        elapsed = time.time() - start   # Tiempo total
        logger.info(f"Task {func.__name__}: {elapsed:.2f}s")  # Log en Prefect
        return result  # Retorna resultado original
    return wrapper


# =========================================================================================
#      Utilidades de sistema de archivos
# =========================================================================================

def get_absolute_path(file_name: str) -> str:
    """Devuelve la ruta absoluta de un archivo."""
    return os.path.abspath(file_name)


def file_permissions(absolute_path: str) -> tuple:
    """Verifica permisos de lectura y escritura sobre un archivo."""
    return os.access(absolute_path, os.R_OK), os.access(absolute_path, os.W_OK)


def get_file_size(absolute_path: str) -> int:
    """Obtiene el tamaño de un archivo en bytes."""
    return os.path.getsize(absolute_path)


def disk_space_check(path: str = "/") -> tuple:
    """Consulta el espacio total, usado y libre del disco."""
    return shutil.disk_usage(path)


def bytes_to_human_readable(num_bytes: int) -> str:
    """Convierte bytes a una unidad más legible: KB, MB, GB, etc."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if num_bytes < 1024:
            return f"{num_bytes:.2f} {unit}"
        num_bytes /= 1024

    return f"{num_bytes:.2f} PB"


@task(retries=3, name="00 - filesystem_diagnostics")
@timer
def filesystem_diagnostics(min_required_bytes: int = 1 * 1024**3) -> None:
    """Verifica el espacio en disco y lanza error si no es suficiente."""

    log_section("DIAGNÓSTICO · Sistema de archivos")

    total, used, free = disk_space_check()

    log_step(f"Espacio total: {bytes_to_human_readable(total)}")
    log_step(f"Espacio usado: {bytes_to_human_readable(used)}")
    log_step(f"Espacio libre: {bytes_to_human_readable(free)}")
    if free < min_required_bytes:
        log_error("Espacio en disco insuficiente para ejecutar el pipeline")

        raise RuntimeError(
            f"Espacio insuficiente: {bytes_to_human_readable(free)} disponibles, "
            f"se requieren al menos {bytes_to_human_readable(min_required_bytes)}"
        )

    log_success("Espacio en disco suficiente")

@task(retries=3, name="07 - check_csv_file")
@timer
def check_csv_file() -> None:
    """Verifica ubicación, permisos y tamaño del CSV final generado."""
    log_section("VALIDACIÓN · Archivo CSV final")

    path = get_absolute_path("youtube_trending_global.csv")

    if not os.path.exists(path):
        log_error(f"No se encontró el archivo final en: {path}")
        return

    can_read, can_write = file_permissions(path)
    file_size = get_file_size(path)

    log_step(f"Ruta absoluta: {path}")
    log_step(f"Permiso de lectura: {can_read}")
    log_step(f"Permiso de escritura: {can_write}")
    log_step(f"Tamaño del archivo: {bytes_to_human_readable(file_size)}")

    log_success("Archivo CSV final verificado correctamente")


# =========================================================================================
#      ETL principal para el dataset YouTube Trending
# =========================================================================================

class ETL:
    """
    Pipeline ETL para el dataset de YouTube Trending.

    Flujo general:
    1. Descargar datos desde Kaggle.
    2. Unificar CSV por país.
    3. Limpiar registros inválidos o duplicados.
    4. Estandarizar fechas.
    5. Calcular periodo hasta tendencia.
    6. Calcular correlación entre periodo de tendencia y vistas.
    7. Exportar CSV final.
    8. Opcionalmente cargar datos a MongoDB.
    """

    def __init__(self):
        """Inicializa configuración base del pipeline."""
        load_dotenv()

        self.dataset = "datasnaek/youtube-new"
        self.path = "data"
        self.output_file = "youtube_trending_global.csv"

    # =====================================================================================
    #      Extracción
    # =====================================================================================

    @task(retries=3, name="01 - import_dataset")
    @timer
    def import_dataset(self):
        """Descarga el dataset desde Kaggle hacia una carpeta local de staging."""
        try:
            log_section("EXTRACCIÓN · Descarga del dataset desde Kaggle")

            log_step(f"Dataset origen: {self.dataset}")
            log_step(f"Carpeta local de staging: {self.path}")

            Path(self.path).mkdir(parents=True, exist_ok=True)
            log_success("Carpeta de staging verificada o creada")

            kg.api.authenticate()
            log_success("Autenticación con Kaggle completada")

            log_step("Descargando y descomprimiendo archivos...")
            kg.api.dataset_download_files(
                self.dataset,
                path=self.path,
                unzip=True
            )

            log_success(f"Dataset descargado correctamente en: {self.path}")

        except Exception as e:
            log_error(f"Error al extraer datos desde Kaggle: {e}")
            raise

    # =====================================================================================
    #      Transformación
    # =====================================================================================

    @task(retries=3, name="02 - concatenate_data")
    @timer
    def concatenate_data(self):
        """
        Une los CSV por país, agrega la columna country,
        filtra los 100 videos más vistos a nivel global
        y mapea las categorías desde archivos JSON.
        """
        try:
            log_section("TRANSFORMACIÓN · Unificación de archivos por país")

            files = glob.glob(f"{self.path}/*.csv")
            log_step(f"Archivos CSV encontrados: {len(files)}")

            if not files:
                log_warning("No se encontraron archivos CSV en la carpeta de staging")
                return None

            dfs = []

            for file_path in files:
                file_name = os.path.basename(file_path)
                country = file_name[:2].upper()

                log_step(f"Leyendo archivo: {file_name} · País detectado: {country}")

                df_temp = pd.read_csv(
                    file_path,
                    encoding="utf-8",
                    encoding_errors="replace"
                )

                df_temp["country"] = country
                dfs.append(df_temp)

            df = pd.concat(dfs, ignore_index=True)

            log_success(f"Datos concatenados: {len(df):,} filas")
            log_step(f"Países detectados: {df['country'].nunique()}")

            log_section("TRANSFORMACIÓN · Selección Top 100 global")

            top100_ids = (
                df.groupby("video_id")["views"]
                .sum()
                .sort_values(ascending=False)
                .head(100)
                .index
            )

            df = df[df["video_id"].isin(top100_ids)].reset_index(drop=True)

            log_success(f"Filas conservadas después del filtro Top 100: {len(df):,}")
            log_step(f"Videos únicos conservados: {df['video_id'].nunique()}")

            log_section("TRANSFORMACIÓN · Mapeo de categorías desde JSON")

            categories = {}
            json_files = glob.glob(f"{self.path}/*_category_id.json")

            log_step(f"Archivos JSON de categorías encontrados: {len(json_files)}")

            for json_file in json_files:
                log_step(f"Leyendo categorías desde: {os.path.basename(json_file)}")

                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                    for item in data["items"]:
                        if item["snippet"]["assignable"]:
                            categories[int(item["id"])] = item["snippet"]["title"]

            df["category"] = df["category_id"].map(categories).fillna("Unknown")

            if "category_id" in df.columns:
                df.drop(columns=["category_id"], inplace=True)

            log_success(f"Categorías mapeadas: {df['category'].nunique()} categorías únicas")

            return df

        except Exception as e:
            log_error(f"Error al concatenar los datos: {e}")
            raise

    @task(retries=3, name="03 - clean_data")
    @timer
    def clean_data(self, df):
        """Elimina filas vacías, registros duplicados y registros sin campos clave."""
        try:
            log_section("TRANSFORMACIÓN · Limpieza de datos")

            rows_before = len(df)

            log_step(f"Filas iniciales: {rows_before:,}")

            df = df.dropna(how="all")
            log_step("Filas completamente vacías eliminadas")

            df = df.dropna(subset=["video_id", "trending_date", "publish_time"])
            log_step("Registros sin video_id, trending_date o publish_time eliminados")

            df = df.drop_duplicates()
            log_step("Duplicados eliminados")

            df = df.reset_index(drop=True)

            rows_after = len(df)
            removed_rows = rows_before - rows_after

            log_success(f"Filas finales después de limpieza: {rows_after:,}")
            log_step(f"Filas eliminadas durante limpieza: {removed_rows:,}")

            return df

        except Exception as e:
            log_error(f"Error al limpiar los datos: {e}")
            raise

    @task(retries=3, name="04 - standardize_dates")
    @timer
    def standardize_dates(self, df):
        """
        Estandariza las columnas de fecha:
        - trending_date usa apply + lambda.
        - publish_time usa iterrows.
        """
        try:
            log_section("TRANSFORMACIÓN · Estandarización de fechas")

            log_step("Convirtiendo trending_date con apply y lambda")
            df["trending_date"] = df["trending_date"].apply(
                lambda x: pd.to_datetime(x, format="%y.%d.%m")
                + pd.Timedelta(hours=23, minutes=59, seconds=59)
            )

            log_step("Convirtiendo publish_time con iterrows")
            publish_times = []

            for _, row in df.iterrows():
                ts = pd.to_datetime(row["publish_time"], format="ISO8601")

                if ts.tzinfo is not None:
                    ts = ts.tz_localize(None)

                publish_times.append(ts)

            df["publish_time"] = publish_times

            log_success("Fechas estandarizadas correctamente")
            log_step("Muestra de fechas transformadas:")
            print(df[["trending_date", "publish_time"]].head())

            return df

        except Exception as e:
            log_error(f"Error al estandarizar las fechas: {e}")
            raise

    @task(retries=3, name="05 - calculate_trending_period")
    @timer
    def calculate_trending_period(self, df):
        """
        Calcula el número de días entre la publicación del video
        y la fecha en que apareció como tendencia.
        """
        try:
            log_section("TRANSFORMACIÓN · Cálculo del periodo hasta tendencia")

            diff = df["trending_date"] - df["publish_time"]

            df["trending_period"] = (
                diff.dt.total_seconds() / 86400
            ).clip(lower=0).round(2)

            log_success("Periodo de tendencia calculado correctamente")
            log_step(
                f"Promedio de días hasta tendencia: "
                f"{df['trending_period'].mean():.2f}"
            )
            log_step(
                f"Rango: {df['trending_period'].min():.2f} "
                f"a {df['trending_period'].max():.2f} días"
            )

            log_step("Muestra del cálculo:")
            print(df[["trending_date", "publish_time", "trending_period"]].head())

            return df

        except Exception as e:
            log_error(f"Error al calcular el periodo de tendencia: {e}")
            raise

    @task(retries=3, name="06 - calculate_correlation")
    @timer
    def calculate_correlation(self, df):
        """
        Calcula la correlación entre el tiempo que tardó un video en ser tendencia
        y las vistas que tenía en su primera aparición como tendencia.

        Unidad de análisis: video único.
        """
        try:
            log_section("ANÁLISIS · Correlación entre tiempo de tendencia y vistas")

            # Una fila por video: primera vez que apareció como tendencia
            sample = (
                df.sort_values(["video_id", "trending_date"])
                .groupby("video_id")
                .first()
                .reset_index()
                [["video_id", "trending_period", "views", "title"]]
                .dropna(subset=["trending_period", "views"])
            )

            sample = sample[sample["trending_period"] > 0]

            n = len(sample)

            log_step(f"Videos únicos válidos para correlación: {n:,}")

            if n < 3:
                raise ValueError("No hay suficientes videos únicos para calcular la correlación")

            if n <= 5000:
                _, p_trending = stats.shapiro(sample["trending_period"])
                _, p_views = stats.shapiro(sample["views"])
                test_used = "Shapiro-Wilk"
            else:
                _, p_trending = stats.normaltest(sample["trending_period"])
                _, p_views = stats.normaltest(sample["views"])
                test_used = "D'Agostino-Pearson"

            log_step(f"Prueba de normalidad utilizada: {test_used}")

            both_normal = p_trending > 0.05 and p_views > 0.05

            if both_normal:
                corr, p_value = stats.pearsonr(
                    sample["trending_period"],
                    sample["views"]
                )
                method = "Pearson"
                reason = "ambas variables siguen distribución normal"
            else:
                corr, p_value = stats.spearmanr(
                    sample["trending_period"],
                    sample["views"]
                )
                method = "Spearman"
                reason = "al menos una variable no sigue distribución normal"

            significant = p_value < 0.05

            print("\n   📊 Test de normalidad")
            print(
                f"   trending_period → p={p_trending:.4f} "
                f"{'normal' if p_trending > 0.05 else 'no normal'}"
            )
            print(
                f"   views           → p={p_views:.4f} "
                f"{'normal' if p_views > 0.05 else 'no normal'}"
            )

            print("\n   🔗 Resultado de correlación")
            print("   Unidad de análisis: videos únicos")
            print("   Criterio: primera aparición como tendencia")
            print(f"   Método: {method}")
            print(f"   Razón: {reason}")
            print(f"   r = {corr:.4f}")
            print(f"   p-value = {p_value:.4f}")
            print(
                f"   Resultado: "
                f"{'significativa' if significant else 'no significativa'} "
                f"(α=0.05)"
            )

            self.correlation_results = {
                "method": method,
                "corr": round(corr, 4),
                "p_value": round(p_value, 4),
                "significant": significant,
                "n": n,
                "reason": reason,
                "test_used": test_used,
                "p_trending": round(p_trending, 4),
                "p_views": round(p_views, 4),
                "unit": "video_id",
                "criterion": "first_trending_appearance",
                "trending_period_source": "first_trending_appearance",
                "views_source": "first_trending_appearance",
            }

            log_success("Correlación calculada correctamente")

            return df

        except Exception as e:
            log_error(f"Error al calcular la correlación: {e}")
            raise

    # =====================================================================================
    #      Carga
    # =====================================================================================

    @task(retries=3, name="08 - load_to_mongodb")
    @timer
    def load_to_mongodb(self, df):
        """Carga el dataset final en MongoDB dentro de la colección trending_videos."""
        try:
            log_section("CARGA · MongoDB")

            mongo_uri = os.getenv("MONGO_URI")
            mongo_db = os.getenv("MONGO_DB", "youtube_trending")

            if not mongo_uri:
                log_error("No se encontró MONGO_URI en el archivo .env")
                raise ValueError("MONGO_URI no está definido")

            safe_uri = (
                f"{mongo_uri[:30]}..."
                if len(mongo_uri) > 30
                else mongo_uri
            )

            log_step(f"URI: {safe_uri}")
            log_step(f"Base de datos: {mongo_db}")

            client = MongoClient(mongo_uri)
            client.admin.command("ping")

            log_success("Conexión con MongoDB exitosa")

            db = client[mongo_db]
            collection = db["trending_videos"]

            docs_before = collection.count_documents({})
            log_step(f"Documentos existentes antes de cargar: {docs_before:,}")

            collection.drop()
            log_success("Colección limpiada antes de insertar nuevos datos")

            df_mongo = df.copy()
            df_mongo["trending_date"] = df_mongo["trending_date"].astype(str)
            df_mongo["publish_time"] = df_mongo["publish_time"].astype(str)

            records = df_mongo.to_dict(orient="records")

            log_step(f"Insertando documentos: {len(records):,}")

            result = collection.insert_many(records)

            docs_after = collection.count_documents({})

            log_success(f"Documentos insertados: {len(result.inserted_ids):,}")
            log_step(f"Documentos actuales en colección: {docs_after:,}")

            sample_doc = collection.find_one(
                {},
                {
                    "_id": 0,
                    "title": 1,
                    "views": 1,
                    "country": 1,
                    "category": 1
                }
            )

            if sample_doc:
                print("\n   🔍 Muestra de documento insertado")
                for key, value in sample_doc.items():
                    print(f"   {key}: {value}")

            print("\n   🌍 Documentos por país")
            for country in sorted(df["country"].unique()):
                count = collection.count_documents({"country": country})
                print(f"   {country}: {count:,} documentos")

            client.close()

            log_success("Conexión con MongoDB cerrada correctamente")

            return len(result.inserted_ids)

        except Exception as e:
            log_error(f"Error al cargar datos en MongoDB: {e}")
            raise

    # =====================================================================================
    #      Orquestación del pipeline
    # =====================================================================================

    @flow(name="run", flow_run_name="ETL-YouTube")
    @timer
    def run(self):
        """Ejecuta el pipeline completo con Prefect."""
        try:
            log_section("INICIO DEL PIPELINE ETL · YOUTUBE TRENDING")
            filesystem_diagnostics()
            self.import_dataset()
            df = self.concatenate_data()
            df = self.clean_data(df)
            df = self.standardize_dates(df)
            df = self.calculate_trending_period(df)
            df = self.calculate_correlation(df)
            log_section("EXPORTACIÓN · Guardado del dataset final")
            df.to_csv(self.output_file, index=False)
            log_success(f"Archivo final generado: {self.output_file}")
            log_step(f"Filas exportadas: {len(df):,}")
            log_step(f"Columnas exportadas: {len(df.columns)}")
            check_csv_file()
            self.load_to_mongodb(df)
            log_section("PIPELINE FINALIZADO CORRECTAMENTE")

        except Exception as e:
            log_error(f"Error en el proceso ETL: {e}")
            raise


if __name__ == "__main__":
    etl = ETL()
    etl.run()