import os
from etl.functions import call_yf_api_historic, extraction_historic, analysis_stock_hist, save_extraction_historic_parquet, get_total_rank
from etl.variables import DATA_DIR
import matplotlib.pyplot as plt
import pandas as pd

def get_index(index_name, index_ticker, benchmark_ticker, start_period, end_period, 
              index_folder, index_filename):
    print(f"Iniciando análisis del {index_name}...")

    bechmark_ibex35 = call_yf_api_historic(start_period, end_period, benchmark_ticker)
    df = extraction_historic(start_period, end_period, index_ticker)

    print(f"\nGuardando datos históricos del {index_name} en Parquet...")
    SUBFOLDER_DIR_IBEX = os.path.join(DATA_DIR, index_folder)
    save_extraction_historic_parquet(df, SUBFOLDER_DIR_IBEX)

    print(f"\nRealizando análisis del {index_name}...")
    analysis_df = analysis_stock_hist(df, index_ticker, bechmark_ibex35)

    print(f"Calculando rankings para {index_name}...")
    analysis_df = get_total_rank(analysis_df, 'rank_per', [80, 40, 20])
    analysis_df = get_total_rank(analysis_df, 'rank_dividend', [30, 70, 30])

    analysis_df = analysis_df.sort_values(by="rank_per", ascending=False)
    ibex35_filename = os.path.join(DATA_DIR, index_filename)
    analysis_df.to_csv(ibex35_filename, index=False)

    print(f"\n--- Resultados Top 30 {index_name} (por rank_per) ---")
    print(analysis_df.head(30))
    print(f"Análisis del {index_name} guardado en: {ibex35_filename}")

    # --- GRÁFICO VOLATILIDAD {index_name} ---
    print(f"\nGenerando gráfico de volatilidad {index_name}...")
    volatilities_index = {
        ticker: data["Daily Return"].std() for ticker, data in df.items() if not data.empty
    }
    vol_df_index = pd.DataFrame.from_dict(volatilities_index, orient='index', columns=["Volatilidad"])
    vol_df_index.sort_values("Volatilidad", ascending=False).plot(kind='bar', figsize=(12, 6), legend=False)
    plt.title(f"Volatilidad Diaria (Std Dev de Daily Return) - {index_name} 2025")
    plt.ylabel("Volatilidad")
    plt.grid(True)
    plt.tight_layout()

    img_volatility_filename = os.path.join(DATA_DIR, f'{index_name.lower().replace(" ", "_")}_volatility_2025.png')
    plt.savefig(img_volatility_filename)
    return analysis_df


def get_etf_data(tickers_index, start_period, end_period):
    # Extracción histórica de índices/ETFs
    index_hist_df = extraction_historic(start_period, end_period, tickers_index)

    # El análisis estaba comentado en el notebook original, se mantiene así.
    # print("\nRealizando análisis de Índices/ETFs...")
    # index_analysed_df = analysis_stock_hist(index_hist_df, tickers_index, bechmark_index_sp500)
    # print(index_analysed_df)

    # --- GRÁFICOS ÍNDICES/ETFS ---
    print("\nGenerando gráficos de Índices/ETFs...")
    plt.figure(figsize=(14, 7))
    for ticker, data in index_hist_df.items():
        if not data.empty:
            plt.plot(data.index, data["Cumulative Return"].rolling(window=5).mean(), label=ticker)

    plt.title("Rentabilidad Acumulada (Índices/ETFs) - 2025")
    plt.xlabel("Fecha")
    plt.ylabel("Rentabilidad Acumulada")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    img_volatility_filename = os.path.join(DATA_DIR, f'etf_return_2025.png')
    plt.savefig(img_volatility_filename)

    volatilities_index = {
        ticker: data["Daily Return"].std() for ticker, data in index_hist_df.items() if not data.empty
    }
    vol_df_index = pd.DataFrame.from_dict(volatilities_index, orient='index', columns=["Volatilidad"])
    vol_df_index.sort_values("Volatilidad", ascending=False).plot(kind='bar', figsize=(12, 6), legend=False)

    plt.title("Volatilidad Diaria (Std Dev de Daily Return) - Índices/ETFs 2025")
    plt.ylabel("Volatilidad")
    plt.grid(True)
    plt.tight_layout()

    img_volatility_filename = os.path.join(DATA_DIR, f'etf_volatility_2025.png')
    plt.savefig(img_volatility_filename)

    return index_hist_df
