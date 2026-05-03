"""Tests for src/etl/functions.py"""

import numpy as np
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock

from etl.functions import (
    call_yf_api_historic,
    compute_alpha_beta,
    compute_sharpe_ratio,
    get_risk_free_rate,
    get_total_rank,
    interpretar_recomendacion,
    interpretar_sharpe,
    load_extraction_historic_parquet,
    save_extraction_historic_parquet,
)


# ---------------------------------------------------------------------------
# compute_sharpe_ratio
# ---------------------------------------------------------------------------

class TestComputeSharpeRatio:
    def test_normal_case_returns_float(self):
        df = pd.DataFrame(
            {'Daily Return': [0.01, -0.005, 0.008, 0.012, -0.003, 0.007, 0.006, -0.002, 0.009, 0.004]}
        )
        result = compute_sharpe_ratio(df, risk_free_rate=0.0)
        assert result is not None
        assert isinstance(result, float)

    def test_missing_daily_return_column_returns_none(self):
        df = pd.DataFrame({'Close': [100, 101, 102, 101, 103]})
        assert compute_sharpe_ratio(df) is None

    def test_zero_std_dev_returns_none(self):
        df = pd.DataFrame({'Daily Return': [0.01, 0.01, 0.01, 0.01, 0.01]})
        assert compute_sharpe_ratio(df) is None

    def test_positive_returns_yield_positive_sharpe(self):
        df = pd.DataFrame(
            {'Daily Return': [0.02, 0.015, 0.025, 0.01, 0.02, 0.015, 0.025, 0.01, 0.02, 0.015]}
        )
        result = compute_sharpe_ratio(df, risk_free_rate=0.0)
        assert result is not None
        assert result > 0

    def test_higher_risk_free_rate_lowers_sharpe(self):
        df = pd.DataFrame(
            {'Daily Return': [0.01, 0.02, 0.015, 0.01, 0.02, 0.015, 0.01, 0.02, 0.015, 0.01]}
        )
        sharpe_no_rf = compute_sharpe_ratio(df, risk_free_rate=0.0)
        sharpe_with_rf = compute_sharpe_ratio(df, risk_free_rate=0.02)
        assert sharpe_no_rf > sharpe_with_rf


# ---------------------------------------------------------------------------
# compute_alpha_beta
# ---------------------------------------------------------------------------

class TestComputeAlphaBeta:
    def _correlated_prices(self, n=100, seed=42):
        np.random.seed(seed)
        dates = pd.date_range('2024-01-01', periods=n, freq='D')
        bench_rets = np.random.normal(0.001, 0.01, n)
        stock_rets = 0.5 * bench_rets + np.random.normal(0, 0.005, n)
        bench = pd.Series(1000.0 * np.cumprod(1 + bench_rets), index=dates)
        stock = pd.Series(100.0 * np.cumprod(1 + stock_rets), index=dates)
        return stock, bench

    def test_normal_case_returns_floats(self):
        stock, bench = self._correlated_prices()
        alpha, beta = compute_alpha_beta(stock, bench)
        assert alpha is not None and beta is not None
        assert isinstance(alpha, float) and isinstance(beta, float)

    def test_empty_series_returns_none(self):
        empty = pd.Series(dtype=float)
        alpha, beta = compute_alpha_beta(empty, empty)
        assert alpha is None and beta is None

    def test_non_overlapping_dates_returns_none(self):
        dates_a = pd.date_range('2024-01-01', periods=10, freq='D')
        dates_b = pd.date_range('2024-06-01', periods=10, freq='D')
        stock = pd.Series([100.0 + i for i in range(10)], index=dates_a)
        bench = pd.Series([1000.0 + i for i in range(10)], index=dates_b)
        alpha, beta = compute_alpha_beta(stock, bench)
        assert alpha is None and beta is None

    def test_beta_approximates_true_value(self):
        """Beta should be close to the synthetic true value of 0.5."""
        stock, bench = self._correlated_prices(n=200, seed=0)
        _, beta = compute_alpha_beta(stock, bench)
        assert beta is not None
        assert abs(beta - 0.5) < 0.3


# ---------------------------------------------------------------------------
# interpretar_recomendacion
# ---------------------------------------------------------------------------

class TestInterpretarRecomendacion:
    def test_none_returns_none(self):
        assert interpretar_recomendacion(None) is None

    def test_strong_buy(self):
        assert "Strong Buy" in interpretar_recomendacion(1.0)
        assert "Strong Buy" in interpretar_recomendacion(1.4)

    def test_boundary_1_5_is_buy_not_strong_buy(self):
        result = interpretar_recomendacion(1.5)
        assert "Buy" in result
        assert "Strong" not in result

    def test_buy_range(self):
        assert "Buy" in interpretar_recomendacion(2.0)

    def test_hold_range(self):
        assert "Hold" in interpretar_recomendacion(3.0)

    def test_sell_range(self):
        result = interpretar_recomendacion(4.0)
        assert "Sell" in result or "Vender" in result

    def test_strong_sell(self):
        result = interpretar_recomendacion(4.5)
        assert "Strong Sell" in result or "fuerte" in result


# ---------------------------------------------------------------------------
# interpretar_sharpe
# ---------------------------------------------------------------------------

class TestInterpretarSharpe:
    def test_none_returns_none(self):
        assert interpretar_sharpe(None) is None

    def test_nan_returns_none(self):
        assert interpretar_sharpe(float('nan')) is None

    def test_negative_is_bad(self):
        result = interpretar_sharpe(-0.5)
        assert result is not None
        assert "Mala" in result or "peor" in result

    def test_low_sharpe(self):
        result = interpretar_sharpe(0.5)
        assert result is not None
        assert "baja" in result.lower() or "Rentabilidad" in result

    def test_acceptable(self):
        assert interpretar_sharpe(1.5) == "Aceptable"

    def test_good(self):
        assert interpretar_sharpe(2.5) == "Buena"

    def test_excellent(self):
        assert interpretar_sharpe(3.0) == "Excelente"
        assert interpretar_sharpe(5.0) == "Excelente"


# ---------------------------------------------------------------------------
# get_total_rank
# ---------------------------------------------------------------------------

class TestGetTotalRank:
    def _base_df(self):
        return pd.DataFrame({
            'P/E (Trailing)': [10.0, 20.0, 15.0],
            'Dividend Yield': [0.03, 0.02, 0.04],
            'P/B': [1.5, 2.0, 1.0],
        })

    def test_adds_rank_column(self):
        result = get_total_rank(self._base_df(), 'value_rank', [1, 1, 1])
        assert 'value_rank' in result.columns

    def test_negative_pe_handled_without_error(self):
        df = pd.DataFrame({
            'P/E (Trailing)': [-10.0, 20.0, 15.0],
            'Dividend Yield': [0.03, 0.02, 0.04],
            'P/B': [1.5, 2.0, 1.0],
        })
        result = get_total_rank(df, 'rank', [1, 1, 1])
        assert 'rank' in result.columns
        assert not result['rank'].isna().all()

    def test_wrong_weight_length_does_not_add_column(self):
        result = get_total_rank(self._base_df(), 'rank', [1, 1])
        assert 'rank' not in result.columns

    def test_rank_sum_equals_sum_of_weights(self):
        weights = [1, 1, 1]
        result = get_total_rank(self._base_df(), 'rank', weights)
        assert abs(result['rank'].sum() - sum(weights)) < 1e-9


# ---------------------------------------------------------------------------
# save / load parquet
# ---------------------------------------------------------------------------

class TestParquetIO:
    def test_roundtrip_preserves_data(self, tmp_path):
        data = {
            'Apple': pd.DataFrame({'Close': [150.0, 151.0, 152.0], 'Daily Return': [0.01, 0.007, -0.003]}),
            'Microsoft': pd.DataFrame({'Close': [300.0, 302.0, 301.0], 'Daily Return': [0.005, 0.007, -0.003]}),
        }
        save_path = str(tmp_path / 'test_data')
        save_extraction_historic_parquet(data, save_path)
        loaded = load_extraction_historic_parquet(save_path)

        assert set(loaded.keys()) == {'Apple', 'Microsoft'}
        assert 'Close' in loaded['Apple'].columns
        assert 'Daily Return' in loaded['Microsoft'].columns

    def test_special_characters_in_name(self, tmp_path):
        data = {'S&P 500': pd.DataFrame({'Close': [100.0, 101.0]})}
        save_path = str(tmp_path / 'special')
        save_extraction_historic_parquet(data, save_path)
        loaded = load_extraction_historic_parquet(save_path)
        assert 'S&P 500' in loaded

    def test_missing_directory_returns_empty_dict(self, tmp_path):
        result = load_extraction_historic_parquet(str(tmp_path / 'nonexistent'))
        assert result == {}

    def test_share_name_column_added_on_save(self, tmp_path):
        data = {'Tesla': pd.DataFrame({'Close': [200.0, 201.0]})}
        save_path = str(tmp_path / 'share_name_test')
        save_extraction_historic_parquet(data, save_path)
        loaded = load_extraction_historic_parquet(save_path)
        assert 'Tesla' in loaded


# ---------------------------------------------------------------------------
# get_risk_free_rate
# ---------------------------------------------------------------------------

class TestGetRiskFreeRate:
    def test_success_converts_annual_to_daily_rate(self):
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame({'Close': [5.25]})
        with patch('etl.functions.yf.Ticker', return_value=mock_ticker):
            rate = get_risk_free_rate()
        expected = (1 + 5.25 / 100) ** (1 / 252) - 1
        assert abs(rate - expected) < 1e-10

    def test_empty_data_returns_zero(self):
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame()
        with patch('etl.functions.yf.Ticker', return_value=mock_ticker):
            rate = get_risk_free_rate()
        assert rate == 0.0

    def test_exception_returns_zero(self):
        with patch('etl.functions.yf.Ticker', side_effect=Exception("Network error")):
            rate = get_risk_free_rate()
        assert rate == 0.0


# ---------------------------------------------------------------------------
# call_yf_api_historic
# ---------------------------------------------------------------------------

class TestCallYfApiHistoric:
    def _mock_data(self):
        dates = pd.date_range('2024-01-01', periods=5, freq='D')
        return pd.DataFrame(
            {'Close': [100.0, 101.0, 102.0, 101.0, 103.0],
             'Open': [99.0] * 5, 'High': [102.0] * 5,
             'Low': [98.0] * 5, 'Volume': [1000] * 5},
            index=dates,
        )

    def test_adds_daily_return_and_cumulative_return(self):
        with patch('etl.functions.yf.download', return_value=self._mock_data()):
            result = call_yf_api_historic('2024-01-01', '2024-01-05', 'AAPL')
        assert 'Daily Return' in result.columns
        assert 'Cumulative Return' in result.columns

    def test_multiindex_columns_are_flattened(self):
        dates = pd.date_range('2024-01-01', periods=5, freq='D')
        cols = pd.MultiIndex.from_tuples(
            [('Close', 'AAPL'), ('Open', 'AAPL'), ('High', 'AAPL'),
             ('Low', 'AAPL'), ('Volume', 'AAPL')],
            names=['Price', 'Ticker'],
        )
        mock_data = pd.DataFrame(
            [[100.0, 99.0, 102.0, 98.0, 1000],
             [101.0, 100.0, 103.0, 99.0, 2000],
             [102.0, 101.0, 104.0, 100.0, 1500],
             [101.0, 100.0, 103.0, 99.0, 1200],
             [103.0, 102.0, 105.0, 101.0, 1800]],
            index=dates, columns=cols,
        )
        with patch('etl.functions.yf.download', return_value=mock_data):
            result = call_yf_api_historic('2024-01-01', '2024-01-05', 'AAPL')
        assert not isinstance(result.columns, pd.MultiIndex)
        assert 'Daily Return' in result.columns
