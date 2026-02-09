import os
from datetime import datetime
from pathlib import Path

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator
from airflow.operators.email import EmailOperator

# -----------------------------
# settings
# -----------------------------

# Directorio src (donde está main.py)
SRC_DIR = os.getenv(
    'STOCK_ANALYSIS_SRC_PATH',
    str(Path(__file__).parent.absolute())
)

# Directorio de datos (un nivel arriba de src)
DATA_DIR = os.getenv(
    'STOCK_ANALYSIS_DATA_PATH',
    str(Path(__file__).parent.parent.absolute() / 'data')
)

# Lista de emails para notificaciones (sin duplicados)
EMAIL_LIST = ["rafachem9@gmail.com"]

# Año actual para nombres de archivos
CURRENT_YEAR = datetime.now().year

# -----------------------------
# DAG settings
# -----------------------------
default_args = {
    'owner': 'rafachem9',
    'depends_on_past': False,
    'retries': 1,
    "email": ["rafachem9@gmail.com"],
    "email_on_failure": True,
}

dag = DAG(
    'run_stock_market_analysis',
    default_args=default_args,
    description='Run stock market analysis Python script daily at 9AM',
    schedule_interval='0 9 * * *',  # Todos los días a las 9:00 AM
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['stock', 'analysis']
)

# -----------------------------
# Dummy start task
# -----------------------------
start = EmptyOperator(
    task_id='start',
    dag=dag
)

# -----------------------------
# Task: run Python script
# -----------------------------
run_script = BashOperator(
    task_id='execute_main_py',
    bash_command=f'python3 {SRC_DIR}/main.py',
    dag=dag
)

send_email = EmailOperator(
    task_id="send_email",
    to=EMAIL_LIST,
    subject="📊 Stock Market Analysis - Reporte {{ ds }}",
    html_content=f"""
    <h2>📈 Reporte Diario de Análisis Bursátil</h2>
    <p>Adjunto encontrarás los análisis del IBEX 35 y S&P 500.</p>
    
    <h3>Gráficos incluidos:</h3>
    <img src="cid:sp500_volatility_{CURRENT_YEAR}.png" alt="Volatilidad SP500" style="max-width:600px;">
    <img src="cid:etf_return_{CURRENT_YEAR}.png" alt="Rentabilidad ETFs" style="max-width:600px;">
    <img src="cid:ibex_35_volatility_{CURRENT_YEAR}.png" alt="Volatilidad IBEX 35" style="max-width:600px;">
    
    <p><em>Generado automáticamente por Stock Market Analysis</em></p>
    """,
    files=[
        f"{DATA_DIR}/sp500_analysed_df.csv",
        f"{DATA_DIR}/ibex35_analysed_df.csv",
        f"{DATA_DIR}/dividendos_sp500_analysed_df.csv",
        f"{DATA_DIR}/dividendos_ibex35_analysed_df.csv",
        f"{DATA_DIR}/sp500_volatility_{CURRENT_YEAR}.png",
        f"{DATA_DIR}/etf_return_{CURRENT_YEAR}.png",
        f"{DATA_DIR}/ibex_35_volatility_{CURRENT_YEAR}.png",
    ],
    conn_id="my_smtp_connection",
    mime_subtype='related',
)


# -----------------------------
# Dummy end task
# -----------------------------
end = EmptyOperator(
    task_id='end',
    dag=dag
)

# -----------------------------
# Task dependencies
# -----------------------------
start >> run_script >> send_email >> end

