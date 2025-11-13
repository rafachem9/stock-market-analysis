#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de Análisis de Acciones convertido desde un Jupyter Notebook.

Este script descarga datos históricos de acciones del IBEX 35, S&P 500 e Índices/ETFs
usando la API de yfinance. Realiza análisis de rentabilidad, volatilidad,
ratios (Sharpe, P/E, P/B), y calcula Alpha y Beta.

Los resultados del análisis se guardan e
n archivos CSV en el directorio 'data'.
También genera y muestra gráficos de volatilidad y rentabilidad acumulada.
"""

import pandas as pd

from etl.get_index_data import get_etf_data, get_index
from etl.variables import ibex35_tickers, tickers_sp500, start_period, end_period, tickers_index

# Configuración de Pandas
pd.set_option('display.max_columns', None)


def main():
    """
    Función principal para ejecutar los análisis.
    """

    index_dictionary = {
        "IBEX 35": {
            "index_ticker": ibex35_tickers,
            "benchmark_ticker": '^IBEX',
            "index_folder": 'ibex35_historic',
            "index_filename": 'ibex35_analysed_df.csv'
        },
        "SP500": {
            "index_ticker": tickers_sp500,
            "benchmark_ticker": '^GSPC',
            "index_folder": 'sp500_historic',
            "index_filename": 'sp500_analysed_df.csv'
        }
    }

    index_result = []

    for index_name in index_dictionary:
        index_info = index_dictionary[index_name]
        df = get_index(index_name, index_info["index_ticker"], index_info["benchmark_ticker"], start_period, end_period,
                       index_info["index_folder"], index_info["index_filename"])

        index_result.append(df)

        print(f"Finalizando análisis del {index_name}...")

    index_hist_df = get_etf_data(tickers_index, start_period, end_period)

    index_result.append(index_hist_df)

    print("\n--- Análisis completado ---")


if __name__ == "__main__":
    main()