"""
Configuración centralizada del proyecto Stock Market Analysis.

Este módulo carga variables de entorno desde un archivo .env y proporciona
configuración para rutas, API keys y parámetros del sistema.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Directorio raíz del proyecto (un nivel arriba de src/)
_PROJECT_ROOT = Path(__file__).parent.parent.absolute()

# Cargar variables de entorno desde .env en la raíz del proyecto
_env_path = _PROJECT_ROOT / '.env'
load_dotenv(dotenv_path=_env_path)

# --- RUTAS DEL PROYECTO ---
# Directorio raíz del proyecto (donde está este archivo config.py)
PROJECT_DIR = Path(os.getenv(
    'PROJECT_DIR',
    Path(__file__).parent.parent.absolute()
))

# Directorio de datos
DATA_DIR = Path(os.getenv(
    'DATA_DIR',
    PROJECT_DIR / 'data'
))

# Crear directorio de datos si no existe
DATA_DIR.mkdir(parents=True, exist_ok=True)

# --- CONFIGURACIÓN DE LOGGING ---
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = os.getenv(
    'LOG_FORMAT',
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# --- CONFIGURACIÓN DE TELEGRAM (para alertas) ---
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')

# --- PARÁMETROS DE ANÁLISIS ---
# Tasa libre de riesgo por defecto (anualizada)
DEFAULT_RISK_FREE_RATE = float(os.getenv('DEFAULT_RISK_FREE_RATE', '0.0'))

# Período de RSI por defecto
RSI_PERIOD = int(os.getenv('RSI_PERIOD', '14'))

# Umbrales de RSI
RSI_OVERSOLD_THRESHOLD = int(os.getenv('RSI_OVERSOLD_THRESHOLD', '30'))
RSI_OVERBOUGHT_THRESHOLD = int(os.getenv('RSI_OVERBOUGHT_THRESHOLD', '70'))

# Días de anticipación para alertas de dividendos
DIVIDEND_ALERT_DAYS = int(os.getenv('DIVIDEND_ALERT_DAYS', '7'))

# Umbral de caída diaria para alerta (porcentaje)
DAILY_DROP_THRESHOLD = float(os.getenv('DAILY_DROP_THRESHOLD', '5.0'))

# Umbral de rentabilidad prevista para alerta (porcentaje)
EXPECTED_RETURN_THRESHOLD = float(os.getenv('EXPECTED_RETURN_THRESHOLD', '20.0'))

# --- PARÁMETROS DE PERÍODO DE ANÁLISIS ---
# Número de meses hacia atrás para el análisis (por defecto: 12 meses)
ANALYSIS_MONTHS_BACK = int(os.getenv('ANALYSIS_MONTHS_BACK', '12'))


def get_config_summary() -> dict:
    """
    Retorna un resumen de la configuración actual (sin datos sensibles).
    
    Returns:
        dict: Diccionario con la configuración actual.
    """
    return {
        'project_dir': str(PROJECT_DIR),
        'data_dir': str(DATA_DIR),
        'log_level': LOG_LEVEL,
        'rsi_period': RSI_PERIOD,
        'rsi_thresholds': {
            'oversold': RSI_OVERSOLD_THRESHOLD,
            'overbought': RSI_OVERBOUGHT_THRESHOLD
        },
        'dividend_alert_days': DIVIDEND_ALERT_DAYS,
        'daily_drop_threshold': DAILY_DROP_THRESHOLD,
        'expected_return_threshold': EXPECTED_RETURN_THRESHOLD,
        'telegram_configured': bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
    }
