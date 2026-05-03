#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Análisis de cartera de inversión personal.

Lee un fichero CSV con las operaciones de compra/venta y:
  - Calcula la posición actual (acciones abiertas) con precio actual vía yfinance
  - Muestra P&L latente por posición y total
  - Resume operaciones cerradas (SOLD) y fondos (FUND)
  - Descarga información de dividendos: yield, importe/acción y próxima fecha ex-div
  - Exporta un CSV actualizado con todos los datos enriquecidos
  - Desglosa la cartera por tipo (SHARE / ETF / FUND), empresa y año

Uso:
    python main.py [ruta_al_csv]

Si no se pasa argumento, busca 'data/cartera.csv' en la raíz del proyecto.
El separador se detecta automáticamente (coma, punto y coma o tabulador).
Genera 'cartera_actualizada.csv' en el mismo directorio que el CSV de entrada.
"""

import sys
import warnings
from pathlib import Path

import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CSV_PATH = PROJECT_ROOT / "data" / "cartera.csv"

# Columnas esperadas en el Excel (minúsculas, sin espacios extra)
COL_MAP = {
    "empresa": "empresa",
    "indice": "indice",
    "tipo": "tipo",
    "divisa": "divisa",
    "strategy": "strategy",
    "buy date": "buy_date",
    "buy_date": "buy_date",
    "sale date": "sale_date",
    "sale_date": "sale_date",
    "vendida": "estado",
    "year": "year",
    "share price": "precio_compra",
    "share_price": "precio_compra",
    "share number": "num_acciones",
    "share_number": "num_acciones",
    "fee in": "comision",
    "fee_in": "comision",
    "invertido total": "invertido_total",
    "invertido_total": "invertido_total",
    # Columnas de venta (solo aplican a filas SOLD)
    "share price now": "precio_venta",
    "share_price_now": "precio_venta",
    "liquido": "liquido",
    "fee out": "comision_venta",
    "fee_out": "comision_venta",
    "gross earning": "ganancia_bruta",
    "gross_earning": "ganancia_bruta",
}

EXCHANGE_SUFFIX = {
    "BME": ".MC",
    "FRA": ".F",
    "AMS": ".AS",
    "EPA": ".PA",
    "NYSE": "",
    "XETRA": ".DE",
    "LSE": ".L",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def parse_euro(value) -> float:
    """Convierte '1.234,56 €' o '1,23 €' a float."""
    if pd.isna(value):
        return 0.0
    s = str(value).strip()
    s = s.replace("€", "").replace(" ", "")
    # Formato europeo: punto=miles, coma=decimal
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def parse_number(value) -> float:
    """Convierte '20,000' (número de acciones) a float."""
    if pd.isna(value):
        return 0.0
    s = str(value).strip()
    # Si tiene punto y coma → europeo
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def indice_to_yf_ticker(indice: str) -> str | None:
    """Convierte 'BME:ACX' → 'ACX.MC' para yfinance."""
    if not indice or pd.isna(indice):
        return None
    indice = str(indice).strip()
    if ":" not in indice:
        return None
    exchange, ticker = indice.split(":", 1)
    suffix = EXCHANGE_SUFFIX.get(exchange.upper(), None)
    if suffix is None:
        return None
    ticker_yf = ticker.replace(".", "-")  # BRK.B → BRK-B
    return f"{ticker_yf}{suffix}"


def fmt(value: float, decimals: int = 2, suffix: str = " €") -> str:
    return f"{value:,.{decimals}f}{suffix}"


def pct(value: float) -> str:
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.2f}%"


def section(title: str):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


# ---------------------------------------------------------------------------
# Carga y limpieza del Excel
# ---------------------------------------------------------------------------


def _detect_separator(path: str) -> str:
    """Detecta el separador del CSV probando coma, punto y coma y tabulador."""
    with open(path, encoding="utf-8", errors="replace") as f:
        sample = f.read(4096)
    counts = {",": sample.count(","), ";": sample.count(";"), "\t": sample.count("\t")}
    return max(counts, key=counts.get)


def load_portfolio(path: str) -> pd.DataFrame:
    sep = _detect_separator(path)
    sep_name = {"," : "coma", ";": "punto y coma", "\t": "tabulador"}.get(sep, sep)
    print(f"Leyendo '{path}' (separador: {sep_name})...")

    # Intentar detectar fila de cabecera
    raw = pd.read_csv(path, sep=sep, header=None, encoding="utf-8", on_bad_lines="skip")

    header_row = 0
    for i, row in raw.iterrows():
        vals = [str(v).lower().strip() for v in row if not pd.isna(v)]
        if "empresa" in vals and ("indice" in vals or "tipo" in vals):
            header_row = i
            break

    df = pd.read_csv(path, sep=sep, header=header_row, encoding="utf-8", on_bad_lines="skip")

    # Normalizar nombres de columnas
    df.columns = [str(c).lower().strip() for c in df.columns]

    rename = {}
    for col in df.columns:
        if col in COL_MAP:
            rename[col] = COL_MAP[col]
    df = df.rename(columns=rename)

    required = ["empresa", "estado"]
    for r in required:
        if r not in df.columns:
            raise ValueError(
                f"No se encontró la columna '{r}'. "
                f"Columnas disponibles: {list(df.columns)}"
            )

    # Eliminar filas sin empresa o sin estado
    df = df.dropna(subset=["empresa"])
    df["estado"] = df["estado"].astype(str).str.upper().str.strip()
    df = df[df["estado"].isin(["BOUGHT", "SOLD", "FUND"])]

    # Conversión de tipos — columnas de compra
    for col in ["precio_compra", "comision", "invertido_total"]:
        if col in df.columns:
            df[col] = df[col].apply(parse_euro)

    # Columnas de venta: parsear y luego ignorar en filas BOUGHT
    for col in ["precio_venta", "liquido", "comision_venta", "ganancia_bruta"]:
        if col in df.columns:
            df[col] = df[col].apply(parse_euro)
            df.loc[df["estado"] != "SOLD", col] = pd.NA

    # Recalcular acciones desde precio y total para evitar problemas de formato CSV
    # (el CSV exporta '20,000' European como '20000', perdiendo el decimal)
    if all(c in df.columns for c in ["invertido_total", "comision", "precio_compra"]):
        df["num_acciones"] = (df["invertido_total"] - df["comision"]) / df["precio_compra"].replace(0, pd.NA)
    elif "num_acciones" in df.columns:
        df["num_acciones"] = df["num_acciones"].apply(parse_number)

    for col in ["buy_date", "sale_date"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], dayfirst=True, errors="coerce")

    if "tipo" in df.columns:
        df["tipo"] = df["tipo"].astype(str).str.upper().str.strip()

    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce")

    print(f"  {len(df)} operaciones cargadas.\n")
    return df


# ---------------------------------------------------------------------------
# Obtener precios actuales y dividendos
# ---------------------------------------------------------------------------


def get_current_prices(tickers: list[str]) -> dict[str, float]:
    prices = {}
    if not tickers:
        return prices

    print(f"  Descargando precios actuales para {len(tickers)} tickers...")
    for ticker in tickers:
        try:
            data = yf.Ticker(ticker).fast_info
            price = getattr(data, "last_price", None)
            if price and price > 0:
                prices[ticker] = price
        except Exception:
            pass
    return prices


def get_dividend_info(tickers: list[str]) -> dict[str, dict]:
    """Descarga dividend yield, importe anual/acción y próxima fecha ex-dividendo."""
    result: dict[str, dict] = {}
    if not tickers:
        return result

    print(f"  Descargando información de dividendos para {len(tickers)} tickers...")
    for ticker in tickers:
        div_yield, div_rate, next_ex_div = None, None, None
        try:
            t = yf.Ticker(ticker)
            info = t.info
            div_yield = info.get("dividendYield") or info.get("trailingAnnualDividendYield")
            div_rate = info.get("dividendRate") or info.get("trailingAnnualDividendRate")

            # Normalizar yield a fracción (yfinance devuelve 0.05 o 5.0 según el mercado)
            if div_yield is not None:
                if div_yield > 1:
                    div_yield = div_yield / 100
                # Descartar yields > 20%: datos incoherentes (ej. FRA con precio en EUR/USD)
                if div_yield > 0.20:
                    div_yield = None
                    div_rate = None

            # Intentar obtener próxima fecha ex-dividendo desde el calendario
            try:
                cal = t.calendar
                if isinstance(cal, dict):
                    next_ex_div = cal.get("Ex-Dividend Date") or cal.get("Dividend Date")
                elif isinstance(cal, pd.DataFrame) and not cal.empty:
                    for label in ["Ex-Dividend Date", "Dividend Date"]:
                        if label in cal.index:
                            next_ex_div = cal.loc[label].iloc[0]
                            break
            except Exception:
                pass

            # Fallback: exDividendDate de info (unix timestamp)
            if next_ex_div is None:
                ts = info.get("exDividendDate")
                if ts:
                    next_ex_div = pd.Timestamp(ts, unit="s").date()

        except Exception:
            pass

        result[ticker] = {
            "div_yield": div_yield,
            "div_rate": div_rate,
            "next_ex_div": next_ex_div,
        }
    return result


# ---------------------------------------------------------------------------
# Análisis de posiciones abiertas
# ---------------------------------------------------------------------------


def analyse_open_positions(df: pd.DataFrame) -> pd.DataFrame:
    bought = df[df["estado"] == "BOUGHT"].copy()
    if bought.empty:
        return pd.DataFrame()

    grp = (
        bought.groupby(["empresa", "indice", "tipo"])
        .agg(
            acciones=("num_acciones", "sum"),
            coste_total=("invertido_total", "sum"),
            comisiones=("comision", "sum"),
            operaciones=("empresa", "count"),
        )
        .reset_index()
    )

    grp["precio_medio"] = (grp["coste_total"] - grp["comisiones"]) / grp["acciones"].replace(0, pd.NA)
    grp["ticker_yf"] = grp["indice"].apply(indice_to_yf_ticker)

    yf_tickers = grp["ticker_yf"].dropna().unique().tolist()
    prices = get_current_prices(yf_tickers)
    dividends = get_dividend_info(yf_tickers)

    grp["precio_actual"] = grp["ticker_yf"].map(prices)
    grp["valor_actual"] = grp["precio_actual"] * grp["acciones"]
    grp["pnl"] = grp["valor_actual"] - grp["coste_total"]
    grp["pnl_pct"] = (grp["pnl"] / grp["coste_total"]) * 100

    grp["div_yield"] = grp["ticker_yf"].map({k: v["div_yield"] for k, v in dividends.items()})
    grp["div_rate"] = grp["ticker_yf"].map({k: v["div_rate"] for k, v in dividends.items()})
    grp["next_ex_div"] = grp["ticker_yf"].map({k: v["next_ex_div"] for k, v in dividends.items()})

    return grp


# ---------------------------------------------------------------------------
# Análisis de posiciones cerradas
# ---------------------------------------------------------------------------


def analyse_closed_positions(df: pd.DataFrame) -> pd.DataFrame:
    sold = df[df["estado"] == "SOLD"].copy()
    if sold.empty:
        return pd.DataFrame()

    agg: dict = {
        "coste_total": ("invertido_total", "sum"),
        "comisiones_compra": ("comision", "sum"),
        "operaciones": ("empresa", "count"),
    }
    if "liquido" in sold.columns:
        agg["liquido_total"] = ("liquido", "sum")
    if "comision_venta" in sold.columns:
        agg["comisiones_venta"] = ("comision_venta", "sum")
    if "ganancia_bruta" in sold.columns:
        agg["ganancia_bruta"] = ("ganancia_bruta", "sum")

    grp = (
        sold.groupby(["empresa", "indice", "tipo"])
        .agg(**agg)
        .reset_index()
    )

    if "liquido_total" in grp.columns:
        grp["pnl"] = grp["liquido_total"] - grp["coste_total"]
        grp["pnl_pct"] = (grp["pnl"] / grp["coste_total"]) * 100

    return grp


# ---------------------------------------------------------------------------
# Análisis de fondos
# ---------------------------------------------------------------------------


def analyse_funds(df: pd.DataFrame) -> pd.DataFrame:
    funds = df[df["estado"] == "FUND"].copy()
    if funds.empty:
        return pd.DataFrame()

    grp = (
        funds.groupby("empresa")
        .agg(
            invertido=("invertido_total", "sum"),
            aportaciones=("empresa", "count"),
        )
        .reset_index()
    )
    return grp


# ---------------------------------------------------------------------------
# Impresión de resultados
# ---------------------------------------------------------------------------


def print_open_positions(grp: pd.DataFrame):
    section("POSICIONES ABIERTAS (BOUGHT)")
    if grp.empty:
        print("  Sin posiciones abiertas.")
        return

    total_coste = grp["coste_total"].sum()
    total_valor = grp["valor_actual"].sum()
    total_pnl = grp["pnl"].sum()

    col_w = [28, 14, 8, 10, 12, 12, 12, 10]
    header = (
        f"{'Empresa':<{col_w[0]}} {'Índice':<{col_w[1]}} {'Tipo':<{col_w[2]}} "
        f"{'Acciones':>{col_w[3]}} {'Coste':>{col_w[4]}} {'Precio act.':>{col_w[5]}} "
        f"{'Valor':>{col_w[6]}} {'P&L%':>{col_w[7]}}"
    )
    print(f"\n{header}")
    print("-" * sum(col_w))

    for _, r in grp.sort_values("coste_total", ascending=False).iterrows():
        precio_str = fmt(r["precio_actual"], suffix="") if pd.notna(r["precio_actual"]) else "  N/D"
        valor_str = fmt(r["valor_actual"]) if pd.notna(r["valor_actual"]) else "    N/D"
        pnl_str = pct(r["pnl_pct"]) if pd.notna(r["pnl_pct"]) else "   N/D"

        print(
            f"{str(r['empresa']):<{col_w[0]}} "
            f"{str(r['indice']):<{col_w[1]}} "
            f"{str(r['tipo']):<{col_w[2]}} "
            f"{r['acciones']:>{col_w[3]},.3f} "
            f"{fmt(r['coste_total']):>{col_w[4]}} "
            f"{precio_str:>{col_w[5]}} "
            f"{valor_str:>{col_w[6]}} "
            f"{pnl_str:>{col_w[7]}}"
        )

    print("-" * sum(col_w))
    sin_precio = grp["precio_actual"].isna().sum()
    print(f"\n  Total invertido (abierto):  {fmt(total_coste)}")
    if pd.notna(total_valor) and total_valor > 0:
        print(f"  Valor actual estimado:       {fmt(total_valor)}")
        print(f"  P&L latente:                 {fmt(total_pnl)}  ({pct(total_pnl / total_coste * 100)})")
    if sin_precio:
        print(f"  ({sin_precio} posiciones sin precio disponible vía yfinance)")


def print_closed_positions(grp: pd.DataFrame):
    section("POSICIONES CERRADAS (SOLD)")
    if grp.empty:
        print("  Sin posiciones cerradas.")
        return

    has_pnl = "pnl" in grp.columns

    col_w = [28, 14, 8, 14, 12, 10, 8]
    header = (
        f"{'Empresa':<{col_w[0]}} {'Índice':<{col_w[1]}} {'Tipo':<{col_w[2]}} "
        f"{'Coste total':>{col_w[3]}} {'Líquido':>{col_w[4]}} {'P&L':>{col_w[5]}} {'Ops':>{col_w[6]}}"
    )
    print(f"\n{header}")
    print("-" * sum(col_w))

    for _, r in grp.sort_values("coste_total", ascending=False).iterrows():
        if has_pnl and pd.notna(r.get("pnl")):
            liquido_str = fmt(r["liquido_total"])
            pnl_str = fmt(r["pnl"])
        else:
            liquido_str = "N/D"
            pnl_str = "N/D"
        print(
            f"{str(r['empresa']):<{col_w[0]}} "
            f"{str(r['indice']):<{col_w[1]}} "
            f"{str(r['tipo']):<{col_w[2]}} "
            f"{fmt(r['coste_total']):>{col_w[3]}} "
            f"{liquido_str:>{col_w[4]}} "
            f"{pnl_str:>{col_w[5]}} "
            f"{int(r['operaciones']):>{col_w[6]}}"
        )

    print("-" * sum(col_w))
    print(f"\n  Total coste base (cerrado):  {fmt(grp['coste_total'].sum())}")
    if has_pnl:
        total_liquido = grp["liquido_total"].sum()
        total_pnl = grp["pnl"].sum()
        total_coste = grp["coste_total"].sum()
        print(f"  Total líquido obtenido:      {fmt(total_liquido)}")
        print(f"  P&L realizado total:         {fmt(total_pnl)}  ({pct(total_pnl / total_coste * 100)})")


def print_funds(grp: pd.DataFrame):
    section("FONDOS (FUND)")
    if grp.empty:
        print("  Sin fondos registrados.")
        return

    col_w = [36, 14, 10]
    header = f"{'Fondo':<{col_w[0]}} {'Invertido':>{col_w[1]}} {'Aportaciones':>{col_w[2]}}"
    print(f"\n{header}")
    print("-" * sum(col_w))

    for _, r in grp.sort_values("invertido", ascending=False).iterrows():
        print(
            f"{str(r['empresa']):<{col_w[0]}} "
            f"{fmt(r['invertido']):>{col_w[1]}} "
            f"{int(r['aportaciones']):>{col_w[2]}}"
        )

    print("-" * sum(col_w))
    print(f"\n  Total en fondos:  {fmt(grp['invertido'].sum())}")


def print_dividends(grp: pd.DataFrame):
    section("DIVIDENDOS — POSICIONES ABIERTAS")
    if grp.empty:
        print("  Sin posiciones abiertas.")
        return

    div_data = grp[grp["div_yield"].notna() | grp["div_rate"].notna()].copy()
    no_div = grp[grp["div_yield"].isna() & grp["div_rate"].isna()]

    if div_data.empty:
        print("  Ninguna posición abierta reporta dividendos en yfinance.")
    else:
        col_w = [28, 14, 10, 14, 14, 16]
        header = (
            f"{'Empresa':<{col_w[0]}} {'Índice':<{col_w[1]}} "
            f"{'Yield':>{col_w[2]}} {'€/acción año':>{col_w[3]}} "
            f"{'€ anuales':>{col_w[4]}} {'Próx. ex-div':>{col_w[5]}}"
        )
        print(f"\n{header}")
        print("-" * sum(col_w))

        for _, r in div_data.sort_values("div_yield", ascending=False).iterrows():
            yld = r["div_yield"]
            yield_str = f"{yld*100:.2f}%" if pd.notna(yld) else "  N/D"
            rate_str = fmt(r["div_rate"]) if pd.notna(r["div_rate"]) else "   N/D"
            annual_str = fmt(r["div_rate"] * r["acciones"]) if pd.notna(r["div_rate"]) else "   N/D"
            ex_str = str(r["next_ex_div"])[:10] if pd.notna(r["next_ex_div"]) else "N/D"

            print(
                f"{str(r['empresa']):<{col_w[0]}} "
                f"{str(r['indice']):<{col_w[1]}} "
                f"{yield_str:>{col_w[2]}} "
                f"{rate_str:>{col_w[3]}} "
                f"{annual_str:>{col_w[4]}} "
                f"{ex_str:>{col_w[5]}}"
            )

        total_anual = (div_data["div_rate"] * div_data["acciones"]).sum()
        print("-" * sum(col_w))
        print(f"\n  Ingresos por dividendos estimados/año:  {fmt(total_anual)}")

    if not no_div.empty:
        empresas = ", ".join(no_div["empresa"].tolist())
        print(f"\n  Sin datos de dividendo: {empresas}")


def print_summary(df: pd.DataFrame, open_grp: pd.DataFrame, closed_grp: pd.DataFrame):
    section("RESUMEN GLOBAL DE LA CARTERA")

    total_comprado = df["invertido_total"].sum()
    total_abierto = df[df["estado"] == "BOUGHT"]["invertido_total"].sum()
    total_cerrado = df[df["estado"] == "SOLD"]["invertido_total"].sum()
    total_fondos = df[df["estado"] == "FUND"]["invertido_total"].sum()

    print(f"\n  Total invertido (histórico):   {fmt(total_comprado)}")
    print(f"    ├─ Posiciones abiertas:       {fmt(total_abierto)}")
    print(f"    ├─ Posiciones cerradas:       {fmt(total_cerrado)}")
    print(f"    └─ Fondos:                   {fmt(total_fondos)}")

    if not open_grp.empty and open_grp["valor_actual"].notna().any():
        valor_actual = open_grp["valor_actual"].sum()
        pnl_total = open_grp["pnl"].sum()
        print(f"\n  Valor actual cartera abierta:  {fmt(valor_actual)}")
        print(f"  P&L latente estimado:          {fmt(pnl_total)}  ({pct(pnl_total / total_abierto * 100)})")

    # P&L realizado de posiciones cerradas
    if not closed_grp.empty and "pnl" in closed_grp.columns:
        pnl_cerrado = closed_grp["pnl"].sum()
        total_cerrado_base = closed_grp["coste_total"].sum()
        print(f"\n  P&L realizado (cerradas):      {fmt(pnl_cerrado)}  ({pct(pnl_cerrado / total_cerrado_base * 100)})")

    # Por tipo
    print(f"\n  {'Desglose por tipo':─<40}")
    for tipo, sub in df.groupby("tipo"):
        print(f"    {tipo:<8}  {fmt(sub['invertido_total'].sum())}")

    # Por año
    if "year" in df.columns:
        print(f"\n  {'Desglose por año':─<40}")
        for year, sub in df.groupby("year"):
            if pd.notna(year):
                print(f"    {int(year)}      {fmt(sub['invertido_total'].sum())}")

    # Top 5 posiciones abiertas por coste
    if not open_grp.empty:
        print(f"\n  {'Top 5 posiciones abiertas (por coste)':─<40}")
        top5 = open_grp.nlargest(5, "coste_total")
        for _, r in top5.iterrows():
            print(f"    {str(r['empresa']):<28}  {fmt(r['coste_total'])}")


# ---------------------------------------------------------------------------
# Exportar CSV actualizado
# ---------------------------------------------------------------------------


def export_updated_csv(open_grp: pd.DataFrame, closed_grp: pd.DataFrame,
                       fund_grp: pd.DataFrame, output_path: str):
    """Genera un CSV con posiciones abiertas, cerradas y fondos enriquecidos."""
    frames = []

    if not open_grp.empty:
        open_out = open_grp[[
            "empresa", "indice", "tipo", "acciones", "precio_medio",
            "coste_total", "comisiones", "precio_actual", "valor_actual",
            "pnl", "pnl_pct", "div_yield", "div_rate", "next_ex_div",
        ]].copy()
        open_out.insert(0, "estado", "BOUGHT")
        frames.append(open_out)

    if not closed_grp.empty:
        closed_cols = ["empresa", "indice", "tipo", "coste_total", "comisiones_compra", "operaciones"]
        for extra in ["liquido_total", "comisiones_venta", "ganancia_bruta", "pnl", "pnl_pct"]:
            if extra in closed_grp.columns:
                closed_cols.append(extra)
        closed_out = closed_grp[closed_cols].copy()
        closed_out.insert(0, "estado", "SOLD")
        frames.append(closed_out)

    if not fund_grp.empty:
        fund_out = fund_grp[["empresa", "invertido", "aportaciones"]].copy()
        fund_out.insert(0, "estado", "FUND")
        frames.append(fund_out)

    if not frames:
        print("  Nada que exportar.")
        return

    combined = pd.concat(frames, ignore_index=True)

    # Redondear columnas numéricas
    for col in ["precio_medio", "coste_total", "precio_actual", "valor_actual", "pnl"]:
        if col in combined.columns:
            combined[col] = combined[col].round(2)
    if "pnl_pct" in combined.columns:
        combined["pnl_pct"] = combined["pnl_pct"].round(4)
    if "div_yield" in combined.columns:
        combined["div_yield"] = combined["div_yield"].round(4)

    combined.to_csv(output_path, index=False, encoding="utf-8")
    print(f"  Fichero exportado: {output_path}  ({len(combined)} filas)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CSV_PATH

    if not path.exists():
        print(f"ERROR: No se encontró el fichero '{path}'.")
        print("Uso: python main.py [ruta_al_csv]")
        print(f"Ruta por defecto: {DEFAULT_CSV_PATH}")
        sys.exit(1)

    df = load_portfolio(str(path))

    open_grp = analyse_open_positions(df)
    closed_grp = analyse_closed_positions(df)
    fund_grp = analyse_funds(df)

    print_open_positions(open_grp)
    print_closed_positions(closed_grp)
    print_funds(fund_grp)
    print_dividends(open_grp)
    print_summary(df, open_grp, closed_grp)

    output_path = str(path.parent / "cartera_actualizada.csv")
    section("EXPORTANDO DATOS ACTUALIZADOS")
    export_updated_csv(open_grp, closed_grp, fund_grp, output_path)

    print(f"\n{'='*70}\n")


if __name__ == "__main__":
    main()