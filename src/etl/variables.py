from datetime import datetime
import os

# --- CONFIGURACIÓN DE DIRECTORIOS ---
PROJECT_DIR = os.getcwd()
DATA_DIR = os.path.join(PROJECT_DIR, 'data')
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)


start_period = datetime(2025, 1, 1)
end_period = datetime(2025, 9, 11)


ibex35_tickers = {
    "ANA.MC": "Acciona", "ANE.MC": "Acciona Energía", "ACX.MC": "Acerinox",
    "ACS.MC": "ACS", "AENA.MC": "Aena", "AMS.MC": "Amadeus",
    "BBVA.MC": "BBVA", "BKT.MC": "Bankinter", "CABK.MC": "CaixaBank",
    "CLNX.MC": "Cellnex Telecom", "COL.MC": "Inmobiliaria Colonial", "ELE.MC": "Endesa",
    "ENG.MC": "Enagás", "FDR.MC": "Fluidra", "FER.MC": "Ferrovial",
    "GRF.MC": "Grifols", "IAG.MC": "IAG (International Airlines Group)", "IBE.MC": "Iberdrola",
    "IDR.MC": "Indra", "ITX.MC": "Inditex", "LOG.MC": "Logista",
    "MAP.MC": "Mapfre", "MEL.MC": "Meliá Hotels International", "MRL.MC": "Merlin Properties",
    "MTS.MC": "ArcelorMittal", "NTGY.MC": "Naturgy", "PUIG.MC": "Puig",
    "RED.MC": "Redeia", "REP.MC": "Repsol", "ROVI.MC": "Rovi",
    "SAB.MC": "Banco Sabadell", "SAN.MC": "Banco Santander", "SCYR.MC": "Sacyr",
    "SLR.MC": "Solaria", "TEF.MC": "Telefónica", "UNI.MC": "Unicaja Banco"
}

tickers_sp500 = {
    "AAPL": "Apple Inc.", "MSFT": "Microsoft Corporation", "NVDA": "NVIDIA Corporation",
    "GOOGL": "Alphabet Inc. (Clase A)", "AMZN": "Amazon.com, Inc.", "META": "Meta Platforms, Inc.",
    "TSLA": "Tesla, Inc.", "BRK-B": "Berkshire Hathaway Inc.", "JPM": "JPMorgan Chase & Co.",
    "V": "Visa Inc.", "LLY": "Eli Lilly and Co.", "JNJ": "Johnson & Johnson",
    "PG": "Procter & Gamble Co.", "UNH": "UnitedHealth Group Inc.", "HD": "Home Depot, Inc.",
    "ABBV": "AbbVie Inc.", "BAC": "Bank of America Corp.", "KO": "Coca-Cola Company",
    "PEP": "PepsiCo, Inc.", "CRM": "Salesforce, Inc.", "ORCL": "Oracle Corporation",
    "CSCO": "Cisco Systems, Inc.", "TMO": "Thermo Fisher Scientific", "QCOM": "Qualcomm Inc.",
    "ADBE": "Adobe Inc.", "INTC": "Intel Corporation", "TXN": "Texas Instruments Inc.",
    "BLK": "BlackRock, Inc.", "LMT": "Lockheed Martin Corp.", "ABT": "Abbott Laboratories",
    "CAT": "Caterpillar Inc.", "MRK": "Merck & Co., Inc.", "AMGN": "Amgen Inc.",
    "MCD": "McDonald's Corp.", "NKE": "Nike, Inc.", "XOM": "Exxon Mobil Corp.",
    "WMT": "Walmart Inc.", "JCI": "Johnson Controls plc", "GE": "General Electric Co.",
    "MMM": "3M Company", "PFE": "Pfizer Inc.", "CVS": "CVS Health Corp.",
    "CL": "Colgate-Palmolive", "DIS": "Walt Disney Company", "RTX": "RTX Corporation",
    "UBER": "Uber Technologies", "NOW": "ServiceNow, Inc.", "SPGI": "S&P Global Inc.",
    "MDT": "Medtronic plc", "NEE": "NextEra Energy, Inc.", "LOW": "Lowe's Companies, Inc.",
    "PYPL": "PayPal Holdings", "INTU": "Intuit Inc.", "ADP": "Automatic Data Processing",
    "ISRG": "Intuitive Surgical", "AMT": "American Tower Corp.", "CSX": "CSX Corporation",
    "DUK": "Duke Energy Corp.", "AVGO": "Broadcom Inc.", "GOOG": "Alphabet Inc. (Clase C)",
    "NFLX": "Netflix, Inc.", "MA": "Mastercard Incorporated", "COST": "Costco Wholesale Corp.",
}

tickers_index = {
    "IWDA.AS": "MSCI World",
    "CSPX.AS": "S&P 500",
    "CS1.PA": "IBEX 35",
    "EUNK.DE": "Core MSCI Europe",
    "LYP6.DE": "Stoxx Europe 600",
    '^GSPC': "SP500 Index",
    '^IBEX': "IBEX35 Index",
    "GREK": "Global X MSCI Greece ETF",
    "EPOL": "iShares MSCI Poland ETF",
    "EWP": "iShares MSCI Spain ETF",
}