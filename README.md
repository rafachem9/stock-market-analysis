# Stock Market Analysis

Sistema automatizado de análisis bursátil para **IBEX 35** y **S&P 500** con alertas en tiempo real vía Telegram.

---

## Características

- **Análisis de índices**: IBEX 35, S&P 500 y ETFs globales
- **Métricas financieras**: Sharpe Ratio, Alpha, Beta, Volatilidad, RSI, Rentabilidad acumulada
- **Sistema de alertas**: Detección de señales de trading (RSI, cruces de medias móviles, dividendos)
- **Notificaciones Telegram**: Alertas en tiempo real a tu dispositivo móvil
- **Automatización**: DAG de Airflow para ejecución diaria programada
- **Exportación de datos**: CSV y Parquet para análisis posterior
- **Gráficos**: Volatilidad y rentabilidad acumulada por índice

---

## Estructura del Proyecto

```
stock-market-analysis/
├── src/
│   ├── config.py              # Configuración centralizada
│   ├── main.py                # Punto de entrada principal
│   ├── dag-stock-analysis.py  # DAG de Airflow
│   └── etl/
│       ├── variables.py       # Tickers y variables de período
│       ├── functions.py       # Funciones de análisis
│       ├── get_index_data.py  # Extracción y gráficos
│       └── alerts.py          # Sistema de alertas
├── data/                      # Datos generados (CSV, Parquet, PNG)
├── requirements.txt           # Dependencias Python
├── .env.example               # Plantilla de variables de entorno
└── README.md
```

---

## Requisitos

### Python
- **Python 3.10+** recomendado

### Dependencias
```bash
pip install -r requirements.txt
```

Dependencias principales:
- `pandas` - Manipulación de datos
- `yfinance` - API de datos financieros
- `matplotlib` - Gráficos
- `python-telegram-bot` - Notificaciones Telegram
- `python-dotenv` - Gestión de variables de entorno

---

## Instalación

### 1. Clonar el repositorio
```bash
git clone https://github.com/rafachem9/stock-market-analysis.git
cd stock-market-analysis
```

### 2. Crear entorno virtual
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno
```bash
cp .env.example .env
# Editar .env con tus credenciales
```

---

## Configuración

### Variables de Entorno (.env)

Crea un archivo `.env` en la raíz del proyecto con las siguientes variables:

```bash
# ====================================
# CONFIGURACIÓN DE TELEGRAM (opcional)
# ====================================
TELEGRAM_BOT_TOKEN=tu_bot_token_aqui
TELEGRAM_CHAT_ID=tu_chat_id_aqui

# ====================================
# RUTAS (opcional - usa valores por defecto)
# ====================================
# PROJECT_DIR=/ruta/al/proyecto
# DATA_DIR=/ruta/al/directorio/data

# ====================================
# PERÍODO DE ANÁLISIS
# ====================================
# Número de meses hacia atrás para analizar (por defecto: 12)
ANALYSIS_MONTHS_BACK=6

# ====================================
# PARÁMETROS DE RSI
# ====================================
RSI_PERIOD=14
RSI_OVERSOLD_THRESHOLD=30
RSI_OVERBOUGHT_THRESHOLD=70

# ====================================
# UMBRALES DE ALERTAS
# ====================================
# Días de anticipación para alertas de dividendos
DIVIDEND_ALERT_DAYS=7

# Umbral de caída diaria para generar alerta (%)
DAILY_DROP_THRESHOLD=5.0

# Umbral de rentabilidad prevista para alerta (%)
EXPECTED_RETURN_THRESHOLD=20.0

# ====================================
# LOGGING
# ====================================
LOG_LEVEL=INFO
```

### Configurar Bot de Telegram

1. Abre Telegram y busca `@BotFather`
2. Envía `/newbot` y sigue las instrucciones
3. Copia el **token** proporcionado → `TELEGRAM_BOT_TOKEN`
4. Inicia conversación con tu bot (envía `/start`)
5. Visita `https://api.telegram.org/bot<TOKEN>/getUpdates`
6. Copia el `chat_id` del resultado → `TELEGRAM_CHAT_ID`

---

## Uso

### Ejecución Manual

```bash
cd src
python main.py
```

### Desde cualquier directorio

```bash
python /ruta/al/proyecto/src/main.py
```

---

## Salidas Generadas

### Archivos CSV
| Archivo | Descripción |
|---------|-------------|
| `ibex35_analysed_df.csv` | Análisis completo IBEX 35 |
| `sp500_analysed_df.csv` | Análisis completo S&P 500 |
| `dividendos_ibex35_analysed_df.csv` | Próximos dividendos IBEX 35 |
| `dividendos_sp500_analysed_df.csv` | Próximos dividendos S&P 500 |

### Gráficos PNG
| Archivo | Descripción |
|---------|-------------|
| `ibex_35_volatility_{año}.png` | Volatilidad diaria IBEX 35 |
| `sp500_volatility_{año}.png` | Volatilidad diaria S&P 500 |
| `etf_return_{año}.png` | Rentabilidad acumulada ETFs |
| `etf_volatility_{año}.png` | Volatilidad ETFs |

### Datos Parquet
Los datos históricos se guardan en formato Parquet en:
- `data/ibex35_historic/`
- `data/sp500_historic/`

---

## Sistema de Alertas

### Tipos de Alertas

| Tipo | Descripción | Umbral por defecto |
|------|-------------|-------------------|
| **RSI Sobrevendido** | RSI < 30 (oportunidad de compra) | RSI < 30 |
| **RSI Sobrecomprado** | RSI > 70 (posible venta) | RSI > 70 |
| **Golden Cross** | MA50 cruza por encima de MA200 | - |
| **Death Cross** | MA50 cruza por debajo de MA200 | - |
| **Dividendos Próximos** | Dividendos en los próximos N días | 7 días |
| **Caída Significativa** | Caída diaria superior al umbral | 5% |
| **Alta Rentabilidad Prevista** | Rentabilidad esperada alta | 20% |

### Ver Alertas

Las alertas se muestran:
1. **Consola**: Durante la ejecución del script
2. **Telegram**: Si está configurado, recibes notificaciones en tiempo real
3. **Logs**: Archivo de log con historial completo

---

## Métricas Calculadas

### Por Acción
- **Rentabilidad**: Daily Return, Cumulative Return
- **Volatilidad**: Desviación estándar de retornos diarios
- **RSI**: Relative Strength Index (14 períodos)
- **Medias Móviles**: MA50, MA200
- **Sharpe Ratio**: Rentabilidad ajustada al riesgo
- **Alpha**: Exceso de retorno vs benchmark
- **Beta**: Sensibilidad al mercado
- **Dividend Yield**: Rentabilidad por dividendo
- **P/E Ratio**: Price to Earnings
- **P/B Ratio**: Price to Book

### Rankings
- `rank_per`: Ranking por rentabilidad esperada
- `rank_dividend`: Ranking por dividendos

---

## Automatización con Airflow

### Configuración del DAG

El archivo `src/dag-stock-analysis.py` está listo para integrarse en Apache Airflow:

```python
schedule_interval='0 9 * * *'  # Todos los días a las 9:00 AM
```

### Variables de Entorno para Airflow

```bash
STOCK_ANALYSIS_SRC_PATH=/ruta/a/src
STOCK_ANALYSIS_DATA_PATH=/ruta/a/data
```

### Funcionalidades del DAG
- Ejecución diaria automática
- Envío de email con reportes adjuntos
- Gráficos integrados en el email

---

## Desarrollo

### Estructura de Módulos

```
src/etl/
├── variables.py      # Configuración de tickers y períodos
├── functions.py      # Funciones de extracción y análisis
├── get_index_data.py # Orquestación y gráficos
└── alerts.py         # Sistema de alertas y Telegram
```

### Añadir Nuevos Índices

1. Agregar tickers en `variables.py`
2. Añadir entrada en `index_dictionary` en `main.py`

### Personalizar Alertas

Modificar umbrales en `.env` o directamente en `config.py`.

---

## Troubleshooting

### Error: "Chat not found" en Telegram
- Asegúrate de haber iniciado conversación con el bot (`/start`)

### Error: "RecursionError" con matplotlib
- El proyecto incluye un parche para Python 3.14 beta
- Usar Python 3.10-3.12 para mayor estabilidad

### Los datos no se actualizan
- Verificar conexión a internet
- yfinance puede tener delays de 15-20 minutos

---

## Licencia

MIT License - Ver archivo LICENSE para más detalles.

---

## Autor

**Rafael** - [@rafachem9](https://github.com/rafachem9)
