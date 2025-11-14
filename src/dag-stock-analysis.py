from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator
from datetime import datetime

# -----------------------------
# DAG settings
# -----------------------------
default_args = {
    'owner': 'rafachem9',
    'depends_on_past': False,
    'retries': 1,
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
    bash_command='python3 /home/rafachem9/data-engineer/stock-market-analysis/src/main.py',
    dag=dag
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
start >> run_script >> end

