"""Tests for src/config.py"""

from config import get_config_summary


def test_returns_dict():
    assert isinstance(get_config_summary(), dict)


def test_has_required_keys():
    summary = get_config_summary()
    required = [
        'project_dir', 'data_dir', 'log_level', 'rsi_period',
        'rsi_thresholds', 'dividend_alert_days', 'daily_drop_threshold',
        'expected_return_threshold', 'telegram_configured',
    ]
    for key in required:
        assert key in summary, f"Missing key: {key}"


def test_excludes_sensitive_credentials():
    summary = get_config_summary()
    for forbidden in ('TELEGRAM_BOT_TOKEN', 'telegram_token', 'TELEGRAM_CHAT_ID', 'bot_token'):
        assert forbidden not in summary


def test_rsi_thresholds_oversold_less_than_overbought():
    thresholds = get_config_summary()['rsi_thresholds']
    assert 'oversold' in thresholds
    assert 'overbought' in thresholds
    assert thresholds['oversold'] < thresholds['overbought']


def test_telegram_configured_is_bool():
    assert isinstance(get_config_summary()['telegram_configured'], bool)
