import os
import re
import json
from pathlib import Path
from collections import defaultdict

def print_progress_bar(iteration, total, prefix='', suffix='', decimals=1, length=40, fill='#', print_end='\r'):
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end=print_end)
    if iteration == total:
        print()

# Pfade definieren
WORKSPACE_DIR = Path(__file__).parent.parent.resolve()
FOREX_FILES_DIR = WORKSPACE_DIR / "extracted_data" / "forex_files"
CHUNKS_DIR = WORKSPACE_DIR / "extracted_data" / "chat_chunks"
REPORT_DIR = WORKSPACE_DIR / "report"

# Liste der Roboter und ihre Suchbegriffe
ROBOTS_REGISTRY = {
    "Waka_Waka_EA": {
        "name": "Waka Waka EA",
        "search_terms": ["waka waka", "wakawaka"],
        "strategy": "Grid / Martingale",
        "risk": "Very High",
        "timeframe": "M15",
        "pairs": "AUDCAD, AUDNZD, NZDCAD",
        "description": "Eines der bekanntesten Grid-Systeme auf dem Forex-Markt. Nutzt ausgefeilte Einstiegsraster und Martingale-Multiplikatoren zur Erholung aus Verlustphasen."
    },
    "WallStreet_Recovery_PRO": {
        "name": "WallStreet Recovery PRO / Forex Robot",
        "search_terms": ["wallstreet recovery", "wallstreet forex", "wallstreet robot", "wallstreet.mq4", "wallstreetx"],
        "strategy": "Ausbruchs-Scalper & Recovery",
        "risk": "Medium",
        "timeframe": "M15",
        "pairs": "EURUSD, GBPUSD, USDJPY, AUDUSD, USDCHF, USDCAD, NZDUSD",
        "description": "Basiert auf dem bewährten Kern des legendären WallStreet Forex Robot. Nutzt einen intelligenten mathematischen Recovery-Modus anstelle von unkontrolliertem Grid."
    },
    "Quantum_Queen_Athena": {
        "name": "Quantum Queen & Athena",
        "search_terms": ["quantum queen", "quantum athena", "qq mt5", "qa mt5", "qq ea", "qa ea"],
        "strategy": "Trend-Grid (Gold)",
        "risk": "Very High",
        "timeframe": "M15",
        "pairs": "XAUUSD (Gold)",
        "description": "Speziell für den hochvolatilen Goldmarkt konzipierte Grid-Systeme. Athena ist eine leichtere Version, während Queen bis zu 10 verschiedene Strategien parallel anbietet."
    },
    "AI_Gen_XII": {
        "name": "AI Gen XII",
        "search_terms": ["ai gen xii", "ai gen 12"],
        "strategy": "Devisen-Grid (Multi-Strategy)",
        "risk": "High",
        "timeframe": "M15",
        "pairs": "Hauptwährungspaare (Forex)",
        "description": "Einer der am intensivsten diskutierten Roboter im Chat. Bietet verschiedene Risikoprofile (Light, Moderate) über vordefinierte Presets."
    },
    "Can_Cu_Bu_Sieng_Nang": {
        "name": "Can Cu Bu Sieng Nang (CCBSN)",
        "search_terms": ["can cu bu", "ccbsn"],
        "strategy": "Asiatisches Devisen-Grid",
        "risk": "Very High",
        "timeframe": "M5",
        "pairs": "EURUSD, USDJPY, GBPUSD",
        "description": "Sehr populärer asiatischer Grid-Bot. Läuft laut Community auf Cent-Konten stabil, benötigt jedoch hohen Kapitalschutz."
    },
    "Boring_Pips": {
        "name": "Boring Pips MT4",
        "search_terms": ["boring pips", "boringpips"],
        "strategy": "Statistischer Scalper",
        "risk": "High",
        "timeframe": "M1 / M5",
        "pairs": "EURUSD, GBPUSD",
        "description": "Nutzt erweiterte statistische Algorithmen für Ein- und Ausstiege. Trotz des Namens ein dynamischer Scalper mit Grid-Absicherung."
    },
    "ForexCracked_AI": {
        "name": "ForexCracked AI",
        "search_terms": ["forexcracked.com_ai", "forexcracked ai"],
        "strategy": "AI LLM-Vision EA",
        "risk": "Low to Medium",
        "timeframe": "M15",
        "pairs": "Hauptwährungspaare (Forex)",
        "description": "Sendet Chart-Screenshots via WebRequest an KIs wie Gemini, Claude oder GPT, welche direkt über Ein-/Ausstiege sowie SL/TP entscheiden."
    },
    "RoyalPrince_Scalper": {
        "name": "RoyalPrince Scalper (Prince)",
        "search_terms": ["royalprince scalper", "prince scalper"],
        "strategy": "Gold-Scalper",
        "risk": "High",
        "timeframe": "M15",
        "pairs": "XAUUSD (Gold)",
        "description": "Ein von Admin @rp4000 bereitgestellter Scalping-EA für Gold. Muss stark auf den Broker-Spread hin optimiert werden."
    },
    "Vigorous_EA": {
        "name": "Vigorous EA (RFT)",
        "search_terms": ["vigorous"],
        "strategy": "Trendfolge-EA",
        "risk": "Low to Medium",
        "timeframe": "M15 / H1",
        "pairs": "EURUSD",
        "description": "Von Responsible Forex Trading entwickelt. Sucht nach Korrekturen (Price Dips) in Richtung des übergeordneten Trends. Läuft laut Live-Review stabil auf Darwinex."
    },
    "Forex_Fury": {
        "name": "Forex Fury (V3)",
        "search_terms": ["forex fury"],
        "strategy": "Zeitgesteuerter Scalper",
        "risk": "Medium",
        "timeframe": "M5",
        "pairs": "Cross-JPY (EURJPY, USDJPY, GBPJPY)",
        "description": "Handelt nur eine bestimmte Stunde am Tag (in ruhigen Marktphasen), um das Risiko plötzlicher Trendwenden zu reduzieren."
    },
    "Gold_Pure_V1": {
        "name": "Gold Pure V1",
        "search_terms": ["gold pure v1", "goldpure"],
        "strategy": "AI-Generated EA",
        "risk": "Medium",
        "timeframe": "M30 / H1",
        "pairs": "XAUUSD (Gold)",
        "description": "Ein von Gemini erstellter und von der Community optimierter EA. Läuft am besten ohne Trend-Filter mit großem SL/TP."
    },
    "Scalping_Entry_M5": {
        "name": "Scalping Entry M5",
        "search_terms": ["scalping entry m5"],
        "strategy": "Scalper (Source-Code)",
        "risk": "Low",
        "timeframe": "M5",
        "pairs": "Hauptwährungspaare (Forex)",
        "description": "Ein über Claude generierter Scalping-EA. Der größte Vorteil ist, dass der MQL5-Quellcode (.mq5) vollständig offenliegt."
    },
    "PropGuardian_Pro": {
        "name": "PropGuardian Pro",
        "search_terms": ["propguardian"],
        "strategy": "Challenge-Absicherung",
        "risk": "Medium",
        "timeframe": "H1",
        "pairs": "XAUUSD (Gold)",
        "description": "Ausgelegt auf das Bestehen von Prop-Firm-Challenges durch strikte Einhaltung täglicher Verlustgrenzen."
    },
    "VR_Smart_Grid": {
        "name": "VR Smart Grid",
        "search_terms": ["vr smart grid", "vr smartgrid"],
        "strategy": "Grid-EA",
        "risk": "High",
        "timeframe": "H1 / M15",
        "pairs": "Hauptpaare (Forex)",
        "description": "Ein flexibles Grid-Handelssystem mit visueller Oberfläche im MetaTrader."
    },
    "RoyalGamble_INDEX": {
        "name": "RoyalGamble INDEX",
        "search_terms": ["royalgamble.index", "royalgamble index"],
        "strategy": "Index-Grid",
        "risk": "Medium",
        "timeframe": "H1",
        "pairs": "US30, US500, GER40, USTECH",
        "description": "Speziell für den CFD-Index-Handel entwickelt und vorkonfiguriert."
    },
    "Hands_of_God": {
        "name": "Hands of God (Hand of God)",
        "search_terms": ["hands of god", "hand of god"],
        "strategy": "Hedge / Grid (Gefährlich)",
        "risk": "Extrem High",
        "timeframe": "M15",
        "pairs": "EURUSD",
        "description": "Wird von der Community als sehr riskant eingestuft. Führt oft zu hohem Drawdown auf Konten."
    },
    "Cobra_Scalper": {
        "name": "Cobra Scalper",
        "search_terms": ["cobra scalper"],
        "strategy": "Trend-Indikator & EA",
        "risk": "Medium",
        "timeframe": "M5",
        "pairs": "Hauptpaare (Forex)",
        "description": "Nutzt eine Kombination aus Trendkanälen und Volatilitätsfiltern."
    },
    "Goldwave_EA": {
        "name": "Goldwave EA",
        "search_terms": ["goldwave"],
        "strategy": "History Reader (Fake)",
        "risk": "Scam Warning",
        "timeframe": "M15",
        "pairs": "XAUUSD (Gold)",
        "description": "Verdacht auf History-Reading. Erzielt im Backtest perfekte Ergebnisse, nimmt live jedoch keine oder nur Verlusttrades."
    },
    "BB_Return": {
        "name": "BB Return mt5",
        "search_terms": ["bb return"],
        "strategy": "History Reader (Fake)",
        "risk": "Scam Warning",
        "timeframe": "M15",
        "pairs": "XAUUSD (Gold)",
        "description": "Vorsicht! Ein bekannter History-Reader, der Backtest-Ergebnisse manipuliert."
    },
    "Aura_Black_Edition": {
        "name": "Aura Black Edition",
        "search_terms": ["aura black"],
        "strategy": "History Reader (Fake)",
        "risk": "Scam Warning",
        "timeframe": "M15",
        "pairs": "Hauptpaare (Forex)",
        "description": "Wurde von der Community als manipulativer History-Reader entlarvt und vom Handel ausgeschlossen."
    },
    "Theranto_EA": {
        "name": "Theranto EA",
        "search_terms": ["theranto"],
        "strategy": "Scalper / Grid",
        "risk": "Medium",
        "timeframe": "M15",
        "pairs": "Hauptpaare (Forex)",
        "description": "Wird im Chat als solider Allrounder mit moderaten Drawdown-Phasen besprochen."
    },
    "Oracle_EA": {
        "name": "Oracle 2.0",
        "search_terms": ["oracle 2.0", "oracle ea"],
        "strategy": "Indikator / EA",
        "risk": "Medium",
        "timeframe": "H1",
        "pairs": "Hauptpaare (Forex)",
        "description": "Indikator-basierter EA mit Signalausgabe direkt auf dem Chart."
    },
    "Goldy_EA": {
        "name": "Goldy EA",
        "search_terms": ["goldy ea", "goldy"],
        "strategy": "Gold-Scalper",
        "risk": "High",
        "timeframe": "M15",
        "pairs": "XAUUSD (Gold)",
        "description": "Nutzt eine aggressive Scalping-Logik für Gold. Muss monatlich neu optimiert werden."
    },
    "Jesko_EA": {
        "name": "Jesko EA",
        "search_terms": ["jesko"],
        "strategy": "Ausbruchs-Scalper",
        "risk": "Medium",
        "timeframe": "H1",
        "pairs": "Hauptpaare (Forex)",
        "description": "Wird im Chat gelobt, allerdings sind viele verfügbare Versionen veraltet."
    },
    "Mansa_Musa": {
        "name": "Mansa Musa Algo",
        "search_terms": ["mansa musa", "mansamusa"],
        "strategy": "Trend-Grid",
        "risk": "High",
        "timeframe": "H1",
        "pairs": "Hauptpaare (Forex)",
        "description": "Basiert auf Trendkanälen, benötigt jedoch ein Passwort zur Aktivierung."
    },
    "Prop_King": {
        "name": "Prop King Bot",
        "search_terms": ["prop king", "propking"],
        "strategy": "Challenge-EA",
        "risk": "Medium",
        "timeframe": "M15",
        "pairs": "CFDs & Forex",
        "description": "Challenge-EA, der speziell für die Risikolimits von Prop-Firms entworfen wurde."
    },
    "Velox_Gold_Scalper": {
        "name": "Velox Gold Scalper",
        "search_terms": ["velox gold", "velox scalper"],
        "strategy": "Gold-Scalper",
        "risk": "High",
        "timeframe": "M5",
        "pairs": "XAUUSD (Gold)",
        "description": "Scalping-EA, der schnelle Kursausbrüche bei Gold handelt."
    },
    "RapidWave": {
        "name": "RapidWave",
        "search_terms": ["rapidwave"],
        "strategy": "Ausbruchs-Bot (Gold)",
        "risk": "High",
        "timeframe": "H1",
        "pairs": "XAUUSD (Gold)",
        "description": "Sucht nach Ausbrüchen auf H1-Goldcharts. Benötigt WebRequests-Anbindung."
    },
    "FundedEA_Deluxe": {
        "name": "FundedEA Deluxe",
        "search_terms": ["fundedea deluxe", "fundedea"],
        "strategy": "Challenge-Grid",
        "risk": "Medium",
        "timeframe": "M15",
        "pairs": "Hauptpaare (Forex)",
        "description": "Optimiert für Prop-Firm-Risikoüberwachung."
    },
    "Hedging_Mania": {
        "name": "Hedging Mania",
        "search_terms": ["hedging mania"],
        "strategy": "Hedging / Grid",
        "risk": "Very High",
        "timeframe": "M5",
        "pairs": "XAUUSD (Gold)",
        "description": "Asynchroner Hedging-EA. Öffnet parallele Buy- und Sell-Orders zur Marginabsicherung."
    },
    "ToTheMoon_NoPain": {
        "name": "ToTheMoon (NoPain Signal)",
        "search_terms": ["tothemoon", "nopain"],
        "strategy": "Grid / Martingale",
        "risk": "Very High",
        "timeframe": "H1",
        "pairs": "AUDCAD",
        "description": "Basiert auf dem bekannten MQL5-Kopiersignal 'NoPain' von Daniel Moraes Da Silva. Nutzt Smart Averaging und schließt Verlustpositionen schrittweise."
    },
    "HFT_Fast_M1_Gold_Scalper": {
        "name": "HFT Fast M1 Gold Scalper",
        "search_terms": ["hft fast m1", "gold scalper v8", "gold scalper v6"],
        "strategy": "High-Frequency Scalper",
        "risk": "Very High",
        "timeframe": "M1",
        "pairs": "XAUUSD (Gold)",
        "description": "High-Frequency Trading (HFT) Scalper für Gold. Erfordert extrem geringe Spreads und Latenzen (< 2ms ping zum Broker-Server via VPS)."
    },
    "RoyalGuard": {
        "name": "RoyalGuard (Drawdown-Schutz)",
        "search_terms": ["royalguard", "royal guard"],
        "strategy": "Risikomanagement / Drawdown-Schutz",
        "risk": "Low",
        "timeframe": "N/A",
        "pairs": "Alle Paare (Konto-Überwachung)",
        "description": "Ein reines Risiko-Management-Tool von @rp4000. Schließt alle Positionen, falls ein definiertes Verlustlimit überschritten wird. Dringend empfohlen für Grid-Bots."
    },
    "AW_Recovery": {
        "name": "AW Recovery EA",
        "search_terms": ["aw recovery"],
        "strategy": "Recovery / Grid Rescue",
        "risk": "Medium",
        "timeframe": "N/A",
        "pairs": "Alle Paare",
        "description": "Ein Rettungs-Tool für offene Verlust-Grids. Versucht, Verlustpositionen durch gezielte Absicherungen und Teilschließungen abzubauen."
    },
    "King_Robot": {
        "name": "King Robot",
        "search_terms": ["king robot"],
        "strategy": "Trend / Scalper",
        "risk": "High",
        "timeframe": "M15",
        "pairs": "Hauptpaare (Forex)",
        "description": "Ein Trendfolge- und Scalping-EA mit hoher Transaktionsfrequenz, der in den Chats intensiv diskutiert wurde."
    },
    "Bunny_EA": {
        "name": "Bunny EA",
        "search_terms": ["bunny ea", "bunnyea"],
        "strategy": "Grid / Scalper",
        "risk": "High",
        "timeframe": "M15",
        "pairs": "Hauptpaare (Forex)",
        "description": "Ein von der Community genutzter Grid-Scalper, der vor allem in Phasen geringer Volatilität gute Ergebnisse erzielt."
    },
    "Pip_Grid": {
        "name": "Pip Grid EA",
        "search_terms": ["pip grid"],
        "strategy": "Grid / Martingale",
        "risk": "Very High",
        "timeframe": "M15",
        "pairs": "Hauptpaare (Forex)",
        "description": "Klassisches Grid-System, das auf die Erfassung kleinerer Kursbewegungen im Forex-Markt setzt."
    },
    "Sup_9_Martingale": {
        "name": "Sup 9 Martingale",
        "search_terms": ["sup 9", "sup9"],
        "strategy": "Martingale / Grid",
        "risk": "Very High",
        "timeframe": "M15",
        "pairs": "Hauptpaare (Forex)",
        "description": "Aggressiver Martingale-Bot. Bietet extrem hohe Gewinnraten, birgt jedoch das Risiko eines Totalverlusts."
    }
}

# Positive & Negative englische Schlüsselwörter für Sentiment-Analyse
POSITIVE_KEYWORDS = [
    "perfect use", "stable profit", "highly recommend", "very profitable", "awesome ea",
    "best bot", "runs stable", "making money", "withdraw", "no drawdown", "low risk",
    "good ea", "nice profit", "consistency", "myfxbook", "verified", "love it",
    "works like a charm", "good results", "making profit", "super bot", "highly profitable",
    "safe settings", "profitable ea", "works well", "runs well", "real profit", "amazing bot"
]

NEGATIVE_KEYWORDS = [
    "blow", "scam", "fake", "trash", "lose", "lost", "garbage", "hazard", "blown", "cheat",
    "dangerous", "high risk", "wiped", "unstable", "not working", "don't use", "avoid",
    "scammer", "history reader", "fake version", "risk calculations", "bad risk",
    "unregulated", "blow account", "junk", "worst bot", "gambling"
]

def clean_comment(comment):
    # Entferne Nachrichten-Metadaten wie ID, Datum, Absender
    # Format: [398295] | [2026-04-06T06:18:15] | @rp4000 ❌Never DM First: Text
    pattern = r'^\[\d+\]\s*\|\s*\[[^\]]+\]\s*\|\s*[^:]+:\s*'
    cleaned = re.sub(pattern, '', comment)
    # Entferne evtl. Anhänge wie [Angehängte Forex-Datei: ...]
    cleaned = re.sub(r'\[Angehängte Forex-Datei:[^\]]+\]', '', cleaned)
    return cleaned.strip()

SUPPORTED_SYMBOLS = [
    "AUDCAD", "AUDCHF", "AUDJPY", "AUDNZD", "AUDUSD",
    "CADCHF", "CADJPY", "EURAUD", "EURCHF", "EURGBP",
    "EURJPY", "EURUSD", "GBPCHF", "GBPJPY", "GBPUSD",
    "NZDJPY", "NZDUSD", "USDCAD", "USDCHF", "USDJPY",
    "XAGUSD", "XAUUSD", "XTIUSD"
]

def parse_registry_pairs(pairs_str):
    if not pairs_str:
        return set()
    pairs_upper = pairs_str.upper()
    if any(k in pairs_upper for k in ["HAUPTWÄHRUNG", "FOREX", "MAJOR", "HAUPTPAARE", "FX"]):
        return {"EURUSD", "GBPUSD", "USDJPY"}
    
    matched = set()
    for sym in SUPPORTED_SYMBOLS:
        if sym in pairs_upper:
            matched.add(sym)
    if not matched:
        if "GOLD" in pairs_upper:
            return {"XAUUSD"}
        if "SILVER" in pairs_upper:
            return {"XAGUSD"}
    return matched

def parse_registry_periods(tf_str):
    if not tf_str:
        return set()
    tf_upper = tf_str.upper()
    matched = set()
    for tf in ["M1", "M5", "M15", "M30", "H1", "H4", "D1"]:
        if tf in tf_upper:
            matched.add(tf)
    return matched

def generate():
    print("[*] Starte Datenerhebung für Dashboard...")
    
    # LLM Insights laden falls vorhanden
    ea_insights = {}
    insights_path = WORKSPACE_DIR / "extracted_data" / "ea_insights.json"
    if insights_path.exists():
        try:
            ea_insights = json.loads(insights_path.read_text(encoding="utf-8"))
            print(f"  [+] {len(ea_insights)} LLM Insights aus ea_insights.json geladen.")
        except Exception as e:
            print(f"  [!] Fehler beim Laden von ea_insights.json: {e}")
    
    # 1. Alle Chat-Chunks einlesen und in einzelne Nachrichten splitten
    messages = []
    if CHUNKS_DIR.exists():
        chunk_files = list(CHUNKS_DIR.glob("chat_chunk_*.txt"))
        total_chunks = len(chunk_files)
        print("[*] [Step 1/5] Lese Chat-Chunks ein...")
        for idx, chunk_file in enumerate(chunk_files):
            try:
                content = chunk_file.read_text(encoding="utf-8")
                # Teile Nachrichten anhand des Trennstrichs
                parts = content.split("----------------------------------------")
                for p in parts:
                    clean_p = p.strip()
                    if clean_p:
                        messages.append(clean_p)
            except Exception as e:
                pass
            print_progress_bar(idx + 1, total_chunks, prefix='Fortschritt Chunks', suffix='gelesen', length=40)
                
    print(f"  [+] {len(messages)} Nachrichten aus Chat-Chunks eingelesen.")
    
    # 2. Alle Forex-Dateien auflisten für dynamisches Mapping
    forex_files = []
    if FOREX_FILES_DIR.exists():
        forex_files = os.listdir(FOREX_FILES_DIR)
    print(f"  [+] {len(forex_files)} Forex-Dateien im Verzeichnis gefunden.")
    
    # 2b. Dynamisches Register aller gefundenen EAs aufbauen
    print("[*] [Step 2/5] Erstelle dynamisches Register aller Roboter-Kandidaten...")
    active_registry = {}
    for k, v in ROBOTS_REGISTRY.items():
        active_registry[k] = v.copy()
        if "search_terms" not in active_registry[k]:
            active_registry[k]["search_terms"] = [k.lower().replace("_", " ")]

    def clean_name(filename):
        name, ext = os.path.splitext(filename)
        if ext.lower() not in ['.ex4', '.ex5', '.mq4', '.mq5', '.set']:
            return None
        name = re.sub(r'_msg\d+', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\b(?:fix|nodll|no_dll|unlocked|trial|free|demo|updated|version|final|pro|v?\d+(?:\.\d+)*)\b', '', name, flags=re.IGNORECASE)
        name = re.sub(r'[\(\)\[\]\{\}\-\+\~]', ' ', name)
        name = re.sub(r'\s+', ' ', name).strip()
        if len(name) < 3 or name.isdigit():
            return None
        generics = {'ea', 'indicator', 'bot', 'robot', 'scalper', 'grid', 'martingale', 'set', 'preset', 'file', 'setup'}
        words = name.split()
        clean_words = [w for w in words if w.lower() not in generics]
        if not clean_words:
            return None
        return " ".join(clean_words)

    robot_files = defaultdict(list)
    for f in forex_files:
        c_name = clean_name(f)
        if c_name:
            key = c_name.lower()
            robot_files[key].append(f)

    # Bereits registrierte EAs sammeln, um Duplikate zu vermeiden
    registered_keys = {k.lower() for k in active_registry.keys()}
    registered_names = {v["name"].lower() for v in active_registry.values()}

    print("[*] [Step 3/5] Durchsuche Chatverlauf für alle Kandidaten...")
    unified_text = "\n".join(messages).lower()
    total_candidates = len(robot_files)

    for idx, (key, files) in enumerate(robot_files.items()):
        folder_name = key.replace(" ", "_").title()
        if folder_name.lower() in registered_keys or key in registered_keys or key in registered_names:
            print_progress_bar(idx + 1, total_candidates, prefix='Fortschritt Register', suffix='gescannt', length=40)
            continue

        # Zähle Erwähnungen im Chat (optimierter C-Count)
        mentions_count = unified_text.count(key)

        # Wenn im Chat mindestens 5-mal erwähnt, füge dem aktiven Register hinzu!
        if mentions_count >= 5:
            # Bestimme Standard-Strategie & Risiko
            strategy = "Community EA"
            risk = "High"
            files_str = " ".join(files).lower()
            if "grid" in files_str or "martingale" in files_str:
                strategy = "Grid / Martingale"
                risk = "Very High"
            elif "scalp" in files_str:
                strategy = "Scalper"
                risk = "High"
            elif "trend" in files_str:
                strategy = "Trendfolger"
                risk = "Medium"

            active_registry[folder_name] = {
                "name": key.title(),
                "search_terms": [key],
                "strategy": strategy,
                "risk": risk,
                "timeframe": "M15 (Empfohlen)",
                "pairs": "Hauptwährungspaare",
                "description": f"Automatisch extrahierter Forex-Roboter mit {len(files)} zugeordneten Versionen. Aktiv in der Community diskutiert."
            }
        print_progress_bar(idx + 1, total_candidates, prefix='Fortschritt Register', suffix='gescannt', length=40)

    print(f"  [+] Register erfolgreich auf {len(active_registry)} Roboter erweitert.")

    # 3. Scan & Sentiment-Analyse durchführen
    robots_data = []
    
    print("[*] [Step 4/5] Führe Sentiment-Analyse, Symbol/Timeframe-Extraktion & Dateizuordnung durch...")
    total_robots = len(active_registry)
    for idx, (robot_id, meta) in enumerate(active_registry.items()):
        search_terms = meta["search_terms"]
        mentions_count = 0
        positive_comments = []
        negative_comments = []
        
        # Collect dynamically mentioned symbols and timeframes
        symbol_counts = defaultdict(int)
        period_counts = defaultdict(int)
        
        # Durchsuche Nachrichten
        for msg in messages:
            msg_lower = msg.lower()
            # Prüfe, ob einer der Suchbegriffe vorkommt
            has_mention = False
            for term in search_terms:
                if term in msg_lower:
                    has_mention = True
                    break
                    
            if has_mention:
                mentions_count += 1
                
                # Dynamic extraction of symbols from this discussion message
                for sym in SUPPORTED_SYMBOLS:
                    prefix = sym[:3].lower()
                    suffix = sym[3:].lower()
                    pattern = rf"\b{prefix}[-_/\s]?{suffix}\b"
                    if re.search(pattern, msg_lower):
                        symbol_counts[sym] += 1
                if "gold" in msg_lower or "xau" in msg_lower:
                    symbol_counts["XAUUSD"] += 1
                if "silver" in msg_lower or "xag" in msg_lower:
                    symbol_counts["XAGUSD"] += 1
                    
                # Dynamic extraction of periods from this discussion message
                patterns = {
                    "M1": [rf"\bm1\b", rf"\b1\s*min\b", rf"\b1\s*minute\b"],
                    "M5": [rf"\bm5\b", rf"\b5\s*min\b", rf"\b5\s*minute\b"],
                    "M15": [rf"\bm15\b", rf"\b15\s*min\b", rf"\b15\s*minute\b"],
                    "M30": [rf"\bm30\b", rf"\b30\s*min\b", rf"\b30\s*minute\b"],
                    "H1": [rf"\bh1\b", rf"\b1\s*hour\b", rf"\b1\s*h\b"],
                    "H4": [rf"\bh4\b", rf"\b4\s*hour\b", rf"\b4\s*h\b"],
                    "D1": [rf"\bd1\b", rf"\b1\s*day\b", rf"\b1\s*d\b"]
                }
                for tf, regexes in patterns.items():
                    for r_pat in regexes:
                        if re.search(r_pat, msg_lower):
                            period_counts[tf] += 1
                            break
                
                # Check sentiment
                has_pos = any(pos in msg_lower for pos in POSITIVE_KEYWORDS)
                has_neg = any(neg in msg_lower for neg in NEGATIVE_KEYWORDS)
                
                cleaned_msg = clean_comment(msg)
                if len(cleaned_msg) > 10:
                    if has_pos and len(positive_comments) < 5:
                        positive_comments.append(cleaned_msg)
                    elif has_neg and len(negative_comments) < 5:
                        negative_comments.append(cleaned_msg)
                        
        # Merge registry with extracted pairs and timeframes
        confirmed_symbols = parse_registry_pairs(meta.get("pairs", ""))
        confirmed_periods = parse_registry_periods(meta.get("timeframe", ""))
        
        # Decide threshold: if EA is mentioned heavily, require at least 2 mentions to avoid random noise
        threshold = 2 if mentions_count >= 10 else 1
        
        for sym, count in symbol_counts.items():
            if count >= threshold:
                confirmed_symbols.add(sym)
                
        for tf, count in period_counts.items():
            if count >= threshold:
                confirmed_periods.add(tf)
                
        if not confirmed_symbols:
            confirmed_symbols = {"EURUSD"}
        if not confirmed_periods:
            confirmed_periods = {"M15"}
            
        sorted_symbols = sorted(list(confirmed_symbols))
        period_order = {"M1": 1, "M5": 2, "M15": 3, "M30": 4, "H1": 5, "H4": 6, "D1": 7}
        sorted_periods = sorted(list(confirmed_periods), key=lambda x: period_order.get(x, 99))
        
        meta_pairs_str = ", ".join(sorted_symbols)
        meta_timeframe_str = ", ".join(sorted_periods)
        
        # Score-Aspekte zaehlen
        pos_count = len(positive_comments)
        neg_count = len(negative_comments)
        
        # Check if we have LLM insights for this EA
        strategy = meta["strategy"]
        risk = meta["risk"]
        description = meta["description"]
        timeframe = meta_timeframe_str
        pairs = meta_pairs_str
        
        insight = None
        if meta["name"] in ea_insights:
            insight = ea_insights[meta["name"]]
        else:
            for k, v in ea_insights.items():
                if k.lower() == meta["name"].lower():
                    insight = v
                    break
        
        if insight:
            strategy = insight.get("strategy", strategy)
            risk = insight.get("risk", risk)
            
            # Override timeframes if present
            tfs = insight.get("timeframes")
            if tfs:
                if isinstance(tfs, list):
                    timeframe = ", ".join(tfs)
                else:
                    timeframe = str(tfs)
            
            # Override pairs if present
            prs = insight.get("pairs")
            if prs:
                if isinstance(prs, list):
                    pairs = ", ".join(prs)
                else:
                    pairs = str(prs)
                    
            # Override description
            description = insight.get("description", description)
            
            # Append warnings if present
            warnings = insight.get("warnings")
            if warnings and warnings.strip() and warnings.strip().lower() not in ["none", "keine", "n/a", "no", "nein", "keine nennung"]:
                description += f"\n\n⚠️ **Risiken & Warnungen (LLM-Analyse):**\n{warnings}"

        # Punkteberechnung basierend auf dem finalen (ggf. LLM) Risiko
        if "scam" in risk.lower():
            score = 30
        else:
            score = 50 + (pos_count * 8) - (neg_count * 10)
            score = max(15, min(95, score))
            
        # Dynamisches Mapping von Dateien
        mapped_files = []
        for f in forex_files:
            f_lower = f.lower()
            for term in search_terms:
                # Verhindere Fehlzuordnungen bei sehr kurzen Begriffen
                if len(term) < 3:
                    continue
                if term in f_lower:
                    mapped_files.append(f)
                    break
                    
        # Entferne Dateiduplikate
        mapped_files = sorted(list(set(mapped_files)))
        
        robots_data.append({
            "id": robot_id,
            "name": meta["name"],
            "strategy": strategy,
            "risk": risk,
            "timeframe": timeframe,
            "pairs": pairs,
            "description": description,
            "mentions": mentions_count,
            "score": score,
            "files": mapped_files,
            "pos_comments": positive_comments,
            "neg_comments": negative_comments
        })
        print_progress_bar(idx + 1, total_robots, prefix='Fortschritt Analyse', suffix='analysiert', length=40)
        
    # Sortieren nach Mentions (Anzahl Postings ist das Ranking)
    robots_data.sort(key=lambda x: x["mentions"], reverse=True)
    
    # Speichere Daten in SQLite-Datenbank
    def save_to_sqlite(data):
        db_dir = WORKSPACE_DIR / "data"
        db_dir.mkdir(parents=True, exist_ok=True)
        db_path = db_dir / "telegram_scraper.db"
        
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = ON;")
        
        cursor.execute("DROP TABLE IF EXISTS robot_comments;")
        cursor.execute("DROP TABLE IF EXISTS robot_files;")
        cursor.execute("DROP TABLE IF EXISTS robots;")
        
        cursor.execute("""
        CREATE TABLE robots (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            strategy TEXT,
            risk TEXT,
            timeframe TEXT,
            pairs TEXT,
            description TEXT,
            mentions INTEGER,
            score INTEGER
        );
        """)
        
        cursor.execute("""
        CREATE TABLE robot_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            robot_id TEXT,
            filename TEXT,
            FOREIGN KEY (robot_id) REFERENCES robots(id) ON DELETE CASCADE
        );
        """)
        
        cursor.execute("""
        CREATE TABLE robot_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            robot_id TEXT,
            comment_text TEXT,
            is_negative INTEGER,
            FOREIGN KEY (robot_id) REFERENCES robots(id) ON DELETE CASCADE
        );
        """)
        
        for r in data:
            cursor.execute("""
            INSERT INTO robots (id, name, strategy, risk, timeframe, pairs, description, mentions, score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                r["id"],
                r["name"],
                r["strategy"],
                r["risk"],
                r["timeframe"],
                r["pairs"],
                r["description"],
                r["mentions"],
                r["score"]
            ))
            
            for f in r["files"]:
                cursor.execute("INSERT INTO robot_files (robot_id, filename) VALUES (?, ?);", (r["id"], f))
                
            for c in r["pos_comments"]:
                cursor.execute("INSERT INTO robot_comments (robot_id, comment_text, is_negative) VALUES (?, ?, 0);", (r["id"], c))
                
            for c in r["neg_comments"]:
                cursor.execute("INSERT INTO robot_comments (robot_id, comment_text, is_negative) VALUES (?, ?, 1);", (r["id"], c))
                
        conn.commit()
        conn.close()
        print(f"[+] Daten erfolgreich in SQLite-Datenbank importiert: {db_path}")

    try:
        save_to_sqlite(robots_data)
    except Exception as dberr:
        print(f"[-] Fehler beim Speichern in SQLite-Datenbank: {dberr}")
    
    # 4. Global Sentiment & Stats
    total_pos = sum(len(r["pos_comments"]) for r in robots_data)
    total_comments = sum(len(r["pos_comments"]) + len(r["neg_comments"]) for r in robots_data)
    global_sentiment_rate = round((total_pos / total_comments) * 100) if total_comments > 0 else 50
    
    # Schreibe stats.json
    stats_data = {
        "clustered_files": len(os.listdir(FOREX_FILES_DIR)) if FOREX_FILES_DIR.exists() else 0,
        "scanned_messages": len(messages),
        "identified_robots": len(robots_data),
        "global_sentiment_rate": global_sentiment_rate
    }
    
    stats_dir = WORKSPACE_DIR / "extracted_data"
    stats_dir.mkdir(parents=True, exist_ok=True)
    stats_path = stats_dir / "stats.json"
    stats_path.write_text(json.dumps(stats_data, indent=2), encoding="utf-8")
    print(f"[+] Statistiken geschrieben in: {stats_path}")
    print("[+] [Step 5/5] Analyse-Datenbank und Statistiken erfolgreich aktualisiert!")

if __name__ == "__main__":
    generate()
