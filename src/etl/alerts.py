"""
Sistema de Alertas para Stock Market Analysis.

Este módulo proporciona funciones para detectar señales de trading y
enviar notificaciones a través de Telegram.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from enum import Enum
from typing import Optional

import numpy as np
import pandas as pd

from config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    RSI_PERIOD,
    RSI_OVERSOLD_THRESHOLD,
    RSI_OVERBOUGHT_THRESHOLD,
    DIVIDEND_ALERT_DAYS,
    DAILY_DROP_THRESHOLD,
    EXPECTED_RETURN_THRESHOLD,
)

logger = logging.getLogger(__name__)


class AlertType(Enum):
    """Tipos de alertas disponibles."""
    RSI_OVERSOLD = "rsi_oversold"
    RSI_OVERBOUGHT = "rsi_overbought"
    GOLDEN_CROSS = "golden_cross"
    DEATH_CROSS = "death_cross"
    DIVIDEND_UPCOMING = "dividend_upcoming"
    LARGE_DROP = "large_drop"
    HIGH_EXPECTED_RETURN = "high_expected_return"


@dataclass
class Alert:
    """Representa una alerta generada por el sistema."""
    alert_type: AlertType
    ticker: str
    company_name: str
    message: str
    value: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_telegram_message(self) -> str:
        """Formatea la alerta para envío por Telegram."""
        emoji_map = {
            AlertType.RSI_OVERSOLD: "🟢",
            AlertType.RSI_OVERBOUGHT: "🔴",
            AlertType.GOLDEN_CROSS: "📈",
            AlertType.DEATH_CROSS: "📉",
            AlertType.DIVIDEND_UPCOMING: "💰",
            AlertType.LARGE_DROP: "⚠️",
            AlertType.HIGH_EXPECTED_RETURN: "🚀",
        }
        emoji = emoji_map.get(self.alert_type, "📊")
        return f"{emoji} *{self.company_name}* ({self.ticker})\n{self.message}"


def compute_rsi(data: pd.DataFrame, period: int = RSI_PERIOD) -> pd.Series:
    """
    Calcula el RSI (Relative Strength Index) para una serie de precios.
    
    Args:
        data: DataFrame con columna 'Close' de precios de cierre.
        period: Período para el cálculo del RSI (por defecto 14).
        
    Returns:
        Serie con los valores de RSI.
    """
    if 'Close' not in data.columns or len(data) < period + 1:
        return pd.Series(dtype=float)
    
    delta = data['Close'].diff()
    
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    
    # Evitar división por cero
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def compute_moving_averages(
    data: pd.DataFrame, 
    short_period: int = 50, 
    long_period: int = 200
) -> tuple[pd.Series, pd.Series]:
    """
    Calcula las medias móviles de 50 y 200 días.
    
    Args:
        data: DataFrame con columna 'Close'.
        short_period: Período corto (por defecto 50 días).
        long_period: Período largo (por defecto 200 días).
        
    Returns:
        Tupla con (MA50, MA200) como Series de pandas.
    """
    if 'Close' not in data.columns:
        return pd.Series(dtype=float), pd.Series(dtype=float)
    
    ma_short = data['Close'].rolling(window=short_period, min_periods=short_period).mean()
    ma_long = data['Close'].rolling(window=long_period, min_periods=long_period).mean()
    
    return ma_short, ma_long


def detect_cross_signals(
    data: pd.DataFrame,
    short_period: int = 50,
    long_period: int = 200
) -> tuple[bool, bool]:
    """
    Detecta señales de Golden Cross y Death Cross.
    
    Golden Cross: MA50 cruza por encima de MA200 (señal alcista).
    Death Cross: MA50 cruza por debajo de MA200 (señal bajista).
    
    Args:
        data: DataFrame con columna 'Close'.
        short_period: Período de la media móvil corta.
        long_period: Período de la media móvil larga.
        
    Returns:
        Tupla (golden_cross, death_cross) indicando si se detectó cada señal.
    """
    if len(data) < long_period + 2:
        return False, False
    
    ma_short, ma_long = compute_moving_averages(data, short_period, long_period)
    
    if ma_short.isna().iloc[-1] or ma_long.isna().iloc[-1]:
        return False, False
    
    # Comparar últimos dos días
    short_prev = ma_short.iloc[-2]
    short_curr = ma_short.iloc[-1]
    long_prev = ma_long.iloc[-2]
    long_curr = ma_long.iloc[-1]
    
    # Golden Cross: MA corta cruza por encima de MA larga
    golden_cross = (short_prev <= long_prev) and (short_curr > long_curr)
    
    # Death Cross: MA corta cruza por debajo de MA larga
    death_cross = (short_prev >= long_prev) and (short_curr < long_curr)
    
    return golden_cross, death_cross


class AlertManager:
    """
    Gestiona la detección y envío de alertas del sistema.
    
    Attributes:
        telegram_token: Token del bot de Telegram.
        chat_id: ID del chat donde enviar las alertas.
    """
    
    def __init__(
        self, 
        telegram_token: str = TELEGRAM_BOT_TOKEN, 
        chat_id: str = TELEGRAM_CHAT_ID
    ):
        """
        Inicializa el gestor de alertas.
        
        Args:
            telegram_token: Token del bot de Telegram.
            chat_id: ID del chat de destino.
        """
        self.telegram_token = telegram_token
        self.chat_id = chat_id
        self._telegram_bot = None
        
        if telegram_token and chat_id:
            try:
                from telegram import Bot
                self._telegram_bot = Bot(token=telegram_token)
                logger.info("Bot de Telegram inicializado correctamente")
            except ImportError:
                logger.warning(
                    "python-telegram-bot no instalado. "
                    "Las alertas de Telegram no estarán disponibles."
                )
            except Exception as e:
                logger.error(f"Error inicializando bot de Telegram: {e}")
        else:
            logger.info("Telegram no configurado. Las alertas solo se registrarán en logs.")
    
    def check_oversold_stocks(
        self, 
        df_analysis: pd.DataFrame,
        historical_data: dict[str, pd.DataFrame],
        threshold: int = RSI_OVERSOLD_THRESHOLD
    ) -> list[Alert]:
        """
        Detecta acciones con RSI por debajo del umbral de sobreventa.
        
        Args:
            df_analysis: DataFrame con el análisis de acciones (debe tener 'Ticker', 'Empresa').
            historical_data: Diccionario con datos históricos {nombre_empresa: DataFrame}.
            threshold: Umbral de RSI para considerar sobreventa.
            
        Returns:
            Lista de alertas para acciones sobrevendidas.
        """
        alerts = []
        
        for _, row in df_analysis.iterrows():
            empresa = row.get('Empresa')
            ticker = row.get('Ticker')
            
            if empresa not in historical_data:
                continue
                
            data = historical_data[empresa]
            if data.empty:
                continue
            
            rsi = compute_rsi(data)
            if rsi.empty or pd.isna(rsi.iloc[-1]):
                continue
            
            current_rsi = rsi.iloc[-1]
            if current_rsi < threshold:
                alert = Alert(
                    alert_type=AlertType.RSI_OVERSOLD,
                    ticker=ticker,
                    company_name=empresa,
                    message=f"RSI en zona de sobreventa: {current_rsi:.1f} (< {threshold})",
                    value=current_rsi
                )
                alerts.append(alert)
                logger.info(f"Alerta RSI sobreventa: {empresa} ({ticker}) - RSI: {current_rsi:.1f}")
        
        return alerts
    
    def check_overbought_stocks(
        self,
        df_analysis: pd.DataFrame,
        historical_data: dict[str, pd.DataFrame],
        threshold: int = RSI_OVERBOUGHT_THRESHOLD
    ) -> list[Alert]:
        """
        Detecta acciones con RSI por encima del umbral de sobrecompra.
        
        Args:
            df_analysis: DataFrame con el análisis de acciones.
            historical_data: Diccionario con datos históricos.
            threshold: Umbral de RSI para considerar sobrecompra.
            
        Returns:
            Lista de alertas para acciones sobrecompradas.
        """
        alerts = []
        
        for _, row in df_analysis.iterrows():
            empresa = row.get('Empresa')
            ticker = row.get('Ticker')
            
            if empresa not in historical_data:
                continue
                
            data = historical_data[empresa]
            if data.empty:
                continue
            
            rsi = compute_rsi(data)
            if rsi.empty or pd.isna(rsi.iloc[-1]):
                continue
            
            current_rsi = rsi.iloc[-1]
            if current_rsi > threshold:
                alert = Alert(
                    alert_type=AlertType.RSI_OVERBOUGHT,
                    ticker=ticker,
                    company_name=empresa,
                    message=f"RSI en zona de sobrecompra: {current_rsi:.1f} (> {threshold})",
                    value=current_rsi
                )
                alerts.append(alert)
                logger.info(f"Alerta RSI sobrecompra: {empresa} ({ticker}) - RSI: {current_rsi:.1f}")
        
        return alerts
    
    def check_cross_signals(
        self,
        df_analysis: pd.DataFrame,
        historical_data: dict[str, pd.DataFrame]
    ) -> list[Alert]:
        """
        Detecta señales de Golden Cross y Death Cross.
        
        Args:
            df_analysis: DataFrame con el análisis de acciones.
            historical_data: Diccionario con datos históricos.
            
        Returns:
            Lista de alertas para cruces detectados.
        """
        alerts = []
        
        for _, row in df_analysis.iterrows():
            empresa = row.get('Empresa')
            ticker = row.get('Ticker')
            
            if empresa not in historical_data:
                continue
                
            data = historical_data[empresa]
            if data.empty:
                continue
            
            golden_cross, death_cross = detect_cross_signals(data)
            
            if golden_cross:
                alert = Alert(
                    alert_type=AlertType.GOLDEN_CROSS,
                    ticker=ticker,
                    company_name=empresa,
                    message="¡Golden Cross detectado! MA50 cruzó por encima de MA200 (señal alcista)"
                )
                alerts.append(alert)
                logger.info(f"Alerta Golden Cross: {empresa} ({ticker})")
            
            if death_cross:
                alert = Alert(
                    alert_type=AlertType.DEATH_CROSS,
                    ticker=ticker,
                    company_name=empresa,
                    message="¡Death Cross detectado! MA50 cruzó por debajo de MA200 (señal bajista)"
                )
                alerts.append(alert)
                logger.info(f"Alerta Death Cross: {empresa} ({ticker})")
        
        return alerts
    
    def check_upcoming_dividends(
        self,
        df_analysis: pd.DataFrame,
        days: int = DIVIDEND_ALERT_DAYS
    ) -> list[Alert]:
        """
        Detecta acciones con dividendo próximo.
        
        Args:
            df_analysis: DataFrame con columnas 'Ex-Dividend Date', 'Next Dividend'.
            days: Días de anticipación para la alerta.
            
        Returns:
            Lista de alertas para dividendos próximos.
        """
        alerts = []
        today = date.today()
        threshold_date = today + timedelta(days=days)
        
        for _, row in df_analysis.iterrows():
            empresa = row.get('Empresa')
            ticker = row.get('Ticker')
            ex_div_date = row.get('Ex-Dividend Date')
            next_dividend = row.get('Next Dividend')
            dividend_yield = row.get('Dividend Yield')
            
            if pd.isna(ex_div_date) or ex_div_date is None:
                continue
            
            # Convertir a date si es necesario
            if isinstance(ex_div_date, datetime):
                ex_div_date = ex_div_date.date()
            elif isinstance(ex_div_date, str):
                try:
                    ex_div_date = datetime.strptime(ex_div_date, '%Y-%m-%d').date()
                except ValueError:
                    continue
            
            if today <= ex_div_date <= threshold_date:
                days_until = (ex_div_date - today).days
                div_info = f"${next_dividend:.4f}" if next_dividend else "N/A"
                yield_info = f"{dividend_yield*100:.2f}%" if dividend_yield else "N/A"
                
                alert = Alert(
                    alert_type=AlertType.DIVIDEND_UPCOMING,
                    ticker=ticker,
                    company_name=empresa,
                    message=(
                        f"Dividendo en {days_until} días ({ex_div_date})\n"
                        f"Dividendo estimado: {div_info} | Yield: {yield_info}"
                    ),
                    value=next_dividend
                )
                alerts.append(alert)
                logger.info(f"Alerta dividendo próximo: {empresa} ({ticker}) - {ex_div_date}")
        
        return alerts
    
    def check_large_drops(
        self,
        df_analysis: pd.DataFrame,
        historical_data: dict[str, pd.DataFrame],
        threshold: float = DAILY_DROP_THRESHOLD
    ) -> list[Alert]:
        """
        Detecta acciones con caídas superiores al umbral en el último día.
        
        Args:
            df_analysis: DataFrame con el análisis de acciones.
            historical_data: Diccionario con datos históricos.
            threshold: Umbral de caída en porcentaje.
            
        Returns:
            Lista de alertas para caídas grandes.
        """
        alerts = []
        
        for _, row in df_analysis.iterrows():
            empresa = row.get('Empresa')
            ticker = row.get('Ticker')
            
            if empresa not in historical_data:
                continue
                
            data = historical_data[empresa]
            if data.empty or 'Daily Return' not in data.columns:
                continue
            
            last_return = data['Daily Return'].iloc[-1] * 100  # Convertir a porcentaje
            
            if last_return < -threshold:
                alert = Alert(
                    alert_type=AlertType.LARGE_DROP,
                    ticker=ticker,
                    company_name=empresa,
                    message=f"Caída significativa del {last_return:.2f}% en el último día",
                    value=last_return
                )
                alerts.append(alert)
                logger.info(f"Alerta caída grande: {empresa} ({ticker}) - {last_return:.2f}%")
        
        return alerts
    
    def check_high_expected_returns(
        self,
        df_analysis: pd.DataFrame,
        threshold: float = EXPECTED_RETURN_THRESHOLD
    ) -> list[Alert]:
        """
        Detecta acciones con rentabilidad prevista superior al umbral.
        
        Args:
            df_analysis: DataFrame con columna 'Rentabilidad prevista'.
            threshold: Umbral de rentabilidad en porcentaje.
            
        Returns:
            Lista de alertas para altas rentabilidades previstas.
        """
        alerts = []
        
        for _, row in df_analysis.iterrows():
            empresa = row.get('Empresa')
            ticker = row.get('Ticker')
            rentabilidad = row.get('Rentabilidad prevista')
            precio_actual = row.get('Precio actual')
            precio_objetivo = row.get('Precio objetivo analistas')
            
            if pd.isna(rentabilidad) or rentabilidad is None:
                continue
            
            if rentabilidad > threshold:
                precio_info = ""
                if precio_actual and precio_objetivo:
                    precio_info = f"\nPrecio actual: ${precio_actual:.2f} → Objetivo: ${precio_objetivo:.2f}"
                
                alert = Alert(
                    alert_type=AlertType.HIGH_EXPECTED_RETURN,
                    ticker=ticker,
                    company_name=empresa,
                    message=f"Rentabilidad prevista alta: {rentabilidad:.1f}%{precio_info}",
                    value=rentabilidad
                )
                alerts.append(alert)
                logger.info(
                    f"Alerta rentabilidad alta: {empresa} ({ticker}) - {rentabilidad:.1f}%"
                )
        
        return alerts
    
    def run_all_checks(
        self,
        df_analysis: pd.DataFrame,
        historical_data: dict[str, pd.DataFrame]
    ) -> list[Alert]:
        """
        Ejecuta todas las verificaciones de alertas.
        
        Args:
            df_analysis: DataFrame con el análisis de acciones.
            historical_data: Diccionario con datos históricos.
            
        Returns:
            Lista con todas las alertas generadas.
        """
        all_alerts = []
        
        logger.info("Ejecutando verificaciones de alertas...")
        
        all_alerts.extend(self.check_oversold_stocks(df_analysis, historical_data))
        all_alerts.extend(self.check_overbought_stocks(df_analysis, historical_data))
        all_alerts.extend(self.check_cross_signals(df_analysis, historical_data))
        all_alerts.extend(self.check_upcoming_dividends(df_analysis))
        all_alerts.extend(self.check_large_drops(df_analysis, historical_data))
        all_alerts.extend(self.check_high_expected_returns(df_analysis))
        
        logger.info(f"Total de alertas generadas: {len(all_alerts)}")
        
        return all_alerts
    
    async def send_telegram_alert(self, alert: Alert) -> bool:
        """
        Envía una alerta individual a Telegram.
        
        Args:
            alert: Alerta a enviar.
            
        Returns:
            True si se envió correctamente, False en caso contrario.
        """
        if not self._telegram_bot:
            logger.debug(f"Telegram no configurado. Alerta no enviada: {alert.message}")
            return False
        
        try:
            message = alert.to_telegram_message()
            await self._telegram_bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='Markdown'
            )
            logger.info(f"Alerta enviada a Telegram: {alert.ticker}")
            return True
        except Exception as e:
            logger.error(f"Error enviando alerta a Telegram: {e}")
            return False
    
    async def send_all_alerts(self, alerts: list[Alert]) -> int:
        """
        Envía todas las alertas a Telegram.
        
        Args:
            alerts: Lista de alertas a enviar.
            
        Returns:
            Número de alertas enviadas correctamente.
        """
        if not alerts:
            logger.info("No hay alertas para enviar")
            return 0
        
        sent_count = 0
        for alert in alerts:
            if await self.send_telegram_alert(alert):
                sent_count += 1
        
        logger.info(f"Alertas enviadas: {sent_count}/{len(alerts)}")
        return sent_count
    
    def send_telegram_alert_sync(self, alert: Alert) -> bool:
        """
        Versión síncrona de send_telegram_alert.
        
        Args:
            alert: Alerta a enviar.
            
        Returns:
            True si se envió correctamente, False en caso contrario.
        """
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Si ya hay un loop ejecutándose, crear una tarea
                return asyncio.ensure_future(self.send_telegram_alert(alert))
            else:
                return loop.run_until_complete(self.send_telegram_alert(alert))
        except RuntimeError:
            # No hay loop, crear uno nuevo
            return asyncio.run(self.send_telegram_alert(alert))
    
    def send_all_alerts_sync(self, alerts: list[Alert]) -> int:
        """
        Versión síncrona de send_all_alerts.
        
        Args:
            alerts: Lista de alertas a enviar.
            
        Returns:
            Número de alertas enviadas correctamente.
        """
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                return asyncio.ensure_future(self.send_all_alerts(alerts))
            else:
                return loop.run_until_complete(self.send_all_alerts(alerts))
        except RuntimeError:
            return asyncio.run(self.send_all_alerts(alerts))
