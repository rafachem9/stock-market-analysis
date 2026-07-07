#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Dashboard de Análisis de Inversiones
=====================================
Visualización interactiva de oportunidades de inversión basada en 
múltiples indicadores financieros.

Ejecutar con: streamlit run dashboard.py
"""

import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
import config as _config

# Configuración de la página
st.set_page_config(
    page_title="Stock Market Analysis",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# CONFIGURACIÓN
# =============================================================================

DATA_DIR = _config.DATA_DIR

# Umbrales de análisis
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
MIN_DIVIDEND_YIELD = 2.0  # %
MIN_EXPECTED_RETURN = 10.0  # %
MIN_SHARPE_RATIO = 1.0


# =============================================================================
# FUNCIONES DE CARGA DE DATOS
# =============================================================================

@st.cache_data(ttl=3600)  # Cache por 1 hora
def load_data():
    """Carga los datos de análisis."""
    data = {}
    
    # IBEX 35
    ibex_path = DATA_DIR / "ibex35_analysed_df.csv"
    if ibex_path.exists():
        data['IBEX 35'] = pd.read_csv(ibex_path)
    
    # S&P 500
    sp500_path = DATA_DIR / "sp500_analysed_df.csv"
    if sp500_path.exists():
        data['S&P 500'] = pd.read_csv(sp500_path)
    
    # Dividendos
    div_ibex = DATA_DIR / "dividendos_ibex35_analysed_df.csv"
    if div_ibex.exists():
        data['Dividendos IBEX'] = pd.read_csv(div_ibex)
    
    div_sp500 = DATA_DIR / "dividendos_sp500_analysed_df.csv"
    if div_sp500.exists():
        data['Dividendos SP500'] = pd.read_csv(div_sp500)
    
    return data


@st.cache_data(ttl=3600)
def load_historical_data(index_name):
    """Carga datos históricos desde archivos parquet."""
    historical = {}
    
    # Determinar carpeta según índice
    if 'IBEX' in index_name:
        hist_dir = DATA_DIR / "ibex35_historic"
    else:
        hist_dir = DATA_DIR / "sp500_historic"
    
    if not hist_dir.exists():
        return historical
    
    for parquet_file in hist_dir.glob("*.parquet"):
        try:
            df = pd.read_parquet(parquet_file)
            # Obtener nombre de la acción
            if 'share_name' in df.columns:
                name = df['share_name'].iloc[0]
            else:
                name = parquet_file.stem.replace('_', ' ').title()
            
            # Asegurar que el índice es datetime
            if not isinstance(df.index, pd.DatetimeIndex):
                if 'Date' in df.columns:
                    df['Date'] = pd.to_datetime(df['Date'])
                    df = df.set_index('Date')
            
            historical[name] = df
        except Exception as e:
            continue
    
    return historical


def render_stock_evolution(df_analysis, index_name):
    """Muestra la evolución de las acciones seleccionadas."""
    st.subheader("📈 Evolución de Acciones")
    
    # Cargar datos históricos
    historical = load_historical_data(index_name)
    
    if not historical:
        st.warning("No hay datos históricos disponibles. Ejecuta primero el análisis.")
        return
    
    # Obtener lista de acciones disponibles
    available_stocks = sorted(historical.keys())
    
    # Selector de acciones
    col1, col2 = st.columns([3, 1])
    
    with col1:
        selected_stocks = st.multiselect(
            "Selecciona acciones para comparar",
            available_stocks,
            default=available_stocks[:3] if len(available_stocks) >= 3 else available_stocks,
            max_selections=10
        )
    
    with col2:
        chart_type = st.selectbox(
            "Tipo de gráfico",
            ["Precio", "Rentabilidad Acumulada", "Rentabilidad Diaria"]
        )
    
    if not selected_stocks:
        st.info("Selecciona al menos una acción para ver su evolución")
        return
    
    # Crear gráfico
    fig = go.Figure()
    
    for stock_name in selected_stocks:
        if stock_name not in historical:
            continue
            
        stock_df = historical[stock_name]
        
        if chart_type == "Precio":
            if 'Close' in stock_df.columns:
                fig.add_trace(go.Scatter(
                    x=stock_df.index,
                    y=stock_df['Close'],
                    mode='lines',
                    name=stock_name
                ))
        elif chart_type == "Rentabilidad Acumulada":
            if 'Cumulative Return' in stock_df.columns:
                fig.add_trace(go.Scatter(
                    x=stock_df.index,
                    y=stock_df['Cumulative Return'] * 100,
                    mode='lines',
                    name=stock_name
                ))
        elif chart_type == "Rentabilidad Diaria":
            if 'Daily Return' in stock_df.columns:
                fig.add_trace(go.Scatter(
                    x=stock_df.index,
                    y=stock_df['Daily Return'] * 100,
                    mode='lines',
                    name=stock_name
                ))
    
    # Configurar layout
    y_title = {
        "Precio": "Precio (€/$)",
        "Rentabilidad Acumulada": "Rentabilidad (%)",
        "Rentabilidad Diaria": "Retorno Diario (%)"
    }
    
    fig.update_layout(
        title=f"{chart_type} - {index_name}",
        xaxis_title="Fecha",
        yaxis_title=y_title.get(chart_type, ""),
        hovermode='x unified',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        height=500
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Tabla de estadísticas
    if selected_stocks:
        st.markdown("### 📊 Estadísticas del Período")
        
        stats_data = []
        for stock_name in selected_stocks:
            if stock_name not in historical:
                continue
            
            stock_df = historical[stock_name]
            
            stats = {
                'Acción': stock_name,
                'Precio Inicial': None,
                'Precio Final': None,
                'Variación (%)': None,
                'Volatilidad (%)': None,
                'Máximo': None,
                'Mínimo': None
            }
            
            if 'Close' in stock_df.columns and len(stock_df) > 0:
                stats['Precio Inicial'] = f"{stock_df['Close'].iloc[0]:.2f}"
                stats['Precio Final'] = f"{stock_df['Close'].iloc[-1]:.2f}"
                variation = ((stock_df['Close'].iloc[-1] / stock_df['Close'].iloc[0]) - 1) * 100
                stats['Variación (%)'] = f"{variation:+.2f}%"
                stats['Máximo'] = f"{stock_df['Close'].max():.2f}"
                stats['Mínimo'] = f"{stock_df['Close'].min():.2f}"
            
            if 'Daily Return' in stock_df.columns:
                stats['Volatilidad (%)'] = f"{stock_df['Daily Return'].std() * 100:.2f}%"
            
            stats_data.append(stats)
        
        if stats_data:
            stats_df = pd.DataFrame(stats_data)
            st.dataframe(stats_df, use_container_width=True, hide_index=True)


def render_sector_performance(df):
    """Gráfico de rendimiento por sector."""
    st.subheader("🏭 Rendimiento por Sector")
    
    if 'Sector' not in df.columns or 'Rentabilidad prevista' not in df.columns:
        st.warning("No hay datos de sector disponibles")
        return
    
    df = df.copy().reset_index(drop=True)
    
    # Agrupar por sector
    sector_data = df.groupby('Sector').agg({
        'Rentabilidad prevista': 'mean',
        'Ticker': 'count'
    }).reset_index()
    sector_data.columns = ['Sector', 'Rentabilidad Media (%)', 'Num. Empresas']
    sector_data = sector_data.sort_values('Rentabilidad Media (%)', ascending=True)
    
    # Crear gráfico de barras horizontal
    fig = px.bar(
        sector_data,
        x='Rentabilidad Media (%)',
        y='Sector',
        orientation='h',
        color='Rentabilidad Media (%)',
        color_continuous_scale=['red', 'yellow', 'green'],
        text='Rentabilidad Media (%)'
    )
    
    fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
    fig.update_layout(
        height=max(400, len(sector_data) * 30),
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_volatility_chart(df):
    """Gráfico de volatilidad vs rentabilidad."""
    st.subheader("📉 Riesgo vs Rentabilidad")
    
    if 'volatilidad' not in df.columns or 'Rentabilidad prevista' not in df.columns:
        st.warning("No hay datos de volatilidad disponibles")
        return
    
    df = df.copy().reset_index(drop=True)
    df = df.dropna(subset=['volatilidad', 'Rentabilidad prevista'])
    
    if df.empty:
        st.warning("No hay datos suficientes")
        return
    
    fig = px.scatter(
        df,
        x='volatilidad',
        y='Rentabilidad prevista',
        color='Sector' if 'Sector' in df.columns else None,
        hover_name='Empresa' if 'Empresa' in df.columns else 'Ticker',
        hover_data=['Ticker', 'sharpe_ratio'] if 'sharpe_ratio' in df.columns else ['Ticker'],
        labels={
            'volatilidad': 'Volatilidad (Riesgo)',
            'Rentabilidad prevista': 'Rentabilidad Prevista (%)'
        }
    )
    
    # Añadir líneas de referencia
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    fig.add_vline(x=df['volatilidad'].median(), line_dash="dash", line_color="gray", opacity=0.5)
    
    fig.update_layout(
        height=500,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.3
        )
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.caption("💡 Ideal: acciones en el cuadrante superior izquierdo (alta rentabilidad, baja volatilidad)")


def get_investment_score(row):
    """
    Calcula un score de inversión basado en múltiples factores.
    Score de 0-100 donde mayor es mejor oportunidad.
    """
    score = 50  # Base
    
    # Rentabilidad prevista (+/- 20 puntos)
    if pd.notna(row.get('Rentabilidad prevista')):
        rent = row['Rentabilidad prevista']
        if rent > 20:
            score += 20
        elif rent > 10:
            score += 10
        elif rent < -10:
            score -= 15
        elif rent < 0:
            score -= 5
    
    # Sharpe Ratio (+/- 15 puntos)
    if pd.notna(row.get('sharpe_ratio')):
        sharpe = row['sharpe_ratio']
        if sharpe > 2:
            score += 15
        elif sharpe > 1:
            score += 10
        elif sharpe < 0:
            score -= 10
    
    # Dividend Yield (+10 puntos si > 3%)
    if pd.notna(row.get('Dividend Yield')):
        div = row['Dividend Yield']
        if div > 5:
            score += 10
        elif div > 3:
            score += 5
    
    # Alpha positivo (+10 puntos)
    if pd.notna(row.get('alpha')) and row['alpha'] > 0:
        score += min(10, row['alpha'] * 100)
    
    # Volatilidad (penalizar alta volatilidad)
    if pd.notna(row.get('volatilidad')):
        vol = row['volatilidad']
        if vol > 0.04:
            score -= 10
        elif vol > 0.03:
            score -= 5
    
    return max(0, min(100, score))


# =============================================================================
# COMPONENTES DE UI
# =============================================================================

def render_metric_card(title, value, delta=None, help_text=None):
    """Renderiza una tarjeta de métrica."""
    if delta:
        st.metric(title, value, delta, help=help_text)
    else:
        st.metric(title, value, help=help_text)


def render_top_opportunities(df, title, n=10):
    """Muestra las mejores oportunidades de inversión."""
    st.subheader(f"🎯 {title}")
    
    if df.empty:
        st.warning("No hay datos disponibles")
        return
    
    # Calcular score de inversión
    df = df.copy().reset_index(drop=True)
    df['Investment Score'] = df.apply(get_investment_score, axis=1)
    
    # Top N por score
    top = df.nlargest(n, 'Investment Score')
    
    # Columnas a mostrar
    cols_to_show = ['Empresa', 'Ticker', 'Sector', 'Rentabilidad prevista', 
                    'sharpe_ratio', 'Dividend Yield', 'Investment Score']
    cols_available = [c for c in cols_to_show if c in top.columns]
    
    # Formatear
    display_df = top[cols_available].copy()
    
    if 'Rentabilidad prevista' in display_df.columns:
        display_df['Rentabilidad prevista'] = display_df['Rentabilidad prevista'].apply(
            lambda x: f"{x:.1f}%" if pd.notna(x) else "-"
        )
    if 'sharpe_ratio' in display_df.columns:
        display_df['sharpe_ratio'] = display_df['sharpe_ratio'].apply(
            lambda x: f"{x:.2f}" if pd.notna(x) else "-"
        )
    if 'Dividend Yield' in display_df.columns:
        display_df['Dividend Yield'] = display_df['Dividend Yield'].apply(
            lambda x: f"{x * 100:.2f}%" if pd.notna(x) else "-"
        )
    if 'Investment Score' in display_df.columns:
        display_df['Investment Score'] = display_df['Investment Score'].apply(
            lambda x: f"{x:.0f}/100"
        )
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    return top


def render_dividend_opportunities(df, title):
    """Muestra oportunidades de dividendos."""
    st.subheader(f"💰 {title}")
    
    if df.empty:
        st.info("No hay dividendos próximos")
        return
    
    cols = ['Empresa', 'Ticker', 'Ex-Dividend Date', 'Dividend Yield', 'Rentabilidad prevista']
    cols_available = [c for c in cols if c in df.columns]
    
    display_df = df[cols_available].copy()
    
    if 'Dividend Yield' in display_df.columns:
        display_df['Dividend Yield'] = display_df['Dividend Yield'].apply(
            lambda x: f"{x:.2f}%" if pd.notna(x) else "-"
        )
    
    st.dataframe(display_df.head(10), use_container_width=True, hide_index=True)


def render_sector_analysis(df, title):
    """Análisis por sector."""
    st.subheader(f"🏢 {title}")
    
    if 'Sector' not in df.columns:
        st.warning("No hay datos de sector")
        return
    
    df = df.copy().reset_index(drop=True)
    sector_stats = df.groupby('Sector').agg({
        'Rentabilidad prevista': 'mean',
        'sharpe_ratio': 'mean',
        'Dividend Yield': 'mean',
        'Ticker': 'count'
    }).rename(columns={'Ticker': 'Num. Empresas'})
    
    sector_stats = sector_stats.sort_values('Rentabilidad prevista', ascending=False)
    
    # Formatear
    sector_stats['Rentabilidad prevista'] = sector_stats['Rentabilidad prevista'].apply(
        lambda x: f"{x:.1f}%" if pd.notna(x) else "-"
    )
    sector_stats['sharpe_ratio'] = sector_stats['sharpe_ratio'].apply(
        lambda x: f"{x:.2f}" if pd.notna(x) else "-"
    )
    sector_stats['Dividend Yield'] = sector_stats['Dividend Yield'].apply(
        lambda x: f"{x:.2f}%" if pd.notna(x) else "-"
    )
    
    st.dataframe(sector_stats.head(10), use_container_width=True)


def render_risk_analysis(df):
    """Análisis de riesgo."""
    st.subheader("⚠️ Análisis de Riesgo")
    
    df = df.copy().reset_index(drop=True)
    col1, col2 = st.columns(2)
    
    with col1:
        # Acciones más volátiles
        st.markdown("**🔴 Mayor Volatilidad**")
        if 'volatilidad' in df.columns:
            high_vol = df.nlargest(5, 'volatilidad')[['Empresa', 'Ticker', 'volatilidad']].copy()
            high_vol['volatilidad'] = high_vol['volatilidad'].apply(lambda x: f"{x*100:.2f}%")
            st.dataframe(high_vol, use_container_width=True, hide_index=True)
    
    with col2:
        # Acciones con beta alta
        st.markdown("**📊 Mayor Beta (vs mercado)**")
        if 'beta_calculada' in df.columns:
            high_beta = df.nlargest(5, 'beta_calculada')[['Empresa', 'Ticker', 'beta_calculada']].copy()
            high_beta['beta_calculada'] = high_beta['beta_calculada'].apply(lambda x: f"{x:.2f}")
            st.dataframe(high_beta, use_container_width=True, hide_index=True)


def render_value_stocks(df):
    """Acciones infravaloradas."""
    st.subheader("💎 Posibles Oportunidades de Valor")
    
    # Filtrar acciones con:
    # - Rentabilidad prevista positiva
    # - P/E razonable
    # - Sharpe positivo
    
    value = df.copy().reset_index(drop=True)
    
    conditions = pd.Series([True] * len(value), index=value.index)
    
    if 'Rentabilidad prevista' in value.columns:
        conditions = conditions & (value['Rentabilidad prevista'] > 10)
    
    if 'P/E (Forward)' in value.columns:
        conditions = conditions & (value['P/E (Forward)'] > 0) & (value['P/E (Forward)'] < 25)
    
    if 'sharpe_ratio' in value.columns:
        conditions = conditions & (value['sharpe_ratio'] > 0.5)
    
    value_stocks = value.loc[conditions]
    
    if value_stocks.empty:
        st.info("No se encontraron acciones que cumplan todos los criterios de valor")
        return
    
    cols = ['Empresa', 'Ticker', 'Sector', 'Rentabilidad prevista', 'P/E (Forward)', 'sharpe_ratio']
    cols_available = [c for c in cols if c in value_stocks.columns]
    
    display = value_stocks[cols_available].head(10)
    
    if 'Rentabilidad prevista' in display.columns:
        display['Rentabilidad prevista'] = display['Rentabilidad prevista'].apply(
            lambda x: f"{x:.1f}%" if pd.notna(x) else "-"
        )
    
    st.dataframe(display, use_container_width=True, hide_index=True)


def render_summary_metrics(df, index_name):
    """Métricas resumen del índice."""
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        total = len(df)
        st.metric("Total Empresas", total)
    
    with col2:
        if 'Rentabilidad prevista' in df.columns:
            positive = (df['Rentabilidad prevista'] > 0).sum()
            pct = (positive / total * 100) if total > 0 else 0
            st.metric("Rentab. Positiva", f"{positive}", f"{pct:.0f}%")
    
    with col3:
        if 'sharpe_ratio' in df.columns:
            good_sharpe = (df['sharpe_ratio'] > 1).sum()
            st.metric("Sharpe > 1", good_sharpe)
    
    with col4:
        if 'Dividend Yield' in df.columns:
            high_div = (df['Dividend Yield'] > 0.03).sum()
            st.metric("Dividendo > 3%", high_div)
    
    with col5:
        if 'Rentabilidad prevista' in df.columns:
            avg_return = df['Rentabilidad prevista'].mean()
            st.metric("Rent. Media", f"{avg_return:.1f}%")


# =============================================================================
# DIVIDENDOS PRÓXIMOS (IBEX 35 + S&P 500)
# =============================================================================

def _render_dividend_calendar(combined: pd.DataFrame):
    """Scatter temporal: eje X = Ex-Dividend Date, eje Y = Yield."""
    st.subheader("📅 Calendario de Ex-Dividendos")
    hover_cols = {
        'Ticker': True,
        'Días hasta Ex-Div': True,
        'Yield (%)': ':.2f',
        'Ex-Dividend Date': '|%d %b %Y',
    }
    if 'Sector' in combined.columns:
        hover_cols['Sector'] = True
    if 'Next Dividend' in combined.columns:
        hover_cols['Next Dividend'] = ':.4f'

    fig = px.scatter(
        combined,
        x='Ex-Dividend Date',
        y='Yield (%)',
        color='Índice',
        size=combined['Yield (%)'].clip(lower=0.1),
        size_max=22,
        hover_name='Empresa',
        hover_data=hover_cols,
        labels={'Ex-Dividend Date': 'Fecha Ex-Dividendo', 'Yield (%)': 'Dividend Yield (%)'},
        color_discrete_map={'IBEX 35': '#EF553B', 'S&P 500': '#00CC96'},
    )
    fig.update_layout(height=450, hovermode='closest')
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Debes poseer la acción ANTES de la fecha Ex-Div para cobrar el dividendo. "
        "Burbuja más grande = mayor yield."
    )


def _render_dividend_yield_chart(combined: pd.DataFrame):
    """Top 25 empresas por dividend yield (barras horizontales)."""
    st.subheader("📊 Empresas con Mayor Dividend Yield")
    top = combined.nlargest(25, 'Yield (%)').copy()
    top['label'] = top.apply(
        lambda r: f"{r.get('Ticker', r.get('Empresa', ''))} ({r['Índice']})", axis=1
    )
    extra_hover = {}
    if 'Next Dividend' in top.columns:
        extra_hover['Next Dividend'] = True
    if 'Rentabilidad prevista' in top.columns:
        extra_hover['Rentabilidad prevista'] = True

    fig = px.bar(
        top.sort_values('Yield (%)'),
        x='Yield (%)',
        y='label',
        orientation='h',
        color='Índice',
        text='Yield (%)',
        hover_data={
            'Empresa': True,
            'Ex-Dividend Date': True,
            **extra_hover,
        },
        labels={'label': ''},
        color_discrete_map={'IBEX 35': '#EF553B', 'S&P 500': '#00CC96'},
    )
    fig.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
    fig.update_layout(height=max(420, len(top) * 28), showlegend=True)
    st.plotly_chart(fig, use_container_width=True)


def _render_dividend_detail(df_ibex: pd.DataFrame, df_sp500: pd.DataFrame):
    """Tablas detalladas separadas por índice."""
    display_cols = [
        'Empresa', 'Ticker', 'Sector', 'Ex-Dividend Date',
        'Next Dividend', 'Dividend Yield', 'Rentabilidad prevista', 'rank_dividend',
    ]

    def _fmt(df: pd.DataFrame) -> pd.DataFrame:
        d = df[[c for c in display_cols if c in df.columns]].copy()
        if 'Dividend Yield' in d.columns:
            d['Dividend Yield'] = d['Dividend Yield'].apply(
                lambda x: f"{x * 100:.2f}%" if pd.notna(x) else "-"
            )
        if 'Rentabilidad prevista' in d.columns:
            d['Rentabilidad prevista'] = d['Rentabilidad prevista'].apply(
                lambda x: f"{x:.1f}%" if pd.notna(x) else "-"
            )
        if 'Ex-Dividend Date' in d.columns:
            d['Ex-Dividend Date'] = pd.to_datetime(
                d['Ex-Dividend Date'], errors='coerce'
            ).dt.strftime('%d %b %Y')
        if 'Ex-Dividend Date' in d.columns:
            d = d.sort_values('Ex-Dividend Date')
        return d

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 🇪🇸 IBEX 35")
        if not df_ibex.empty:
            st.dataframe(_fmt(df_ibex), use_container_width=True, hide_index=True)
        else:
            st.info("No hay datos de dividendos para IBEX 35")
    with col2:
        st.markdown("#### 🇺🇸 S&P 500")
        if not df_sp500.empty:
            st.dataframe(_fmt(df_sp500), use_container_width=True, hide_index=True)
        else:
            st.info("No hay datos de dividendos para S&P 500")


def render_dividends_tab(data: dict):
    """Pestaña de dividendos próximos de IBEX 35 y S&P 500 combinados."""
    div_ibex = data.get('Dividendos IBEX', pd.DataFrame())
    div_sp500 = data.get('Dividendos SP500', pd.DataFrame())

    if div_ibex.empty and div_sp500.empty:
        st.info("No hay datos de dividendos. Ejecuta primero `python main.py`.")
        return

    # Combinar con etiqueta de índice
    frames = []
    for raw, label in [(div_ibex, 'IBEX 35'), (div_sp500, 'S&P 500')]:
        if not raw.empty:
            df = raw.copy()
            df['Índice'] = label
            frames.append(df)
    combined = pd.concat(frames, ignore_index=True)

    # Normalizar fechas y calcular días
    combined['Ex-Dividend Date'] = pd.to_datetime(combined['Ex-Dividend Date'], errors='coerce')
    combined = combined.dropna(subset=['Ex-Dividend Date'])
    today = pd.Timestamp.today().normalize()
    combined['Días hasta Ex-Div'] = (combined['Ex-Dividend Date'] - today).dt.days
    combined = combined[combined['Días hasta Ex-Div'] >= 0].sort_values('Días hasta Ex-Div').reset_index(drop=True)

    # Yield en porcentaje
    combined['Yield (%)'] = (combined['Dividend Yield'] * 100).where(
        combined['Dividend Yield'].notna(), other=None
    ) if 'Dividend Yield' in combined.columns else None

    # Filtro de horizonte temporal
    max_days = int(combined['Días hasta Ex-Div'].max()) if not combined.empty else 365
    days_filter = st.slider(
        "Mostrar dividendos en los próximos (días)",
        min_value=30, max_value=min(365, max_days + 1),
        value=min(180, max_days),
        key="div_days_filter",
    )
    combined = combined[combined['Días hasta Ex-Div'] <= days_filter].reset_index(drop=True)

    if combined.empty:
        st.info(f"No hay dividendos registrados en los próximos {days_filter} días.")
        return

    # Métricas resumen
    ibex_count = (combined['Índice'] == 'IBEX 35').sum()
    sp500_count = (combined['Índice'] == 'S&P 500').sum()
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Próximos dividendos", len(combined),
                  f"IBEX 35: {ibex_count}  ·  S&P 500: {sp500_count}")
    with c2:
        next_row = combined.iloc[0]
        empresa = next_row.get('Empresa', next_row.get('Ticker', ''))
        st.metric("Más próximo", next_row['Ex-Dividend Date'].strftime('%d %b %Y'),
                  f"{empresa} · {next_row['Índice']}")
    with c3:
        if combined['Yield (%)'].notna().any():
            st.metric("Yield medio", f"{combined['Yield (%)'].mean():.2f}%")
    with c4:
        if combined['Yield (%)'].notna().any():
            max_row = combined.loc[combined['Yield (%)'].idxmax()]
            st.metric("Mayor yield", f"{max_row['Yield (%)']:.2f}%",
                      f"{max_row.get('Empresa', max_row.get('Ticker', ''))}")

    st.markdown("---")

    tab_cal, tab_yield, tab_detail = st.tabs(["📅 Calendario", "📊 Por Yield", "📋 Por Índice"])
    with tab_cal:
        _render_dividend_calendar(combined)
    with tab_yield:
        _render_dividend_yield_chart(combined)
    with tab_detail:
        _render_dividend_detail(div_ibex, div_sp500)


# =============================================================================
# PÁGINA PRINCIPAL
# =============================================================================

def main():
    # Header
    st.title("📈 Stock Market Analysis Dashboard")
    st.markdown(f"*Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    
    # Cargar datos
    data = load_data()
    
    if not data:
        st.error("❌ No se encontraron datos. Ejecuta primero el análisis con `python main.py`")
        st.stop()
    
    # Sidebar
    st.sidebar.title("🔧 Configuración")
    
    # Selector de índice
    available_indices = [k for k in data.keys() if k in ['IBEX 35', 'S&P 500']]
    selected_index = st.sidebar.selectbox(
        "Seleccionar Índice",
        available_indices,
        index=0 if available_indices else None
    )
    
    if not selected_index:
        st.warning("No hay índices disponibles")
        st.stop()
    
    # Copiar y resetear índice para evitar problemas de alineación
    df = data[selected_index].copy().reset_index(drop=True)
    
    # Filtros
    st.sidebar.markdown("---")
    st.sidebar.subheader("📊 Filtros")
    
    # Filtro por sector
    if 'Sector' in df.columns:
        sectors = ['Todos'] + sorted(df['Sector'].dropna().unique().tolist())
        selected_sector = st.sidebar.selectbox("Sector", sectors)
        if selected_sector != 'Todos':
            df = df[df['Sector'] == selected_sector].reset_index(drop=True)
    
    # Filtro por rentabilidad mínima
    min_return = st.sidebar.slider(
        "Rentabilidad Prevista Mínima (%)",
        min_value=-50,
        max_value=100,
        value=0
    )
    if 'Rentabilidad prevista' in df.columns:
        df = df[df['Rentabilidad prevista'] >= min_return].reset_index(drop=True)
    
    # Filtro por dividendo
    show_dividend_only = st.sidebar.checkbox("Solo con dividendos")
    if show_dividend_only and 'Dividend Yield' in df.columns:
        df = df[df['Dividend Yield'] > 0].reset_index(drop=True)
    
    st.sidebar.markdown("---")
    st.sidebar.info(f"📊 Mostrando {len(df)} empresas")
    
    # Contenido principal
    st.header(f"📊 {selected_index}")
    
    # Métricas resumen
    render_summary_metrics(data[selected_index], selected_index)
    
    st.markdown("---")
    
    # Tabs de contenido
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "🎯 Oportunidades",
        "📈 Evolución",
        "💰 Dividendos", 
        "🏢 Sectores",
        "📉 Riesgo/Rentabilidad",
        "⚠️ Análisis Riesgo",
        "💎 Valor"
    ])
    
    with tab1:
        render_top_opportunities(df, f"Top Oportunidades {selected_index}")
    
    with tab2:
        render_stock_evolution(df, selected_index)
    
    with tab3:
        render_dividends_tab(data)
    
    with tab4:
        col1, col2 = st.columns(2)
        with col1:
            render_sector_analysis(df, f"Rendimiento por Sector - {selected_index}")
        with col2:
            render_sector_performance(df)
    
    with tab5:
        render_volatility_chart(df)
    
    with tab6:
        render_risk_analysis(df)
    
    with tab7:
        render_value_stocks(df)
    
    # Tabla completa
    st.markdown("---")
    with st.expander("📋 Ver todos los datos"):
        st.dataframe(df, use_container_width=True, hide_index=True)
    
    # Footer
    st.markdown("---")
    st.markdown(
        "*Dashboard generado por Stock Market Analysis | "
        "Datos de Yahoo Finance | No es asesoramiento financiero*"
    )


if __name__ == "__main__":
    main()
