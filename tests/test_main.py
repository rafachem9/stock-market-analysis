"""Tests for src/main.py"""

import pytest
from datetime import datetime

from main import format_alerts_summary
from etl.alerts import Alert, AlertType


def _make_alert(alert_type, ticker='TICK', company='Company'):
    return Alert(
        alert_type=alert_type,
        ticker=ticker,
        company_name=company,
        message='test message',
        timestamp=datetime.now(),
    )


def test_empty_list_returns_no_alerts_message():
    result = format_alerts_summary([], 'IBEX 35')
    assert 'No se generaron alertas' in result
    assert 'IBEX 35' in result


def test_alert_count_in_summary():
    alerts = [
        _make_alert(AlertType.RSI_OVERSOLD, 'AAPL', 'Apple'),
        _make_alert(AlertType.LARGE_DROP, 'MSFT', 'Microsoft'),
        _make_alert(AlertType.RSI_OVERSOLD, 'GOOG', 'Google'),
    ]
    result = format_alerts_summary(alerts, 'SP500')
    assert '3 alertas' in result
    assert 'SP500' in result


def test_alerts_grouped_by_type():
    alerts = [
        _make_alert(AlertType.RSI_OVERSOLD, 'AAPL', 'Apple'),
        _make_alert(AlertType.RSI_OVERSOLD, 'MSFT', 'Microsoft'),
        _make_alert(AlertType.LARGE_DROP, 'GOOG', 'Google'),
    ]
    result = format_alerts_summary(alerts, 'SP500')
    assert AlertType.RSI_OVERSOLD.value in result
    assert AlertType.LARGE_DROP.value in result


def test_more_than_three_per_type_shows_truncation():
    alerts = [_make_alert(AlertType.RSI_OVERSOLD, f'T{i}', f'Co{i}') for i in range(5)]
    result = format_alerts_summary(alerts, 'Test')
    assert 'y 2 más' in result


def test_single_alert_type_shows_company_name():
    alerts = [_make_alert(AlertType.HIGH_EXPECTED_RETURN, 'AAPL', 'Apple')]
    result = format_alerts_summary(alerts, 'Test')
    assert 'Apple' in result
