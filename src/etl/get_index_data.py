import copy
import logging
import os

# Configurar backend de matplotlib antes de importar pyplot
import matplotlib
matplotlib.use('Agg')

# Parche para compatibilidad con Python 3.14 beta
# El método __deepcopy__ de matplotlib.path.Path tiene un bug en Python 3.14
from matplotlib.path import Path as MplPath
_original_deepcopy = MplPath.__deepcopy__

def _patched_deepcopy(self, memo):
    """Versión parcheada de __deepcopy__ para evitar recursión infinita en Python 3.14."""
    try:
        # Intentar usar shallow copy en lugar de deepcopy
        return MplPath(
            copy.copy(self.vertices),
            copy.copy(self.codes) if self.codes is not None else None,
        )
    except Exception:
        # Fallback: retornar una copia simple
        return MplPath(self.vertices.copy(), self.codes.copy() if self.codes is not None else None)

MplPath.__deepcopy__ = _patched_deepcopy

import matplotlib.pyplot as plt
import pandas as pd

from config import DATA_DIR
from etl.functions import (
    call_yf_api_historic,
    extraction_historic,
    analysis_stock_hist,
    save_extraction_historic_parquet,
    get_total_rank
)

logger = logging.getLogger(__name__)

def get_index(index_name, index_ticker, benchmark_ticker, start_period, end_period, 
              index_folder, index_filename):
    """Analiza un índice bursátil y genera gráficos."""
    # Año para nombres de archivos (basado en fecha de fin del análisis)
    analysis_year = end_period.year
    
    logger.info(f"Iniciando análisis del {index_name}...")

    bechmark_ibex35 = call_yf_api_historic(start_period, end_period, benchmark_ticker)
    df = extraction_historic(start_period, end_period, index_ticker)

    logger.info(f"Guardando datos históricos del {index_name} en Parquet...")
    SUBFOLDER_DIR_IBEX = os.path.join(DATA_DIR, index_folder)
    save_extraction_historic_parquet(df, SUBFOLDER_DIR_IBEX)

    logger.info(f"Realizando análisis del {index_name}...")
    analysis_df = analysis_stock_hist(df, index_ticker, bechmark_ibex35)

    logger.info(f"Calculando rankings para {index_name}...")
    analysis_df = get_total_rank(analysis_df, 'rank_per', [80, 40, 20])
    analysis_df = get_total_rank(analysis_df, 'rank_dividend', [30, 70, 30])

    analysis_df = analysis_df.sort_values(by="rank_per", ascending=False)
    index_filename_dir = os.path.join(DATA_DIR, index_filename)
    analysis_df.to_csv(index_filename_dir, index=False)

    logger.info(f"--- Resultados Top 30 {index_name} (por rank_per) ---")
    logger.info(f"\n{analysis_df.head(30).to_string()}")
    logger.info(f"Análisis del {index_name} guardado en: {index_filename_dir}")

    logger.info(f"Calculando Próximos dividendos para {index_name}...")

    dividend_cols = ['Empresa', 'Ticker', 'Sector', 'Rentabilidad prevista', 'Ex-Dividend Date', 'Next Dividend',
                     'Dividend Yield', 'rank_dividend']
    dividen_df = analysis_df.loc[pd.to_datetime(analysis_df['Ex-Dividend Date']) >= end_period][dividend_cols].sort_values(
        by='Dividend Yield', ascending=False)

    dividend_filename_dir = os.path.join(DATA_DIR, f"dividendos_{index_filename}")
    dividen_df.to_csv(dividend_filename_dir, index=False)

    logger.info(f"Análisis del Dividendo {index_name} guardado en: {dividend_filename_dir}")

    # --- GRÁFICO VOLATILIDAD {index_name} ---
    logger.info(f"Generando gráfico de volatilidad {index_name}...")
    volatilities_index = {
        ticker: data["Daily Return"].std() for ticker, data in df.items() if not data.empty
    }
    vol_df_index = pd.DataFrame.from_dict(volatilities_index, orient='index', columns=["Volatilidad"])
    vol_df_sorted = vol_df_index.sort_values("Volatilidad", ascending=False)
    
    # Usar matplotlib directamente en lugar de pandas.plot() para evitar problemas con deepcopy
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.bar(range(len(vol_df_sorted)), vol_df_sorted["Volatilidad"].values)
    ax.set_xticks(range(len(vol_df_sorted)))
    ax.set_xticklabels(vol_df_sorted.index, rotation=90)
    ax.set_title(f"Volatilidad Diaria (Std Dev de Daily Return) - {index_name} {analysis_year}")
    ax.set_ylabel("Volatilidad")
    ax.grid(True)
    fig.tight_layout()

    img_volatility_filename = os.path.join(DATA_DIR, f'{index_name.lower().replace(" ", "_")}_volatility_{analysis_year}.png')
    fig.savefig(img_volatility_filename)
    plt.close(fig)
    
    # Retornar tanto el análisis como los datos históricos (para alertas)
    return analysis_df, df


def get_etf_data(tickers_index, start_period, end_period):
    """Extrae y grafica datos de ETFs e índices."""
    # Año para nombres de archivos
    analysis_year = end_period.year
    
    # Extracción histórica de índices/ETFs
    index_hist_df = extraction_historic(start_period, end_period, tickers_index)

    # --- GRÁFICOS ÍNDICES/ETFS ---
    logger.info("Generando gráficos de Índices/ETFs...")
    
    # Gráfico de rentabilidad acumulada
    fig1, ax1 = plt.subplots(figsize=(14, 7))
    for ticker, data in index_hist_df.items():
        if not data.empty:
            ax1.plot(data.index, data["Cumulative Return"].rolling(window=5).mean(), label=ticker)

    ax1.set_title(f"Rentabilidad Acumulada (Índices/ETFs) - {analysis_year}")
    ax1.set_xlabel("Fecha")
    ax1.set_ylabel("Rentabilidad Acumulada")
    ax1.legend()
    ax1.grid(True)
    fig1.tight_layout()
    img_return_filename = os.path.join(DATA_DIR, f'etf_return_{analysis_year}.png')
    fig1.savefig(img_return_filename)
    plt.close(fig1)

    # Gráfico de volatilidad
    volatilities_index = {
        ticker: data["Daily Return"].std() for ticker, data in index_hist_df.items() if not data.empty
    }
    vol_df_index = pd.DataFrame.from_dict(volatilities_index, orient='index', columns=["Volatilidad"])
    vol_df_sorted = vol_df_index.sort_values("Volatilidad", ascending=False)
    
    # Usar matplotlib directamente en lugar de pandas.plot()
    fig2, ax2 = plt.subplots(figsize=(12, 6))
    ax2.bar(range(len(vol_df_sorted)), vol_df_sorted["Volatilidad"].values)
    ax2.set_xticks(range(len(vol_df_sorted)))
    ax2.set_xticklabels(vol_df_sorted.index, rotation=90)
    ax2.set_title(f"Volatilidad Diaria (Std Dev de Daily Return) - Índices/ETFs {analysis_year}")
    ax2.set_ylabel("Volatilidad")
    ax2.grid(True)
    fig2.tight_layout()

    img_volatility_filename = os.path.join(DATA_DIR, f'etf_volatility_{analysis_year}.png')
    fig2.savefig(img_volatility_filename)
    plt.close(fig2)

    return index_hist_df
