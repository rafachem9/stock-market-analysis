import sys
import os
from unittest.mock import MagicMock

# Make src/ importable so all modules resolve correctly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# yfinance requires curl_cffi which cannot be built in this environment.
# Register a MagicMock so that `import yfinance as yf` in source modules
# succeeds; individual tests patch yf.Ticker / yf.download as needed.
sys.modules.setdefault('yfinance', MagicMock())

import pytest
import pandas as pd
from datetime import date, timedelta


@pytest.fixture
def price_df_rising():
    """16-row DataFrame with strongly rising Close prices → RSI near 100 on last row."""
    prices = [100.0 + i * 5.0 for i in range(15)] + [169.0]
    return pd.DataFrame({'Close': prices})


@pytest.fixture
def price_df_declining():
    """16-row DataFrame with strongly declining Close prices → RSI near 0 on last row."""
    prices = [170.0 - i * 5.0 for i in range(15)] + [101.0]
    return pd.DataFrame({'Close': prices})


@pytest.fixture
def price_df_with_daily_return():
    """DataFrame with Close and Daily Return columns (returns as fractions)."""
    prices = [100.0, 101.0, 102.0, 101.0, 103.0, 102.0, 104.0, 103.0, 105.0, 106.0]
    daily_returns = [float('nan')] + [
        (prices[i] - prices[i - 1]) / prices[i - 1] for i in range(1, len(prices))
    ]
    return pd.DataFrame({'Close': prices, 'Daily Return': daily_returns}).dropna()


@pytest.fixture
def alert_manager():
    """AlertManager without Telegram configured."""
    from etl.alerts import AlertManager
    return AlertManager(telegram_token='', chat_id='')


@pytest.fixture
def sample_analysis_df():
    """Minimal DataFrame mimicking the output of analysis_stock_hist."""
    today = date.today()
    return pd.DataFrame([
        {
            'Empresa': 'Apple',
            'Ticker': 'AAPL',
            'Rentabilidad prevista': 25.0,
            'Precio actual': 150.0,
            'Precio objetivo analistas': 187.5,
            'Ex-Dividend Date': today + timedelta(days=3),
            'Next Dividend': 0.25,
            'Dividend Yield': 0.015,
        },
        {
            'Empresa': 'Microsoft',
            'Ticker': 'MSFT',
            'Rentabilidad prevista': 5.0,
            'Precio actual': 300.0,
            'Precio objetivo analistas': 315.0,
            'Ex-Dividend Date': today + timedelta(days=60),
            'Next Dividend': 0.75,
            'Dividend Yield': 0.025,
        },
    ])
