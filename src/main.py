#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de Análisis de Acciones convertido desde un Jupyter Notebook.

Este script descarga datos históricos de acciones del IBEX 35, S&P 500 e Índices/ETFs
usando la API de yfinance. Realiza análisis de rentabilidad, volatilidad,
ratios (Sharpe, P/E, P/B), y calcula Alpha y Beta.

Los resultados del análisis se guardan en archivos CSV en el directorio 'data'.
También genera y muestra gráficos de volatilidad y rentabilidad acumulada.
Genera alertas de Telegram para señales de trading importantes.
"""

import asyncio
import logging

import pandas as pd

from config import LOG_LEVEL, LOG_FORMAT, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from etl.alerts import AlertManager, Alert
from etl.get_index_data import get_etf_data, get_index
from etl.variables import ibex35_tickers, tickers_sp500, start_period, end_period, tickers_index

# Configuración de Logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)

# Configuración de Pandas
pd.set_option('display.max_columns', None)


def format_alerts_summary(alerts: list[Alert], index_name: str) -> str:
    """
    Formatea un resumen de alertas para logging.
    
    Args:
        alerts: Lista de alertas generadas.
        index_name: Nombre del índice analizado.
        
    Returns:
        Resumen formateado de las alertas.
    """
    if not alerts:
        return f"No se generaron alertas para {index_name}"
    
    summary_lines = [f"\n📊 Resumen de Alertas - {index_name} ({len(alerts)} alertas):"]
    
    # Agrupar por tipo
    by_type = {}
    for alert in alerts:
        alert_type = alert.alert_type.value
        if alert_type not in by_type:
            by_type[alert_type] = []
        by_type[alert_type].append(alert)
    
    for alert_type, type_alerts in by_type.items():
        summary_lines.append(f"  • {alert_type}: {len(type_alerts)}")
        for alert in type_alerts[:3]:  # Mostrar máximo 3 por tipo
            summary_lines.append(f"    - {alert.company_name} ({alert.ticker})")
        if len(type_alerts) > 3:
            summary_lines.append(f"    ... y {len(type_alerts) - 3} más")
    
    return "\n".join(summary_lines)


async def send_telegram_summary(alert_manager: AlertManager, all_alerts: list[Alert]) -> None:
    """
    Envía un resumen consolidado de alertas a Telegram.
    
    Args:
        alert_manager: Instancia del gestor de alertas.
        all_alerts: Lista de todas las alertas a enviar.
    """
    if not all_alerts:
        logger.info("No hay alertas para enviar a Telegram")
        return
    
    if not alert_manager._telegram_bot:
        logger.info("Telegram no configurado. Las alertas no se enviarán.")
        return
    
    # Enviar resumen inicial
    header = f"🔔 *Stock Market Analysis*\n\n📈 Se han detectado {len(all_alerts)} alertas:\n"
    
    try:
        await alert_manager._telegram_bot.send_message(
            chat_id=alert_manager.chat_id,
            text=header,
            parse_mode='Markdown'
        )
        
        # Enviar alertas individuales (con un pequeño delay para evitar rate limiting)
        sent_count = 0
        for alert in all_alerts:
            try:
                await alert_manager.send_telegram_alert(alert)
                sent_count += 1
                # Pequeño delay para evitar rate limiting de Telegram
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Error enviando alerta {alert.ticker}: {e}")
        
        logger.info(f"Alertas enviadas a Telegram: {sent_count}/{len(all_alerts)}")
        
    except Exception as e:
        logger.error(f"Error enviando resumen a Telegram: {e}")


def run_alerts_for_index(
    alert_manager: AlertManager,
    analysis_df: pd.DataFrame,
    historical_data: dict,
    index_name: str
) -> list[Alert]:
    """
    Ejecuta todas las verificaciones de alertas para un índice.
    
    Args:
        alert_manager: Instancia del gestor de alertas.
        analysis_df: DataFrame con el análisis del índice.
        historical_data: Diccionario con datos históricos.
        index_name: Nombre del índice.
        
    Returns:
        Lista de alertas generadas.
    """
    logger.info(f"Ejecutando verificaciones de alertas para {index_name}...")
    
    alerts = alert_manager.run_all_checks(analysis_df, historical_data)
    
    # Log del resumen
    summary = format_alerts_summary(alerts, index_name)
    logger.info(summary)
    
    return alerts


def main():
    """
    Función principal para ejecutar los análisis.
    """
    # Inicializar el gestor de alertas
    alert_manager = AlertManager()
    
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        logger.info("Sistema de alertas de Telegram configurado correctamente")
    else:
        logger.warning(
            "Telegram no configurado. Configure TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID "
            "en el archivo .env para recibir alertas."
        )

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
    all_alerts = []

    for index_name in index_dictionary:
        index_info = index_dictionary[index_name]
        analysis_df, historical_data = get_index(
            index_name, 
            index_info["index_ticker"], 
            index_info["benchmark_ticker"], 
            start_period, 
            end_period,
            index_info["index_folder"], 
            index_info["index_filename"]
        )

        index_result.append(analysis_df)
        
        # Ejecutar verificaciones de alertas para este índice
        alerts = run_alerts_for_index(
            alert_manager, 
            analysis_df, 
            historical_data, 
            index_name
        )
        all_alerts.extend(alerts)

        logger.info(f"Finalizando análisis del {index_name}...")

    index_hist_df = get_etf_data(tickers_index, start_period, end_period)

    index_result.append(index_hist_df)

    logger.info("--- Análisis completado ---")
    
    # Enviar todas las alertas a Telegram
    if all_alerts:
        logger.info(f"Total de alertas generadas: {len(all_alerts)}")
        try:
            asyncio.run(send_telegram_summary(alert_manager, all_alerts))
        except Exception as e:
            logger.error(f"Error al enviar alertas a Telegram: {e}")
    else:
        logger.info("No se generaron alertas durante el análisis")
    
    logger.info("--- Proceso finalizado ---")


if __name__ == "__main__":
    main()