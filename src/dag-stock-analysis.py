from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator
from datetime import datetime
from airflow.operators.email import EmailOperator

# -----------------------------
# settings
# -----------------------------

FILE_PATH = "/home/rafachem9/data-engineer/stock-market-analysis"
EMAIL_LIST = ["rafachem9@gmail.com", "rafachem9@gmail.com"]
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
    bash_command=f'python3 {FILE_PATH}/src/main.py',
    dag=dag
)

send_email = EmailOperator(
    task_id="send_email",
    to=EMAIL_LIST,
    subject="Reporte diario con adjunto {{ ds }}",
    html_content="""
    <h3>Hola,</h3>
    <p>Adjunto el fichero con el reporte diario.</p>
    <img src="cid:sp500_volatility_2025.png" alt="Logo" style="width:200px;">
    <img src="cid:etf_return_2025.png" alt="Logo" style="width:200px;">
    <img src="cid:ibex_35_volatility_2025.png" alt="Logo" style="width:200px;">

    """,
    files=[
        f"{FILE_PATH}/data/sp500_analysed_df.csv",
                        f"{FILE_PATH}/data/dividendos_ibex35_analysed_df.csv",
                        f"{FILE_PATH}/data/dividendos_sp500_analysed_df.csv",
                        f"{FILE_PATH}/data/sp500_volatility_2025.png",
                        f"{FILE_PATH}/data/etf_return_2025.png",
                        f"{FILE_PATH}/data/ibex_35_volatility_2025.png",
                        f"{FILE_PATH}/data/ibex35_analysed_df.csv"
    ],
    conn_id="my_smtp_connection",
    mime_subtype='related',                  # Necesario para manejar multipart MIME
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

