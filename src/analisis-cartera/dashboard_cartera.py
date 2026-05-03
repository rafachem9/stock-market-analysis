#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dashboard de Cartera Personal de Inversión.

Ejecutar con:
    streamlit run dashboard_cartera.py

Lee 'cartera_actualizada.csv' generado por main.py.
"""

from datetime import date
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Configuración de página
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Mi Cartera",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .metric-card { background:#1e2130; border-radius:10px; padding:16px; text-align:center; }
    .positive { color: #00cc88; font-weight:bold; }
    .negative { color: #ff4b4b; font-weight:bold; }
    div[data-testid="metric-container"] { background:#1e2130; border-radius:8px; padding:10px; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Carga de datos
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = PROJECT_ROOT / "data" / "cartera_actualizada.csv"

@st.cache_data(ttl=300)
def load_data(path: Path):
    df = pd.read_csv(path)
    open_df = df[df["estado"] == "BOUGHT"].copy()
    sold_df = df[df["estado"] == "SOLD"].copy()
    fund_df = df[df["estado"] == "FUND"].copy()

    # Limpiar filas con acciones negativas (artefacto de datos)
    open_df = open_df[open_df["acciones"] > 0].copy()

    for col in ["coste_total", "valor_actual", "pnl", "pnl_pct",
                "div_yield", "div_rate", "acciones", "precio_actual", "precio_medio"]:
        if col in open_df.columns:
            open_df[col] = pd.to_numeric(open_df[col], errors="coerce")

    if "next_ex_div" in open_df.columns:
        open_df["next_ex_div"] = pd.to_datetime(open_df["next_ex_div"], errors="coerce")

    for col in ["coste_total", "comisiones"]:
        if col in sold_df.columns:
            sold_df[col] = pd.to_numeric(sold_df[col], errors="coerce")

    if "invertido" in fund_df.columns:
        fund_df["invertido"] = pd.to_numeric(fund_df["invertido"], errors="coerce")

    return open_df, sold_df, fund_df


if not CSV_PATH.exists():
    st.error(f"No se encontró '{CSV_PATH}'. Ejecuta primero: `python main.py cartera.csv`")
    st.stop()

open_df, sold_df, fund_df = load_data(CSV_PATH)

# ---------------------------------------------------------------------------
# Sidebar — filtros
# ---------------------------------------------------------------------------

st.sidebar.title("🔧 Filtros")

tipos = ["Todos"] + sorted(open_df["tipo"].dropna().unique().tolist())
sel_tipo = st.sidebar.selectbox("Tipo de activo", tipos)

if sel_tipo != "Todos":
    open_df = open_df[open_df["tipo"] == sel_tipo]

solo_pnl_positivo = st.sidebar.checkbox("Solo posiciones en positivo")
if solo_pnl_positivo:
    open_df = open_df[open_df["pnl"] > 0]

solo_dividendos = st.sidebar.checkbox("Solo con dividendos")
if solo_dividendos:
    open_df = open_df[open_df["div_yield"] > 0]

st.sidebar.markdown("---")
st.sidebar.caption(f"Mostrando {len(open_df)} posiciones abiertas")
st.sidebar.caption(f"Datos: {CSV_PATH.name}")

# ---------------------------------------------------------------------------
# Métricas globales
# ---------------------------------------------------------------------------

st.title("📊 Mi Cartera de Inversión")
st.caption(f"Actualizado: {date.today().strftime('%d/%m/%Y')}")

total_abierto = open_df["coste_total"].sum()
total_cerrado = sold_df["coste_total"].sum() if not sold_df.empty else 0
total_fondos = fund_df["invertido"].sum() if not fund_df.empty else 0
total_historico = total_abierto + total_cerrado + total_fondos

valor_actual = open_df["valor_actual"].dropna().sum()
pnl_total = open_df["pnl"].dropna().sum()
pnl_pct = (pnl_total / total_abierto * 100) if total_abierto else 0

div_data = open_df[open_df["div_rate"].notna() & (open_df["div_rate"] > 0)].copy()
ingresos_div = (div_data["div_rate"] * div_data["acciones"]).sum()

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total histórico", f"{total_historico:,.0f} €")
col2.metric("Invertido abierto", f"{total_abierto:,.0f} €")
col3.metric("Valor actual", f"{valor_actual:,.0f} €")
col4.metric("P&L latente", f"{pnl_total:,.0f} €", f"{pnl_pct:+.2f}%")
col5.metric("Dividendos/año est.", f"{ingresos_div:,.0f} €")

st.markdown("---")

# ---------------------------------------------------------------------------
# Tabs principales
# ---------------------------------------------------------------------------

tab1, tab2, tab3, tab4 = st.tabs([
    "📈 Posiciones abiertas",
    "💰 Dividendos",
    "📋 Posiciones cerradas",
    "🏦 Fondos",
])

# ===========================================================================
# TAB 1 — Posiciones abiertas
# ===========================================================================

with tab1:
    if open_df.empty:
        st.info("Sin posiciones abiertas con los filtros actuales.")
    else:
        # --- Gráfico: coste vs valor actual ---
        c1, c2 = st.columns([3, 2])

        with c1:
            st.subheader("Coste vs Valor actual")
            plot_df = open_df.dropna(subset=["valor_actual"]).sort_values("coste_total", ascending=True)
            fig = go.Figure()
            fig.add_trace(go.Bar(
                y=plot_df["empresa"], x=plot_df["coste_total"],
                name="Coste", orientation="h",
                marker_color="#5b7fa6",
            ))
            fig.add_trace(go.Bar(
                y=plot_df["empresa"], x=plot_df["valor_actual"],
                name="Valor actual", orientation="h",
                marker_color="#00cc88",
            ))
            fig.update_layout(
                barmode="group", height=max(350, len(plot_df) * 28),
                margin=dict(l=0, r=10, t=10, b=10),
                legend=dict(orientation="h", y=1.05),
                xaxis_title="€",
            )
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            st.subheader("Distribución por coste")
            fig2 = px.pie(
                open_df, values="coste_total", names="empresa",
                hole=0.45,
                color_discrete_sequence=px.colors.qualitative.Set3,
            )
            fig2.update_traces(textposition="inside", textinfo="percent+label")
            fig2.update_layout(
                showlegend=False, height=max(350, len(open_df) * 14),
                margin=dict(l=0, r=0, t=10, b=10),
            )
            st.plotly_chart(fig2, use_container_width=True)

        # --- Gráfico P&L % por empresa ---
        st.subheader("P&L latente por posición")
        pnl_df = open_df.dropna(subset=["pnl_pct"]).sort_values("pnl_pct")
        colors = ["#ff4b4b" if v < 0 else "#00cc88" for v in pnl_df["pnl_pct"]]
        fig3 = go.Figure(go.Bar(
            x=pnl_df["empresa"], y=pnl_df["pnl_pct"],
            marker_color=colors,
            text=pnl_df["pnl_pct"].apply(lambda v: f"{v:+.1f}%"),
            textposition="outside",
        ))
        fig3.add_hline(y=0, line_color="white", line_width=1, opacity=0.4)
        fig3.update_layout(
            height=380, yaxis_title="P&L (%)",
            margin=dict(l=0, r=0, t=10, b=10),
        )
        st.plotly_chart(fig3, use_container_width=True)

        # --- Tabla detalle ---
        st.subheader("Detalle de posiciones")

        def color_pnl(val):
            try:
                return "color: #00cc88" if float(val) >= 0 else "color: #ff4b4b"
            except Exception:
                return ""

        display = open_df[[
            "empresa", "indice", "tipo", "acciones", "precio_medio",
            "precio_actual", "coste_total", "valor_actual", "pnl", "pnl_pct",
        ]].copy()
        display.columns = [
            "Empresa", "Índice", "Tipo", "Acciones", "P. Medio €",
            "P. Actual €", "Coste €", "Valor €", "P&L €", "P&L %",
        ]

        def fmt_num(v, dec=2):
            return f"{v:,.{dec}f}" if pd.notna(v) else "—"

        for col in ["Acciones", "P. Medio €", "P. Actual €", "Coste €", "Valor €", "P&L €"]:
            display[col] = display[col].apply(lambda v: fmt_num(v))
        display["P&L %"] = display["P&L %"].apply(
            lambda v: f"{v:+.2f}%" if pd.notna(v) else "—"
        )

        st.dataframe(
            display.style.applymap(color_pnl, subset=["P&L %"]),
            use_container_width=True, hide_index=True,
        )

# ===========================================================================
# TAB 2 — Dividendos
# ===========================================================================

with tab2:
    div_open = open_df[open_df["div_yield"].notna()].copy()

    if div_open.empty:
        st.info("No hay datos de dividendos disponibles con los filtros actuales.")
    else:
        has_div = div_open[div_open["div_yield"] > 0].copy()
        no_div = div_open[div_open["div_yield"] == 0]["empresa"].tolist()

        # KPIs dividendos
        d1, d2, d3 = st.columns(3)
        d1.metric("Posiciones con dividendo", len(has_div))
        d2.metric("Ingresos estimados/año", f"{(has_div['div_rate'] * has_div['acciones']).sum():,.2f} €")
        d3.metric("Yield medio ponderado",
                  f"{(has_div['div_yield'] * has_div['coste_total']).sum() / has_div['coste_total'].sum() * 100:.2f}%"
                  if not has_div.empty else "—")

        st.markdown("---")

        c1, c2 = st.columns([2, 3])

        with c1:
            st.subheader("Dividend Yield por empresa")
            yd = has_div.sort_values("div_yield", ascending=True)
            fig_y = go.Figure(go.Bar(
                y=yd["empresa"],
                x=(yd["div_yield"] * 100).round(2),
                orientation="h",
                marker_color="#f7b731",
                text=(yd["div_yield"] * 100).apply(lambda v: f"{v:.2f}%"),
                textposition="outside",
            ))
            fig_y.update_layout(
                xaxis_title="Yield (%)",
                height=max(300, len(yd) * 30),
                margin=dict(l=0, r=30, t=10, b=10),
            )
            st.plotly_chart(fig_y, use_container_width=True)

        with c2:
            st.subheader("Ingresos anuales estimados por posición")
            has_div["ingresos_anuales"] = (has_div["div_rate"] * has_div["acciones"]).round(2)
            ing = has_div.sort_values("ingresos_anuales", ascending=True)
            fig_i = go.Figure(go.Bar(
                y=ing["empresa"],
                x=ing["ingresos_anuales"],
                orientation="h",
                marker_color="#20bf6b",
                text=ing["ingresos_anuales"].apply(lambda v: f"{v:.2f} €"),
                textposition="outside",
            ))
            fig_i.update_layout(
                xaxis_title="€/año",
                height=max(300, len(ing) * 30),
                margin=dict(l=0, r=60, t=10, b=10),
            )
            st.plotly_chart(fig_i, use_container_width=True)

        # Tabla próximas ex-div
        st.subheader("Próximas fechas ex-dividendo")
        prox = has_div[has_div["next_ex_div"].notna()].copy()
        prox = prox.sort_values("next_ex_div")
        today = pd.Timestamp(date.today())
        prox["Días restantes"] = (prox["next_ex_div"] - today).dt.days

        prox_display = prox[[
            "empresa", "indice", "next_ex_div", "Días restantes",
            "div_yield", "div_rate", "acciones", "ingresos_anuales",
        ]].copy()
        prox_display.columns = [
            "Empresa", "Índice", "Ex-Div date", "Días",
            "Yield", "€/acción año", "Acciones", "Ingresos/año €",
        ]
        prox_display["Yield"] = prox_display["Yield"].apply(lambda v: f"{v*100:.2f}%")
        prox_display["€/acción año"] = prox_display["€/acción año"].apply(lambda v: f"{v:.2f}")
        prox_display["Ingresos/año €"] = prox_display["Ingresos/año €"].apply(lambda v: f"{v:.2f}")
        prox_display["Ex-Div date"] = prox_display["Ex-Div date"].dt.strftime("%d/%m/%Y")

        def highlight_days(val):
            try:
                d = int(val)
                if d < 0:
                    return "color: gray"
                if d < 14:
                    return "color: #f7b731; font-weight:bold"
                return ""
            except Exception:
                return ""

        st.dataframe(
            prox_display.style.applymap(highlight_days, subset=["Días"]),
            use_container_width=True, hide_index=True,
        )

        if no_div:
            st.caption(f"Sin dividendo: {', '.join(no_div)}")

# ===========================================================================
# TAB 3 — Posiciones cerradas
# ===========================================================================

with tab3:
    if sold_df.empty:
        st.info("Sin posiciones cerradas.")
    else:
        total_cerrado = sold_df["coste_total"].sum()
        st.metric("Total coste base (cerrado)", f"{total_cerrado:,.2f} €")
        st.caption("El precio de venta no está en el CSV → P&L realizado no calculable desde estos datos.")

        c1, c2 = st.columns([3, 2])

        with c1:
            st.subheader("Coste base por empresa")
            s_sorted = sold_df.sort_values("coste_total", ascending=True)
            fig_s = go.Figure(go.Bar(
                y=s_sorted["empresa"], x=s_sorted["coste_total"],
                orientation="h", marker_color="#5b7fa6",
                text=s_sorted["coste_total"].apply(lambda v: f"{v:,.0f} €"),
                textposition="outside",
            ))
            fig_s.update_layout(
                height=max(350, len(s_sorted) * 22),
                margin=dict(l=0, r=80, t=10, b=10),
                xaxis_title="€",
            )
            st.plotly_chart(fig_s, use_container_width=True)

        with c2:
            st.subheader("Distribución por tipo")
            tipo_sold = sold_df.groupby("tipo")["coste_total"].sum().reset_index()
            fig_t = px.pie(
                tipo_sold, values="coste_total", names="tipo",
                hole=0.4,
                color_discrete_sequence=["#5b7fa6", "#f7b731", "#20bf6b"],
            )
            fig_t.update_layout(height=350, margin=dict(l=0, r=0, t=10, b=10))
            st.plotly_chart(fig_t, use_container_width=True)

        st.subheader("Tabla de posiciones cerradas")
        sold_display = sold_df[["empresa", "indice", "tipo", "coste_total", "comisiones", "operaciones"]].copy()
        sold_display.columns = ["Empresa", "Índice", "Tipo", "Coste €", "Comisiones €", "Operaciones"]
        sold_display["Coste €"] = sold_display["Coste €"].apply(lambda v: f"{v:,.2f}")
        sold_display["Comisiones €"] = sold_display["Comisiones €"].apply(lambda v: f"{v:,.2f}")
        sold_display = sold_display.sort_values("Coste €", ascending=False)
        st.dataframe(sold_display, use_container_width=True, hide_index=True)

# ===========================================================================
# TAB 4 — Fondos
# ===========================================================================

with tab4:
    if fund_df.empty:
        st.info("Sin fondos registrados.")
    else:
        total_f = fund_df["invertido"].sum()
        st.metric("Total en fondos", f"{total_f:,.2f} €")

        c1, c2 = st.columns([2, 3])

        with c1:
            st.subheader("Distribución de fondos")
            fig_f = px.pie(
                fund_df, values="invertido", names="empresa",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Pastel,
            )
            fig_f.update_traces(textposition="inside", textinfo="percent+label")
            fig_f.update_layout(showlegend=False, height=350, margin=dict(l=0, r=0, t=10, b=10))
            st.plotly_chart(fig_f, use_container_width=True)

        with c2:
            st.subheader("Aportaciones por fondo")
            fund_sorted = fund_df.sort_values("invertido", ascending=True)
            fig_fb = go.Figure(go.Bar(
                y=fund_sorted["empresa"], x=fund_sorted["invertido"],
                orientation="h", marker_color="#a29bfe",
                text=fund_sorted["invertido"].apply(lambda v: f"{v:,.0f} €"),
                textposition="outside",
            ))
            fig_fb.update_layout(
                height=max(280, len(fund_sorted) * 40),
                margin=dict(l=0, r=80, t=10, b=10),
                xaxis_title="€",
            )
            st.plotly_chart(fig_fb, use_container_width=True)

        st.subheader("Detalle de fondos")
        fund_display = fund_df[["empresa", "invertido", "aportaciones"]].copy()
        fund_display.columns = ["Fondo", "Invertido €", "Aportaciones"]
        fund_display["Invertido €"] = fund_display["Invertido €"].apply(lambda v: f"{v:,.2f}")
        fund_display = fund_display.sort_values("Invertido €", ascending=False)
        st.dataframe(fund_display, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

st.markdown("---")
st.caption("Datos obtenidos de Yahoo Finance vía yfinance · No constituye asesoramiento financiero")
