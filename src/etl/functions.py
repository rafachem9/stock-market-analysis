from datetime import datetime, date
import yfinance as yf
import pandas as pd
from tqdm import tqdm
import numpy as np
import statsmodels.api as sm
import os

def get_risk_free_rate():
    """
    Obtiene el tipo de interés libre de riesgo (T-Bill 3M, ticker ^IRX) desde Yahoo Finance.
    Devuelve el valor diario equivalente (no anual).
    """
    try:
        t_bill = yf.Ticker("^IRX")
        data = t_bill.history(period="5d")  # últimos 5 días para evitar problemas de días festivos
        if data.empty:
            print("No se pudieron obtener datos para ^IRX. Usando 0 como tasa libre de riesgo.")
            return 0.0

        last_yield = data["Close"].iloc[-1] / 100.0  # convertir % a decimal

        # Pasar de anual a diario (252 días de mercado al año)
        risk_free_daily = (1 + last_yield) ** (1 / 252) - 1
        return risk_free_daily
    except Exception as e:
        print(f"Error al obtener tasa libre de riesgo: {e}. Usando 0.")
        return 0.0


def save_extraction_historic_parquet(data_his, path="data_historic"):
    """
    Guarda un diccionario de DataFrames en archivos parquet en el directorio especificado.
    (Versión corregida de la función original del notebook)
    """
    os.makedirs(path, exist_ok=True)
    for name, df in data_his.items():
        df_copy = df.copy()  # Evitar SettingWithCopyWarning
        df_copy['share_name'] = name
        filename = name.lower().replace(' ', '_').replace('.', '_').replace('/', '_')
        output_path = os.path.join(path, f"{filename}.parquet")
        df_copy.to_parquet(output_path, index=True)


def load_extraction_historic_parquet(path="data_historic"):
    """
    Carga archivos parquet de un directorio en un diccionario de DataFrames.
    """
    data_his = {}
    if not os.path.exists(path):
        print(f"Directorio no encontrado: {path}")
        return data_his

    for file in os.listdir(path):
        if file.endswith(".parquet"):
            name = file.replace(".parquet", "")
            try:
                df = pd.read_parquet(os.path.join(path, file))
                # El nombre de la acción se infiere del nombre del fichero,
                # pero la función analysis_stock_hist lo saca del diccionario.
                # Restauramos el nombre original (el del diccionario) como clave.
                # Esto asume que el analysis_stock_hist usará las claves del dict.
                # La función de guardado original usaba las claves del dict para el nombre.
                # Esta carga recuperará el nombre del archivo, que es una versión 'slug'
                # Para que coincida, carguemos el 'share_name' guardado si existe.
                if 'share_name' in df.columns:
                    original_name = df['share_name'].iloc[0]
                    data_his[original_name] = df
                else:
                    data_his[name] = df  # Fallback por si 'share_name' no se guardó
            except Exception as e:
                print(f"Error al cargar {file}: {e}")
    return data_his


def compute_sharpe_ratio(data, risk_free_rate=0):
    """
    Calcula el Sharpe Ratio para los retornos diarios de un activo.
    """
    if "Daily Return" not in data.columns or data["Daily Return"].std() == 0:
        return None
    mean_return = data["Daily Return"].mean()
    std = data["Daily Return"].std()
    sharpe_ratio = (mean_return - risk_free_rate) / std
    return sharpe_ratio


def compute_alpha_beta(stock_data, benchmark_data):
    """
    Calcula Alpha y Beta de un activo (precios) respecto a un benchmark (precios).
    stock_data y benchmark_data deben ser Series de precios de cierre.
    """
    # Alinear índices de fechas
    data = pd.merge(
        stock_data.rename("stock"),
        benchmark_data.rename("benchmark"),
        left_index=True,
        right_index=True,
        how="left"
    ).dropna()

    if data.empty or len(data) < 2:
        return None, None

    stock_returns = data.iloc[:, 0].pct_change(1).dropna()
    benchmark_returns = data.iloc[:, 1].pct_change(1).dropna()

    if stock_returns.empty or benchmark_returns.empty:
        return None, None

    # Regresión lineal: stock = alpha + beta * benchmark
    X = sm.add_constant(benchmark_returns)
    model = sm.OLS(stock_returns, X).fit()
    alpha, beta = model.params

    return alpha, beta


def call_yf_api_historic(start_period, end_period, ticker):
    """
    Descarga datos históricos para un ticker y calcula retornos.
    """
    data = yf.download(ticker, start_period, end_period, auto_adjust=True)
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.droplevel('Ticker')
    data["Daily Return"] = data["Close"].pct_change(1)
    data = data.dropna()
    data["Cumulative Return"] = (1 + data["Daily Return"]).cumprod() - 1
    return data


def extraction_historic(start_period, end_period, tickers):
    """
    Ejecuta la extracción histórica para un diccionario de tickers.
    """
    data_his = {}

    for ticker in tqdm(tickers, desc="Procesando tickers (extracción histórica)"):
        name_ticker = tickers[ticker]
        try:
            data_his[name_ticker] = call_yf_api_historic(start_period, end_period, ticker)
        except Exception as e:
            print(f"Error al descargar {ticker} ({name_ticker}): {e}")
            data_his[name_ticker] = pd.DataFrame()  # DataFrame vacío si falla
    return data_his


def interpretar_recomendacion(val):
    """
    Interpreta el valor numérico de la recomendación de analistas.
    """
    if val is None:
        return None
    elif val < 1.5:
        return "Compra fuerte (Strong Buy)"
    elif val < 2.5:
        return "Compra (Buy)"
    elif val < 3.5:
        return "Mantener (Hold)"
    elif val < 4.5:
        return "Vender (Underperform / Sell)"
    else:
        return "Vender fuerte (Strong Sell)"


def interpretar_sharpe(sharpe):
    """
    Interpreta el valor del Sharpe Ratio.
    """
    if sharpe is None or pd.isna(sharpe):
        return None
    elif sharpe < 0:
        return "Mala inversión (rinde peor que activo libre de riesgo)"
    elif sharpe < 1:
        return "Rentabilidad baja para el riesgo asumido"
    elif sharpe < 2:
        return "Aceptable"
    elif sharpe < 3:
        return "Buena"
    else:
        return "Excelente"


def analysis_stock_hist(df_raw, tickers, bechmark_df):
    """
    Realiza el análisis completo para un diccionario de DataFrames de acciones.
    """
    rows = []

    # Obtener la tasa libre de riesgo una vez
    risk_free_rate = get_risk_free_rate()
    print(f"Tasa libre de riesgo diaria (T-Bill 3M): {risk_free_rate:.6f}")

    for name, df in tqdm(df_raw.items(), desc="Procesando tickers (análisis)"):
        ticker = next((k for k, v in tickers.items() if v == name), None)
        if ticker is None or df.empty or len(df) < 2:
            print(f"Omitiendo {name} (ticker no encontrado o datos insuficientes)")
            continue

        try:
            # Fechas de referencia
            end_date = df.index[-1]
            one_month_ago = end_date - pd.DateOffset(months=1)
            two_months_ago = end_date - pd.DateOffset(months=2)
            three_months_ago = end_date - pd.DateOffset(months=3)

            # Filtramos precios desde esas fechas más cercanas
            price_now = df["Close"].iloc[-1]

            # Asegurarse de que las fechas existen en el índice
            price_1m_ago = df[df.index >= one_month_ago]["Close"].iloc[0] if not df[
                df.index >= one_month_ago].empty else np.nan
            price_2m_ago = df[df.index >= two_months_ago]["Close"].iloc[0] if not df[
                df.index >= two_months_ago].empty else np.nan
            price_3m_ago = df[df.index >= three_months_ago]["Close"].iloc[0] if not df[
                df.index >= three_months_ago].empty else np.nan

            # Calculamos retornos acumulados
            ret_1m = ((price_now / price_1m_ago) - 1) * 100 if not pd.isna(price_1m_ago) else np.nan
            ret_2m = ((price_now / price_2m_ago) - 1) * 100 if not pd.isna(price_2m_ago) else np.nan
            ret_3m = ((price_now / price_3m_ago) - 1) * 100 if not pd.isna(price_3m_ago) else np.nan

            df["Daily Return"] = df["Close"].pct_change()
            volatilidad = df["Daily Return"].std()
            precio_actual = df["Close"].iloc[-1]

            # Datos de Yahoo Finance
            company_data = yf.Ticker(ticker).info
            sector = company_data.get("sector")
            industry = company_data.get("industry")
            market_cap = company_data.get("marketCap")
            recommendation = company_data.get("recommendationMean")
            target_price = company_data.get("targetMeanPrice")
            recommendation_interpratation = interpretar_recomendacion(recommendation)

            sharpe_ratio = compute_sharpe_ratio(df, risk_free_rate)
            sharpe_interpretation = interpretar_sharpe(sharpe_ratio)
            alpha, beta_calculated = compute_alpha_beta(df["Close"], bechmark_df["Close"])

            dividend_yield = company_data.get("dividendYield")
            pe_trailing = company_data.get("trailingPE")
            pe_forward = company_data.get("forwardPE")
            pb = company_data.get("priceToBook")
            volume = company_data.get("volume")
            beta = company_data.get("beta")

            # Próximo dividendo
            timestamp = company_data.get("exDividendDate")
            ex_dividend_date = datetime.fromtimestamp(timestamp).date() if timestamp else None
            dividend_rate = company_data.get("dividendRate")  # dividendo anual
            next_dividend = round(dividend_rate / 4, 4) if dividend_rate else None  # Aproximación trimestral

            rentabilidad_prevista = round((target_price - precio_actual) / precio_actual * 100,
                                          1) if target_price and precio_actual != 0 else None

            rows.append({
                "Empresa": name,
                "Ticker": ticker,
                "Sector": sector,
                "Industria": industry,
                "Capitalización mercado": market_cap,
                "Retorno 1 mes": ret_1m,
                "Retorno 2 meses": ret_2m,
                "Retorno 3 meses": ret_3m,
                "Precio actual": precio_actual,
                "Precio objetivo analistas": target_price,
                "Rentabilidad prevista": rentabilidad_prevista,
                "Valoración analistas": recommendation,
                "Interpretacion recomendacion": recommendation_interpratation,
                "sharpe_ratio": sharpe_ratio,
                "Interpretacion Sharpe": sharpe_interpretation,
                "volatilidad": volatilidad,
                "alpha": alpha,
                "beta_calculada": beta_calculated,
                "Dividend Yield": dividend_yield,
                "P/E (Trailing)": pe_trailing,
                "P/E (Forward)": pe_forward,
                "P/B": pb,
                "Volumen": volume,
                "beta": beta,
                "Ex-Dividend Date": ex_dividend_date,
                "Next Dividend": next_dividend,
            })
        except Exception as e:
            print(f"Error procesando el análisis de {name} ({ticker}): {e}")

    df_ranking = pd.DataFrame(rows)
    return df_ranking.sort_values('Rentabilidad prevista', ascending=False, na_position='last')


def get_total_rank(df, rank_name, weight):
    """
    Calcula un ranking ponderado basado en P/E, Dividend Yield y P/B.
    """
    if len(weight) == 3:
        df_calc = df.copy()

        # Reemplazar valores no positivos en P/E y P/B por NaN para evitar divisiones por cero o resultados incorrectos
        df_calc["P/E (Trailing)"] = df_calc["P/E (Trailing)"].apply(lambda x: x if x > 0 else np.nan)
        df_calc["P/B"] = df_calc["P/B"].apply(lambda x: x if x > 0 else np.nan)
        df_calc["Dividend Yield"] = df_calc["Dividend Yield"].apply(lambda x: x if x > 0 else np.nan)

        # Normalización ponderada (inversa para P/E y P/B, directa para DY)
        # Se manejan NaNs en la suma para que no den error
        peso_pe = (1 / df_calc["P/E (Trailing)"]) / (1 / df_calc["P/E (Trailing)"]).sum() * weight[0]
        peso_dy = (df_calc["Dividend Yield"] / df_calc["Dividend Yield"].sum()) * weight[1]
        peso_pb = (1 / df_calc["P/B"]) / (1 / df_calc["P/B"]).sum() * weight[2]

        # Rellenar NaNs con 0 después de la ponderación para poder sumar
        df_calc["Peso_PE"] = peso_pe.fillna(0)
        df_calc["Peso_DY"] = peso_dy.fillna(0)
        df_calc["Peso_PB"] = peso_pb.fillna(0)

        # Sumatorio total
        df[rank_name] = (
                df_calc["Peso_PE"] +
                df_calc["Peso_DY"] +
                df_calc["Peso_PB"]
        )
    else:
        print('La lista de pesos (weight) no tiene la longitud correcta (3).')
    return df
