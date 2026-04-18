"""Tests for src/etl/alerts.py"""

import pandas as pd
import pytest
from datetime import date, timedelta
from unittest.mock import patch

from etl.alerts import (
    Alert,
    AlertManager,
    AlertType,
    compute_moving_averages,
    compute_rsi,
    detect_cross_signals,
)


# ---------------------------------------------------------------------------
# compute_rsi
# ---------------------------------------------------------------------------

class TestComputeRsi:
    def test_returns_series_of_same_length(self, price_df_rising):
        rsi = compute_rsi(price_df_rising)
        assert isinstance(rsi, pd.Series)
        assert len(rsi) == len(price_df_rising)

    def test_declining_prices_produce_low_rsi(self, price_df_declining):
        rsi = compute_rsi(price_df_declining)
        assert not rsi.empty
        assert not pd.isna(rsi.iloc[-1])
        assert rsi.iloc[-1] < 30

    def test_rising_prices_produce_high_rsi(self, price_df_rising):
        rsi = compute_rsi(price_df_rising)
        assert not rsi.empty
        assert not pd.isna(rsi.iloc[-1])
        assert rsi.iloc[-1] > 70

    def test_insufficient_data_returns_empty_series(self):
        df = pd.DataFrame({'Close': [100.0, 101.0, 102.0]})
        rsi = compute_rsi(df, period=14)
        assert rsi.empty

    def test_missing_close_column_returns_empty_series(self):
        df = pd.DataFrame({'Price': [100.0, 101.0, 102.0]})
        rsi = compute_rsi(df)
        assert rsi.empty

    def test_valid_values_are_between_0_and_100(self, price_df_rising):
        rsi = compute_rsi(price_df_rising)
        valid = rsi.dropna()
        assert len(valid) > 0
        assert (valid >= 0).all()
        assert (valid <= 100).all()


# ---------------------------------------------------------------------------
# compute_moving_averages
# ---------------------------------------------------------------------------

class TestComputeMovingAverages:
    def test_normal_case_both_ma_valid(self):
        df = pd.DataFrame({'Close': list(range(1, 11))})
        ma_short, ma_long = compute_moving_averages(df, short_period=3, long_period=5)
        assert not pd.isna(ma_short.iloc[-1])
        assert not pd.isna(ma_long.iloc[-1])

    def test_missing_close_column_returns_empty_series(self):
        df = pd.DataFrame({'Price': [100.0, 101.0]})
        ma_short, ma_long = compute_moving_averages(df)
        assert ma_short.empty
        assert ma_long.empty

    def test_insufficient_data_long_ma_is_nan(self):
        df = pd.DataFrame({'Close': [100.0] * 100})
        ma_short, ma_long = compute_moving_averages(df, short_period=50, long_period=200)
        assert not pd.isna(ma_short.iloc[-1])
        assert pd.isna(ma_long.iloc[-1])


# ---------------------------------------------------------------------------
# detect_cross_signals
# ---------------------------------------------------------------------------

class TestDetectCrossSignals:
    def test_insufficient_data_returns_false_false(self):
        df = pd.DataFrame({'Close': [100.0] * 100})
        golden, death = detect_cross_signals(df)
        assert golden is False
        assert death is False

    def test_golden_cross_detected(self):
        data = pd.DataFrame({'Close': [100.0] * 202})
        # MA short was below MA long yesterday, crosses above today
        ma_short = pd.Series([99.0] * 200 + [99.0, 101.0])
        ma_long = pd.Series([100.0] * 202)
        with patch('etl.alerts.compute_moving_averages', return_value=(ma_short, ma_long)):
            golden, death = detect_cross_signals(data)
        assert golden == True   # noqa: E712  (may return np.bool_)
        assert death == False   # noqa: E712

    def test_death_cross_detected(self):
        data = pd.DataFrame({'Close': [100.0] * 202})
        # MA short was above MA long yesterday, crosses below today
        ma_short = pd.Series([101.0] * 200 + [101.0, 99.0])
        ma_long = pd.Series([100.0] * 202)
        with patch('etl.alerts.compute_moving_averages', return_value=(ma_short, ma_long)):
            golden, death = detect_cross_signals(data)
        assert golden == False  # noqa: E712
        assert death == True    # noqa: E712

    def test_no_cross_when_already_above(self):
        data = pd.DataFrame({'Close': [100.0] * 202})
        ma_short = pd.Series([105.0] * 202)
        ma_long = pd.Series([100.0] * 202)
        with patch('etl.alerts.compute_moving_averages', return_value=(ma_short, ma_long)):
            golden, death = detect_cross_signals(data)
        assert golden == False  # noqa: E712
        assert death == False   # noqa: E712


# ---------------------------------------------------------------------------
# Alert dataclass
# ---------------------------------------------------------------------------

class TestAlertToTelegramMessage:
    def test_contains_ticker_and_company(self):
        alert = Alert(
            alert_type=AlertType.RSI_OVERSOLD,
            ticker='AAPL',
            company_name='Apple',
            message='RSI very low',
        )
        msg = alert.to_telegram_message()
        assert 'AAPL' in msg
        assert 'Apple' in msg

    def test_golden_cross_has_correct_emoji(self):
        alert = Alert(
            alert_type=AlertType.GOLDEN_CROSS,
            ticker='AAPL',
            company_name='Apple',
            message='Golden Cross!',
        )
        assert '📈' in alert.to_telegram_message()

    def test_death_cross_has_correct_emoji(self):
        alert = Alert(
            alert_type=AlertType.DEATH_CROSS,
            ticker='AAPL',
            company_name='Apple',
            message='Death Cross!',
        )
        assert '📉' in alert.to_telegram_message()


# ---------------------------------------------------------------------------
# AlertManager.check_oversold_stocks
# ---------------------------------------------------------------------------

class TestCheckOversoldStocks:
    def test_detects_oversold_stock(self, alert_manager, price_df_declining):
        df = pd.DataFrame([{'Empresa': 'Apple', 'Ticker': 'AAPL'}])
        hist = {'Apple': price_df_declining}
        alerts = alert_manager.check_oversold_stocks(df, hist, threshold=30)
        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.RSI_OVERSOLD
        assert alerts[0].ticker == 'AAPL'

    def test_no_alert_when_not_oversold(self, alert_manager, price_df_rising):
        df = pd.DataFrame([{'Empresa': 'Apple', 'Ticker': 'AAPL'}])
        hist = {'Apple': price_df_rising}
        alerts = alert_manager.check_oversold_stocks(df, hist, threshold=30)
        assert len(alerts) == 0

    def test_skips_company_not_in_historical_data(self, alert_manager):
        df = pd.DataFrame([{'Empresa': 'Unknown', 'Ticker': 'UNK'}])
        hist = {'Apple': pd.DataFrame({'Close': [100.0]})}
        alerts = alert_manager.check_oversold_stocks(df, hist)
        assert len(alerts) == 0

    def test_skips_empty_historical_dataframe(self, alert_manager):
        df = pd.DataFrame([{'Empresa': 'Apple', 'Ticker': 'AAPL'}])
        hist = {'Apple': pd.DataFrame()}
        alerts = alert_manager.check_oversold_stocks(df, hist)
        assert len(alerts) == 0


# ---------------------------------------------------------------------------
# AlertManager.check_overbought_stocks
# ---------------------------------------------------------------------------

class TestCheckOverboughtStocks:
    def test_detects_overbought_stock(self, alert_manager, price_df_rising):
        df = pd.DataFrame([{'Empresa': 'Apple', 'Ticker': 'AAPL'}])
        hist = {'Apple': price_df_rising}
        alerts = alert_manager.check_overbought_stocks(df, hist, threshold=70)
        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.RSI_OVERBOUGHT

    def test_no_alert_when_not_overbought(self, alert_manager, price_df_declining):
        df = pd.DataFrame([{'Empresa': 'Apple', 'Ticker': 'AAPL'}])
        hist = {'Apple': price_df_declining}
        alerts = alert_manager.check_overbought_stocks(df, hist, threshold=70)
        assert len(alerts) == 0

    def test_skips_empty_historical_dataframe(self, alert_manager):
        df = pd.DataFrame([{'Empresa': 'Apple', 'Ticker': 'AAPL'}])
        hist = {'Apple': pd.DataFrame()}
        alerts = alert_manager.check_overbought_stocks(df, hist)
        assert len(alerts) == 0


# ---------------------------------------------------------------------------
# AlertManager.check_cross_signals
# ---------------------------------------------------------------------------

class TestCheckCrossSignals:
    def test_detects_golden_cross(self, alert_manager):
        df = pd.DataFrame([{'Empresa': 'Apple', 'Ticker': 'AAPL'}])
        hist = {'Apple': pd.DataFrame({'Close': [100.0] * 202})}
        with patch('etl.alerts.detect_cross_signals', return_value=(True, False)):
            alerts = alert_manager.check_cross_signals(df, hist)
        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.GOLDEN_CROSS

    def test_detects_death_cross(self, alert_manager):
        df = pd.DataFrame([{'Empresa': 'Apple', 'Ticker': 'AAPL'}])
        hist = {'Apple': pd.DataFrame({'Close': [100.0] * 202})}
        with patch('etl.alerts.detect_cross_signals', return_value=(False, True)):
            alerts = alert_manager.check_cross_signals(df, hist)
        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.DEATH_CROSS

    def test_no_cross_generates_no_alerts(self, alert_manager):
        df = pd.DataFrame([{'Empresa': 'Apple', 'Ticker': 'AAPL'}])
        hist = {'Apple': pd.DataFrame({'Close': [100.0] * 202})}
        with patch('etl.alerts.detect_cross_signals', return_value=(False, False)):
            alerts = alert_manager.check_cross_signals(df, hist)
        assert len(alerts) == 0


# ---------------------------------------------------------------------------
# AlertManager.check_upcoming_dividends
# ---------------------------------------------------------------------------

class TestCheckUpcomingDividends:
    def test_detects_dividend_within_window(self, alert_manager, sample_analysis_df):
        # Apple has ex_div in 3 days, inside the 7-day window
        df = sample_analysis_df[sample_analysis_df['Empresa'] == 'Apple']
        alerts = alert_manager.check_upcoming_dividends(df, days=7)
        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.DIVIDEND_UPCOMING

    def test_no_alert_for_distant_dividend(self, alert_manager, sample_analysis_df):
        # Microsoft has ex_div in 60 days, outside the 7-day window
        df = sample_analysis_df[sample_analysis_df['Empresa'] == 'Microsoft']
        alerts = alert_manager.check_upcoming_dividends(df, days=7)
        assert len(alerts) == 0

    def test_string_date_is_parsed_correctly(self, alert_manager):
        today = date.today()
        ex_div = today + timedelta(days=3)
        df = pd.DataFrame([{
            'Empresa': 'Apple', 'Ticker': 'AAPL',
            'Ex-Dividend Date': ex_div.strftime('%Y-%m-%d'),
            'Next Dividend': 0.25, 'Dividend Yield': 0.015,
        }])
        alerts = alert_manager.check_upcoming_dividends(df, days=7)
        assert len(alerts) == 1

    def test_none_date_is_skipped(self, alert_manager):
        df = pd.DataFrame([{
            'Empresa': 'Apple', 'Ticker': 'AAPL',
            'Ex-Dividend Date': None,
            'Next Dividend': 0.25, 'Dividend Yield': 0.015,
        }])
        alerts = alert_manager.check_upcoming_dividends(df)
        assert len(alerts) == 0

    def test_boundary_day_triggers_alert(self, alert_manager):
        """Dividend exactly at the threshold day should still trigger."""
        today = date.today()
        ex_div = today + timedelta(days=7)
        df = pd.DataFrame([{
            'Empresa': 'Apple', 'Ticker': 'AAPL',
            'Ex-Dividend Date': ex_div,
            'Next Dividend': 0.25, 'Dividend Yield': 0.015,
        }])
        alerts = alert_manager.check_upcoming_dividends(df, days=7)
        assert len(alerts) == 1


# ---------------------------------------------------------------------------
# AlertManager.check_large_drops
# ---------------------------------------------------------------------------

class TestCheckLargeDrops:
    def test_detects_large_drop(self, alert_manager):
        df = pd.DataFrame([{'Empresa': 'Apple', 'Ticker': 'AAPL'}])
        hist = {'Apple': pd.DataFrame({
            'Close': [100.0, 101.0, 100.0, 94.0],
            'Daily Return': [0.01, -0.0099, -0.06, -0.06],
        })}
        alerts = alert_manager.check_large_drops(df, hist, threshold=5.0)
        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.LARGE_DROP
        assert alerts[0].value < -5.0

    def test_no_alert_for_small_drop(self, alert_manager):
        df = pd.DataFrame([{'Empresa': 'Apple', 'Ticker': 'AAPL'}])
        hist = {'Apple': pd.DataFrame({
            'Close': [100.0, 101.0, 99.0],
            'Daily Return': [0.01, 0.01, -0.02],
        })}
        alerts = alert_manager.check_large_drops(df, hist, threshold=5.0)
        assert len(alerts) == 0

    def test_skips_df_without_daily_return_column(self, alert_manager):
        df = pd.DataFrame([{'Empresa': 'Apple', 'Ticker': 'AAPL'}])
        hist = {'Apple': pd.DataFrame({'Close': [100.0, 94.0]})}
        alerts = alert_manager.check_large_drops(df, hist, threshold=5.0)
        assert len(alerts) == 0


# ---------------------------------------------------------------------------
# AlertManager.check_high_expected_returns
# ---------------------------------------------------------------------------

class TestCheckHighExpectedReturns:
    def test_detects_high_return(self, alert_manager, sample_analysis_df):
        # Apple has 25% expected return (above 20% threshold)
        df = sample_analysis_df[sample_analysis_df['Empresa'] == 'Apple']
        alerts = alert_manager.check_high_expected_returns(df, threshold=20.0)
        assert len(alerts) == 1
        assert alerts[0].alert_type == AlertType.HIGH_EXPECTED_RETURN

    def test_no_alert_below_threshold(self, alert_manager, sample_analysis_df):
        # Microsoft has 5% expected return (below 20% threshold)
        df = sample_analysis_df[sample_analysis_df['Empresa'] == 'Microsoft']
        alerts = alert_manager.check_high_expected_returns(df, threshold=20.0)
        assert len(alerts) == 0

    def test_skips_nan_rentabilidad(self, alert_manager):
        df = pd.DataFrame([{
            'Empresa': 'Apple', 'Ticker': 'AAPL',
            'Rentabilidad prevista': float('nan'),
            'Precio actual': 150.0, 'Precio objetivo analistas': 200.0,
        }])
        alerts = alert_manager.check_high_expected_returns(df, threshold=20.0)
        assert len(alerts) == 0


# ---------------------------------------------------------------------------
# AlertManager.run_all_checks
# ---------------------------------------------------------------------------

class TestRunAllChecks:
    def test_combines_alerts_from_all_checks(
        self, alert_manager, sample_analysis_df, price_df_declining
    ):
        hist = {'Apple': price_df_declining, 'Microsoft': price_df_declining}
        alerts = alert_manager.run_all_checks(sample_analysis_df, hist)
        assert isinstance(alerts, list)
        # Oversold RSI x2 + upcoming dividend (Apple) + high expected return (Apple)
        assert len(alerts) >= 3

    def test_empty_dataframe_returns_empty_list(self, alert_manager):
        df = pd.DataFrame(columns=['Empresa', 'Ticker'])
        alerts = alert_manager.run_all_checks(df, {})
        assert alerts == []
