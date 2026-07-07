# CLAUDE.md — Stock Market Analysis

## Descripción del proyecto

Sistema automatizado de análisis bursátil para **IBEX 35** y **S&P 500** con:
- Cálculo de métricas financieras (RSI, Sharpe, Alpha, Beta, MA50/MA200, etc.)
- Sistema de alertas de trading enviadas vía **Telegram**
- Dashboard interactivo con **Streamlit + Plotly**
- Ejecución diaria automatizada mediante **Apache Airflow**
- Pipeline **CI/CD con Jenkins** y rollback automático

---

## Estructura del repositorio

```
stock-market-analysis/
├── src/
│   ├── main.py                    # Punto de entrada: orquesta todo el pipeline ETL + alertas
│   ├── config.py                  # Lee variables de entorno (.env) y expone constantes globales
│   ├── dashboard.py               # App Streamlit — ejecutar con: streamlit run src/dashboard.py
│   ├── dag-stock-analysis.py      # DAG Airflow (schedule: 9:00 AM diario)
│   ├── etl/
│   │   ├── variables.py           # Tickers IBEX35, S&P500 y ETFs; períodos de análisis
│   │   ├── functions.py           # Extracción yfinance + cálculo de todos los indicadores
│   │   ├── get_index_data.py      # Orquestación ETL por índice + generación de gráficos PNG
│   │   └── alerts.py              # Clase AlertManager: detección de señales + envío Telegram
│   ├── analisis-cartera/
│   │   ├── main.py                # Análisis de cartera personal (independiente)
│   │   └── dashboard_cartera.py   # Dashboard Streamlit para cartera personal
│   └── notebooks/                 # Notebooks exploratorios Jupyter
├── tests/
│   ├── conftest.py                # Fixtures compartidas (DataFrames sintéticos)
│   ├── test_alerts.py             # Tests de AlertManager y todos los tipos de señal
│   ├── test_functions.py          # Tests de extracción y cálculo de indicadores
│   ├── test_config.py             # Tests de carga de configuración
│   └── test_main.py               # Tests de integración del pipeline principal
├── docs/                          # Documentación adicional
├── Jenkinsfile                    # Pipeline CI/CD con rollback automático
├── pytest.ini                     # Configuración de pytest
└── requirements.txt               # Dependencias Python
```

---

## Cómo ejecutar

### Análisis completo (ETL + alertas)
```bash
cd src
python main.py
```

### Dashboard interactivo
```bash
streamlit run src/dashboard.py
```

### Tests
```bash
pytest tests/
```

---

## Variables de entorno (.env)

Copia `.env.example` a `.env` y rellena:

```bash
TELEGRAM_BOT_TOKEN=         # Token del bot de Telegram (opcional)
TELEGRAM_CHAT_ID=           # Chat ID destino (opcional)
ANALYSIS_MONTHS_BACK=6      # Meses de histórico a analizar
RSI_PERIOD=14
RSI_OVERSOLD_THRESHOLD=30
RSI_OVERBOUGHT_THRESHOLD=70
DIVIDEND_ALERT_DAYS=7
DAILY_DROP_THRESHOLD=5.0
EXPECTED_RETURN_THRESHOLD=20.0
LOG_LEVEL=INFO
```

Si no se configuran las variables de Telegram, el análisis se ejecuta igualmente pero sin enviar notificaciones.

---

## Módulos clave

### `src/etl/variables.py`
Define los diccionarios de tickers:
- `ibex35_tickers` — 36 empresas del IBEX 35 (sufijo `.MC`)
- `tickers_sp500` — ~65 empresas representativas del S&P 500
- `tickers_index` — ETFs globales (MSCI World, Stoxx 600, etc.)
- `start_period` / `end_period` — ventana temporal calculada desde `ANALYSIS_MONTHS_BACK`

### `src/etl/functions.py`
Funciones puras de análisis:
- `extraction_historic(tickers, start, end)` → descarga precios con yfinance y calcula retornos diarios, RSI, MA50/MA200, Sharpe, Alpha, Beta, P/E, P/B, Dividend Yield

### `src/etl/get_index_data.py`
- `get_index(name, tickers, benchmark, start, end, folder, filename)` → ejecuta el ETL completo para un índice, guarda CSV y Parquet, genera gráficos PNG
- `get_etf_data(tickers, start, end)` → extrae y grafica ETFs globales

### `src/etl/alerts.py`
Clase `AlertManager` con `run_all_checks(df, historical)`:
- RSI sobrevendido/sobrecomprado
- Golden Cross / Death Cross (MA50 vs MA200)
- Dividendos próximos
- Caída diaria significativa
- Alta rentabilidad prevista

### `src/config.py`
Expone como constantes todo lo leído del `.env`. Importar desde aquí, nunca leer `os.environ` directamente en otros módulos.

---

## Salidas generadas (directorio `data/`)

| Archivo | Descripción |
|---------|-------------|
| `ibex35_analysed_df.csv` | Análisis completo IBEX 35 |
| `sp500_analysed_df.csv` | Análisis completo S&P 500 |
| `dividendos_ibex35_analysed_df.csv` | Próximos dividendos IBEX 35 |
| `dividendos_sp500_analysed_df.csv` | Próximos dividendos S&P 500 |
| `ibex35_historic/*.parquet` | Histórico por acción IBEX 35 |
| `sp500_historic/*.parquet` | Histórico por acción S&P 500 |
| `*.png` | Gráficos de volatilidad y rentabilidad |

---

## Pipeline Jenkins (`Jenkinsfile`)

1. **Backup** — guarda el commit actual en `/tmp/stock_analysis_last_commit.txt`
2. **Actualizar** — `git pull origin main`
3. **Instalar dependencias** — recrea `.venv` solo si `requirements.txt` cambió (hash SHA256)
4. **Test Imports** — verifica que todos los módulos importan sin errores
5. **Test Dashboard** — comprueba Streamlit y Plotly
6. **Test Sintaxis** — `py_compile` sobre todos los `.py`
7. **Post failure** — rollback automático al commit previo

---

## Convenciones de desarrollo

- Todo acceso a configuración va a través de `src/config.py`
- Los nuevos índices se añaden en `variables.py` (tickers) y en el `index_dictionary` de `main.py`
- Las alertas nuevas se implementan en `AlertManager` dentro de `alerts.py`
- El dashboard usa `@st.cache_data(ttl=3600)` para todas las cargas de datos
- Tests con `pytest` + `pytest-mock`; los fixtures de DataFrames van en `conftest.py`
- Python 3.10+ requerido (usar 3.10–3.12 para mayor estabilidad con matplotlib)
