import os
import shutil
import re
from pathlib import Path
from collections import defaultdict

# Pfade definieren
WORKSPACE_DIR = Path(__file__).parent.parent.resolve()
FOREX_FILES_DIR = WORKSPACE_DIR / "extracted_data" / "forex_files"
CHUNKS_DIR = WORKSPACE_DIR / "extracted_data" / "chat_chunks"
REPORT_DIR = WORKSPACE_DIR / "report"
ROBOTS_DIR = REPORT_DIR / "robots"

# Konfiguration der empfohlenen Roboter
ROBOTS_CONFIG = {
    "Quantum_Queen_Athena": {
        "files": [
            "Quantum Queen EA MT5 v3.52.ex5",
            "Quantum Athena_1.1_fix (1).ex5"
        ],
        "settings": [],
        "description": """# Quantum Queen & Quantum Athena

## 📝 Beschreibung
Ein trendfolgendes Grid-System, das primär auf Gold (XAUUSD) spezialisiert ist. Quantum Athena (QA) ist eine leichtere Version mit weniger eingebauten Strategien, während Quantum Queen (QQ) bis zu 10 Strategien anbietet.

## ⚙️ Einstellungen
* **Währungspaar:** Gold (XAUUSD)
* **Timeframe:** M15 (Standard)
* **Settings:** Standard-Einstellungen (Default) werden empfohlen.

## ⚠️ Risikomanagement & Kapitalanforderung
* **Kapital:** Mindestens **$500 für 0.01 Lot** (Standard-Risiko).
* **Risiko-Rating:** 🔴 Sehr Hoch (Grid-System)
* **Community-Tipp:** Idealerweise auf einem **Cent-Konto** (z. B. Vantage Cent MT5) betreiben. `C137` empfiehlt, feste Lotgrößen zu verwenden (z. B. 0.02 Lot für 5.000 USD Startkapital) und das Modell mindestens 2 Jahre rückwirkend zu backtesten. Führen Sie diesen EA immer parallel mit einem Drawdown-Schutz wie *RoyalGuard* aus.
"""
    },
    "Can_Cu_Bu_Sieng_Nang": {
        "files": [
            "Can Cu Bu Sieng Nang v2.9.3.ex5",
            "Can Cu Bu Sieng Nang v2.6.1.ex5",
            "CCBSN Black Dragon v1.1.ex5"
        ],
        "settings": [],
        "description": """# Can Cu Bu Sieng Nang (CCBSN)

## 📝 Beschreibung
Ein asiatisches Grid-System, das besonders für Währungspaare (Forex) geeignet ist. Es läuft bei vielen Community-Mitgliedern seit Monaten stabil, erfordert jedoch eine solide Kontogröße, um Drawdowns zu überstehen.

## ⚙️ Einstellungen
* **Währungspaare:** Hauptwährungspaare (Forex), z. B. EURUSD, USDJPY, GBPUSD
* **Timeframe:** M5 (Standard)
* **Settings:** Standard-Einstellungen (Default), müssen jedoch pro Währungspaar feinjustiert werden.

## ⚠️ Risikomanagement & Kapitalanforderung
* **Kapital:** Mindestens **150.000 Cent ($1.500 USD)** Guthaben auf einem Cent-Konto für ein sicheres und stressfreies Trading ("without tension").
* **Risiko-Rating:** 🟠 Hoch (Grid-System)
"""
    },
    "ForexCracked_AI": {
        "files": [
            "ForexCracked.com_AI_FREE.ex5"
        ],
        "settings": [],
        "description": """# ForexCracked.com AI (AI FREE)

## 📝 Beschreibung
Ein moderner EA, der technische Indikatoren (ADX & Alligator) als Pre-Filter nutzt. Sobald ein Trend erkannt wird, erstellt der EA drei Screenshots des Charts und sendet sie per WebRequest an ein konfiguriertes LLM (z. B. Claude, GPT, Gemini). Die KI entscheidet über den Einstieg, die Richtung sowie SL/TP.

## ⚙️ Einstellungen
1. **WebRequest-Freigabe:** In MetaTrader 5 unter *Tools -> Options -> Expert Advisors* müssen folgende URLs eingetragen werden:
   * `https://api.anthropic.com`
   * `https://api.openai.com`
   * `https://generativelanguage.googleapis.com`
   * `https://api.deepseek.com`
   * `https://api.x.ai`
2. **API-Key:** Sie müssen Ihren eigenen API-Schlüssel im EA-Eingabeparameter `InpAPIKey` eintragen.
3. **LLM-Provider:** In `InpProviderOverride` können Sie die KI wählen. Gemini (Free Key) funktioniert gut, DeepSeek unterstützt in dieser Version keine Vision-Bilder.
4. **Timeframe:** Standardmäßig M15.

## ⚠️ Risikomanagement & Kapitalanforderung
* **Kapital:** Flexibel (Standard-Konten oder Prop-Firm-Modus).
* **Risiko-Rating:** 🟢 Gering bis 🟠 Mittel (abhängig davon, ob optionales Martingale aktiviert ist).
* **Hinweis:** Kann im MT5-Tester nicht backgetestet werden, da WebRequests dort blockiert sind. Optimierung nur auf Demo-Konten möglich.
"""
    },
    "Forex_Fury": {
        "files": [
            "Forex Fury Updated MT5 EA(1).ex5",
            "Forex Fury V3 MT4.ex4"
        ],
        "settings": [],
        "description": """# Forex Fury (V3)

## 📝 Beschreibung
Ein zeitgesteuerter Ausbruchs-Scalper. Der Bot ist so programmiert, dass er nur während einer bestimmten Stunde am Tag handelt (in der Regel in ruhigen Marktphasen um 22:00 Uhr Brokerzeit), um das Risiko von Trendwenden zu minimieren. Er arbeitet mit verdeckten Stop-Loss und Take-Profit Levels.

## ⚙️ Einstellungen
* **Währungspaare:** Cross-JPY Paare (EURJPY, USDJPY, GBPJPY)
* **Timeframe:** M5
* **Wichtig:** Die Handelszeiten in den Input-Parametern müssen manuell an die Zeitzone des eigenen Brokers angepasst werden.

## ⚠️ Risikomanagement & Kapitalanforderung
* **Kapital:** Ab $200 auf Standard-Konten (oder Cent-Konten).
* **Risiko-Rating:** 🟠 Mittel (Verwendung von verdeckten SL/TPs reduziert das Risiko).
"""
    },
    "Gold_Pure_V1": {
        "files": [
            "Gold Pure V1.ex5"
        ],
        "settings": [
            "Gold Pure V1_1.set"
        ],
        "description": """# Gold Pure V1

## 📝 Beschreibung
Ein von der KI Gemini generierter EA für den Goldmarkt. Er wurde von der Community optimiert und erzielt in Tests gute Ergebnisse.

## ⚙️ Einstellungen
* **Währungspaar:** Gold (XAUUSD)
* **Timeframe:** M30 oder H1 (empfohlen von `C137`)
* **Settings:** Nutzen Sie die mitgelieferte Einstellungsdatei `Gold Pure V1_1.set`.
* **Optimierung von `C137`:** Trend-Filter in den Einstellungen deaktivieren (TREND_OFF). Stop-Loss (SL) auf über 200 Punkte und Take-Profit (TP) auf über 800 Punkte anheben, um die Profit-Faktor-Performance zu maximieren.

## ⚠️ Risikomanagement & Kapitalanforderung
* **Kapital:** Ab $500 aufwärts.
* **Risiko-Rating:** 🟠 Mittel (bessere Verlustabsicherung durch optimierten SL).
"""
    },
    "Scalping_Entry_M5": {
        "files": [
            "scalping entry m5.ex5",
            "scalping entry m5.mq5"
        ],
        "settings": [],
        "description": """# Scalping Entry M5 (Claude-built)

## 📝 Beschreibung
Ein von dem Nutzer `Irfan` mithilfe von Claude erstellter Scalping-EA. Der größte Vorteil ist, dass der **vollständige MQL5-Quellcode** (`.mq5`) vorliegt. Perfekt geeignet, um MQL5-Programmierung zu lernen oder eigene Optimierungen im MetaEditor vorzunehmen.

## ⚙️ Einstellungen
* **Währungspaare:** Hauptpaare (Forex)
* **Timeframe:** M5
* **Settings:** Standard-Einstellungen.

## ⚠️ Risikomanagement & Kapitalanforderung
* **Kapital:** Sehr gut geeignet für kleine Konten (**$100 bis $200**).
* **Risiko-Rating:** 🟢 Gering bis 🟠 Mittel (aufgrund kleiner Kontogrößen).
"""
    },
    "PropGuardian_Pro": {
        "files": [
            "PropGuardian Pro Fix.ex4",
            "PropGuardian Pro.ex4",
            "PropGuardianPro PART.ex4"
        ],
        "settings": [],
        "description": """# PropGuardian Pro

## 📝 Beschreibung
Ein EA, der speziell dafür entwickelt wurde, die Auszahlungs- und Verlustgrenzen bei Prop-Firm-Challenges einzuhalten und diese zu bestehen. Die enthaltenen Versionen sind freigeschaltete Fixes von Arthur Shony.

## ⚙️ Einstellungen
* **Währungspaar:** Gold (XAUUSD)
* **Timeframe:** H1
* **Settings:** Standard-Einstellungen (Default-SL liegt bei 2500 Punkten).

## ⚠️ Risikomanagement & Kapitalanforderung
* **Kapital:** Prop-Firm-Kontogrößen ($10k, $50k, $100k).
* **Risiko-Rating:** 🟠 Mittel (für Challenge-Regeln optimiert).
"""
    },
    "RoyalGamble_INDEX": {
        "files": [
            "RoyalGamble.INDEX.Trial.Version.JUNE.ex5"
        ],
        "settings": [],
        "description": """# RoyalGamble INDEX

## 📝 Beschreibung
Ein EA, der speziell für den Handel von Indizes optimiert ist. Er wird im Chat für Anlageklassen wie US30, US500 (S&P 500), GER40 (DAX) und USTECH (Nasdaq) diskutiert.

## ⚙️ Einstellungen
* **Timeframe:** H1 (1 Stunde)
* **Handelsinstrumente:** US30, US500, GER40, USTECH
* **Settings:** Es wird empfohlen, die integrierten Standard-Einstellungen zu verwenden.

## ⚠️ Risikomanagement & Kapitalanforderung
* **Risiko-Rating:** 🟠 Mittel (Index-Handel birgt durch Hebelwirkungen hohe Risiken, die Standard-Settings sind jedoch solide).
* **Hinweis:** Da es sich um eine Trial-Version für Juni handelt, sollte die Laufzeit und Funktionsfähigkeit auf Demo-Konten überwacht werden.
"""
    },
    "RapidWave": {
        "files": [
            "RapidWave-fix2.ex5"
        ],
        "settings": [],
        "description": """# RapidWave

## 📝 Beschreibung
Ein Ausbruchs-Roboter, der primär auf den Goldmarkt (XAUUSD) ausgelegt ist. Laut Community-Mitglied `Joel` benötigt er WebRequests, um voll funktionsfähig zu sein.

## ⚙️ Einstellungen
* **Währungspaar:** Gold (XAUUSD)
* **Timeframe:** H1 (1 Stunde)
* **Wichtig:** Aktivieren Sie WebRequests in MetaTrader 5 unter *Tools -> Options -> Expert Advisors* für die vom Entwickler benötigten URLs.

## ⚠️ Risikomanagement & Kapitalanforderung
* **Risiko-Rating:** 🟠 Mittel bis 🔴 Hoch (Gold-Ausbrüche können sehr volatil sein).
"""
    },
    "AI_Gen_XII": {
        "files": [
            "AI Gen XII v2.3 MT4 1421.ex4",
            "AI Gen XII MT4_2.71_fix.ex4",
            "AI Gen XII MT4_2.8_fix.ex4",
            "AI Gen XII MT4_2.9_fix.ex4",
            "AI Gen XII MT4_v3.0_fix.ex4"
        ],
        "settings": [
            "AI GEN XII v2.3 (Light Setting).set",
            "AI GEN XII v2.3 (Moderate Setting).set"
        ],
        "description": """# AI Gen XII

## 📝 Beschreibung
Ein hochentwickelter Forex-Handelsroboter (EA), der im Chat sehr intensiv diskutiert wird (einer der meistgenannten Bots). Er bietet ausgefeilte Strategien für den automatisierten Devisenhandel.

## ⚙️ Einstellungen
* **Plattform:** MetaTrader 4 (MT4)
* **Presets:** Nutzen Sie die mitgelieferten Einstellungsdateien für risikoarme (`Light Setting`) oder ausgewogene (`Moderate Setting`) Konfigurationen.

## ⚠️ Risikomanagement & Kapitalanforderung
* **Risiko-Rating:** 🟠 Mittel bis 🔴 Hoch (abhängig von den gewählten Einstellungen und Lotgrößen).
* **Community-Empfehlung:** Immer zuerst auf einem Demo-Konto mit dem `Light Setting` beginnen, um das Verhalten des Bots zu verstehen.
"""
    },
    "Waka_Waka_EA": {
        "files": [
            "Waka Waka EA V3.55 No DLL.ex4",
            "Waka Waka EA v4.29.ex4",
            "Waka Waka EA V4.37_fix-1400+.ex4",
            "Waka Waka EA V4.43_fix.ex4",
            "Waka Waka EA_4.59_fix amaloadmin.ex4"
        ],
        "settings": [
            "WakaWaka 4.37 working news filter.set"
        ],
        "description": """# Waka Waka EA

## 📝 Beschreibung
Waka Waka ist eines der bekanntesten und erfolgreichsten Grid-Systeme auf dem Devisenmarkt. Es handelt primär Währungskreuzungen (Cross-Pairs) und nutzt ausgefeilte Grid- und Martingale-Strategien mit einem integrierten News-Filter.

## ⚙️ Einstellungen
* **Timeframe:** M15 (Standard)
* **Währungspaare:** AUDCAD, AUDNZD, NZDCAD (Empfohlene Cross-Pairs)
* **Settings:** Nutzen Sie das Preset `WakaWaka 4.37 working news filter.set` für eine korrekte Funktionsweise des News-Filters.

## ⚠️ Risikomanagement & Kapitalanforderung
* **Kapital:** Benötigt eine solide Kontogröße, um Drawdowns in Grid-Phasen abzufedern (empfohlen: Cent-Konten oder mindestens $1.000+ USD bei Standard-Konten).
* **Risiko-Rating:** 🔴 Sehr Hoch (Martingale/Grid-System). Niemals ohne harten Drawdown-Schutz oder Drawdown-Limit betreiben.
"""
    },
    "FundedEA_Deluxe": {
        "files": [
            "FundedEA Deluxe.ex4"
        ],
        "settings": [],
        "description": """# FundedEA Deluxe

## 📝 Beschreibung
Ein EA, der speziell für Prop-Firm-Trading (Challenges) entwickelt wurde. Er zielt darauf ab, die strikten Daily Drawdown- und Profit-Vorgaben von Fremdkapitalanbietern zu erfüllen.

## ⚙️ Einstellungen
* **Plattform:** MetaTrader 4
* **Settings:** Nutzen Sie die vordefinierten Standardeinstellungen oder passen Sie diese an die spezifischen Max-Drawdown-Regeln Ihrer Prop-Firm an.

## ⚠️ Risikomanagement & Kapitalanforderung
* **Risiko-Rating:** 🟠 Mittel (aufgrund der eingebauten Verlustgrenzen, die das Konto vor der Liquidation schützen sollen).
"""
    },
    "Hedging_Mania": {
        "files": [
            "1EA Hedging Mania.ex5",
            "1EA Hedging Mania (1).ex5"
        ],
        "settings": [],
        "description": """# Hedging Mania

## 📝 Beschreibung
Ein asynchroner Hedging-EA für MetaTrader 5. Er versucht, Marktschwankungen durch gleichzeitiges Eröffnen von Kauf- und Verkaufsaufträgen (Hedge) und anschließendes schrittweises Schließen im Profit auszugleichen.

## ⚙️ Einstellungen
* **Plattform:** MetaTrader 5
* **Timeframe:** M5 oder M15 (Standard)

## ⚠️ Risikomanagement & Kapitalanforderung
* **Risiko-Rating:** 🔴 Sehr Hoch (Hedging-Systeme können bei starken, einseitigen Trendbewegungen ohne Korrekturen zu hohem Margin-Druck führen).
"""
    },
    "Boring_Pips": {
        "files": [
            "Boring Pips MT4 - No DLL.ex4",
            "Boring Pips MT4 fix.ex4",
            "Boring Pips MT4_4.1_fix.ex4",
            "Boring Pips MT4_4.3_fix.ex4",
            "Boring Pips MT4_nodll.ex4"
        ],
        "settings": [],
        "description": """# Boring Pips MT4

## 📝 Beschreibung
Ein bekannter, vollautomatischer Scalping-EA. Er nutzt erweiterte statistische Algorithmen und mathematische Modelle, um Ein- und Ausstiege zu timen. Trotz des Namens "Boring" handelt es sich um ein dynamisches und hochprofitables System, wenn es unter den richtigen Marktbedingungen läuft.

## ⚙️ Einstellungen
* **Plattform:** MetaTrader 4
* **Timeframe:** M1 oder M5 (Scalping)
* **Handelspaar:** EURUSD, GBPUSD

## ⚠️ Risikomanagement & Kapitalanforderung
* **Risiko-Rating:** 🟠 Mittel bis 🔴 Hoch (nutzt Grid-Elemente zur Verlustverwaltung).
"""
    },
    "HFT_Fast_M1_Gold_Scalper": {
        "files": [
            "HFT Fast M1 Gold Scalper V6 EA MT4 v6.2_1431+.ex4",
            "HFT FAST M1 GOLD SCALPER V8 EA -DEMO.ex4"
        ],
        "settings": [],
        "description": """# HFT Fast M1 Gold Scalper

## 📝 Beschreibung
Ein High-Frequency Trading (HFT) Scalper für den Goldmarkt (XAUUSD). Er zielt darauf ab, Kleinstbewegungen im Sekundenbereich auf dem M1-Timeframe mit sehr engen Stops und schnellen Teilverkäufen auszunutzen.

## ⚙️ Einstellungen
* **Plattform:** MetaTrader 4
* **Timeframe:** M1 (1 Minute)
* **Handelspaar:** Gold (XAUUSD)
* **Wichtig:** Benötigt zwingend eine extrem geringe Latenz (< 1-2 ms) zum Broker-Server via VPS, da Slippage sonst den gesamten Ertrag vernichtet.

## ⚠️ Risikomanagement & Kapitalanforderung
* **Risiko-Rating:** 🔴 Sehr Hoch (hohe Transaktionsfrequenz, empfindlich gegenüber Spreads und Latenzen).
"""
    },
    "Vigorous_EA": {
        "files": [
            "(PH) Vigorous 3.4_fix.ex4"
        ],
        "settings": [],
        "description": """# Vigorous EA (RFT)

## 📝 Beschreibung
Ein von der bekannten Firma *Responsible Forex Trading (RFT)* entwickelter Trendfolge-EA für das Währungspaar EURUSD. Das System analysiert den übergeordneten Markttrend auf höheren Zeiteinheiten und sucht nach kleinen Korrekturen (Price Dips) in Trendrichtung, um kurzfristige Positionen zu eröffnen.

## ⚙️ Einstellungen
* **Währungspaar:** EURUSD
* **Zeiteinheit:** M15 oder H1 (für die Trendbestimmung)
* **Settings:** Nutzen Sie die Standardeinstellungen.

## ⚠️ Risikomanagement & Kapitalanforderung
* **Community-Test:** Community-Mitglied `Phil` berichtet, dass der EA bei ihm seit längerem stabil und profitabel auf einem echten Live-Konto bei *Darwinex* läuft. RFT hat zudem verifizierte Live-Ergebnisse auf Myfxbook veröffentlicht.
* **Risiko-Rating:** 🟢 Gering bis 🟠 Mittel (solide Trendfolgestrategie, kein unbegrenztes Grid/Martingale).
"""
    },
    "WallStreet_Recovery_PRO": {
        "files": [
            "WallStreet Recovery PRO_fix.ex4",
            "WallStreet Recovery PRO_fix (1).ex4",
            "WallStreet Recovery PRO_fix_msg367755.ex4",
            "wallstreet.mq4",
            "WallStreetForexRobot_v3.6_noIntern.mq4",
            "WallStreetForexRobot_v3.6~.mq4",
            "WallStreetForexRobot_v4.5_nodll.mq4",
            "WallStreetForexRobot_v4.6_nodll.mq4",
            "WallStreetX.mq4"
        ],
        "settings": [],
        "description": """# WallStreet Recovery PRO & WallStreet Forex Robot

## 📝 Beschreibung
WallStreet Recovery PRO ist ein hochentwickeltes automatisiertes Handelssystem für die MT4-Plattform, das auf dem legendären und bewährten Kern des WallStreet Forex Robot aufbaut. 
Es kombiniert die zuverlässige Handelslogik von WallStreet mit dem "Advanced Recovery System" – einem intelligenten Deal-Management-System, das temporäre Verluste ohne gefährliches Martingale oder unkontrollierte Grid-Erweiterung durch mathematische Verlustabsicherung in Gewinne umwandelt.

## ⚙️ Einstellungen
* **Timeframe:** M15
* **Währungspaare:** EURUSD, GBPUSD, USDJPY, AUDUSD, USDCHF, USDCAD, NZDUSD
* **Settings:** Die Standard-Eigenschaften (Default) sind bereits für alle unterstützten Paare vollständig optimiert. Es werden keine externen Set-Dateien benötigt.

## ⚠️ Risikomanagement & Backtesting
* **Risiko-Rating:** 🟠 Mittel (Verwendung des intelligenten Recovery-Modus ist sicherer als reines Grid/Martingale, birgt aber bei extremen Trends dennoch Risiken).
* **Backtesting-Empfehlungen:** 
  * Schneller Backtest: M1-Daten + Eröffnungspreise.
  * Präziser Backtest: M15-Daten + Jeder Tick (Every Tick) für die beste Simulationsqualität.
"""
    },
    "ToTheMoon_NoPain": {
        "files": [
            "ToTheMoon 3.3 MT4 English.ex4",
            "ToTheMoon 3.3 MT4 English_msg260630.ex4",
            "ToTheMoon 3.3 MT4 English_msg260784.ex4",
            "ToTheMoon 3.5 MT4 English.ex4",
            "ToTheMoon 3.5 MT4 English_msg365210.ex4",
            "ToTheMoon 3.5 MT4 English_msg366472.ex4",
            "ToTheMoon 3.5 MT5 English (2).ex5",
            "ToTheMoon 3.5 MT5 English.ex5"
        ],
        "settings": [
            "ToTheMoon 3.5 MT5 English (2).set"
        ],
        "description": """# ToTheMoon (NoPain Signal)

## 📝 Beschreibung
ToTheMoon ist ein vollautomatischer Grid-Handelsroboter (Expert Advisor), der von Daniel Moraes Da Silva (MQL5: `tec_daniel`) entwickelt wurde und die Basis für das bekannte MQL5-Kopiersignal **"NoPain"** bildet.
Der EA nutzt eine intelligente Grid-Strategie mit automatischem Durchschnittspreis-Management (Smart Averaging). Bei Trendwenden schützt er das Konto durch ein integriertes Verlustmanagement (Smart Loss Management / Smart Stop Loss), das Verlustpositionen schrittweise (teilweise) schließt, um einen hohen Drawdown zu verhindern.

## ⚙️ Einstellungen
* **Währungspaar:** Hauptsächlich optimiert für Paare mit geringer Volatilität und Seitwärtsphasen, insbesondere **AUDCAD**. Kann auch im Multi-Symbol-Modus betrieben werden.
* **Timeframe:** In der Regel auf **H1** betrieben (manche Nutzer nutzen auch M15/M5).
* **Settings:** Der Entwickler bietet spezielle Presets (.set) an. Standardeinstellungen sollten primär auf Demo-Konten getestet werden.

## ⚠️ Risikomanagement & Kapitalanforderung
* **Risiko-Rating:** 🔴 Sehr Hoch (Grid-/Martingale-Verhalten). Obwohl das Smart-Loss-Management den Drawdown dämpft, besteht bei lang anhaltenden Einwegtrends das Risiko von erheblichen Verlusten.
* **Kapital:** Mindestens **$1.000 bis $2.000 USD** oder Betrieb auf einem **Cent-Konto** mit entsprechendem Risikopuffer.
"""
    }
}

def load_all_messages():
    messages = []
    if CHUNKS_DIR.exists():
        for chunk_file in CHUNKS_DIR.glob("chat_chunk_*.txt"):
            try:
                content = chunk_file.read_text(encoding="utf-8")
                parts = content.split("----------------------------------------")
                for p in parts:
                    clean_p = p.strip()
                    if clean_p:
                        messages.append(clean_p)
            except Exception:
                pass
    return messages

def clean_comment(comment):
    pattern = r'^\[\d+\]\s*\|\s*\[[^\]]+\]\s*\|\s*[^:]+:\s*'
    cleaned = re.sub(pattern, '', comment)
    cleaned = re.sub(r'\[Angehängte Forex-Datei:[^\]]+\]', '', cleaned)
    return cleaned.strip()

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

def analyze_chats():
    print("[*] Lese Chat-Chunks für statistische Kurzübersicht...")
    scam_count = 0
    warning_count = 0
    profit_count = 0
    
    if CHUNKS_DIR.exists():
        for chunk_file in CHUNKS_DIR.glob("chat_chunk_*.txt"):
            try:
                content = chunk_file.read_text(encoding="utf-8")
                scam_count += len(re.findall(r"scam", content, re.IGNORECASE))
                warning_count += len(re.findall(r"warning|blow|loss", content, re.IGNORECASE))
                profit_count += len(re.findall(r"profit|win|doubled", content, re.IGNORECASE))
            except Exception as e:
                print(f"  [!] Fehler beim Lesen von {chunk_file.name}: {e}")
                
    print(f"  [+] Statistik aus Chat-Dateien: {scam_count}x 'Scam', {warning_count}x 'Warnungen', {profit_count}x 'Gewinne/Wins'")

def organize_robots():
    print("[*] Organisiere empfohlene Roboter...")
    ROBOTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. Zuerst die statisch konfigurierten Premium-Roboter organisieren
    organized_keys = set()
    for robot_name, config in ROBOTS_CONFIG.items():
        organized_keys.add(robot_name.lower())
        robot_folder = ROBOTS_DIR / robot_name
        robot_folder.mkdir(exist_ok=True)
        
        # EA-Dateien kopieren
        for filename in config["files"]:
            src_file = FOREX_FILES_DIR / filename
            if src_file.exists():
                shutil.copy2(src_file, robot_folder / filename)
                
        # Settings kopieren
        if config["settings"]:
            for set_name in config["settings"]:
                src_set = FOREX_FILES_DIR / set_name
                if src_set.exists():
                    shutil.copy2(src_set, robot_folder / set_name)
        else:
            with open(robot_folder / "settings_info.txt", "w", encoding="utf-8") as f:
                f.write("Dieser Roboter verwendet standardmäßig seine integrierten Default-Einstellungen.\nEs sind keine externen .set-Dateien erforderlich.\n")
                
        # Beschreibung schreiben
        with open(robot_folder / "beschreibung.md", "w", encoding="utf-8") as f:
            f.write(config["description"])
            
    print(f"  [+] {len(ROBOTS_CONFIG)} konfigurierte Premium-Roboter organisiert.")
    
    # 2. Dynamisch nach weiteren Robotern mit Chat-Erwähnungen scannen
    print("[*] Scanne nach weiteren vielbesprochenen EAs aus der Dateiliste...")
    if not FOREX_FILES_DIR.exists():
        return
        
    robot_files = defaultdict(list)
    for f in os.listdir(FOREX_FILES_DIR):
        c_name = clean_name(f)
        if c_name:
            key = c_name.lower()
            robot_files[key].append(f)
            
    messages = load_all_messages()
    
    dynamic_count = 0
    for key, files in robot_files.items():
        # Verhindere Überschreiben von Premium-Robotern
        folder_name = key.replace(" ", "_").title()
        if folder_name.lower() in organized_keys or key in organized_keys:
            continue
            
        # Zähle Erwähnungen und hole Beispiel-Kommentare
        mentions_count = 0
        matching_messages = []
        for msg in messages:
            if key in msg.lower():
                mentions_count += 1
                cleaned_msg = clean_comment(msg)
                if len(cleaned_msg) > 10 and len(matching_messages) < 8:
                    matching_messages.append(cleaned_msg)
                    
        # Wenn im Chat mindestens 5-mal erwähnt
        if mentions_count >= 5:
            dynamic_count += 1
            robot_folder = ROBOTS_DIR / folder_name
            robot_folder.mkdir(exist_ok=True)
            
            # Zugehörige Dateien kopieren
            for f in files:
                shutil.copy2(FOREX_FILES_DIR / f, robot_folder / f)
                
            # Generiere automatische Beschreibung
            desc = f"# {folder_name} (Automatisch extrahiert)\n\n"
            desc += "## 📝 Beschreibung\n"
            desc += f"Dieser Forex-Roboter wurde automatisch aus den Chat-Nachrichten und Dateianhängen extrahiert, da er in der Community aktiv diskutiert wird.\n\n"
            desc += "## 📊 Statistiken\n"
            desc += f"* **Erwähnungen im Chat:** {mentions_count} Mal\n"
            desc += f"* **Gefundene Versionen/Dateien:** {len(files)} Datei(en)\n\n"
            
            desc += "## 📁 Zugehörige Dateien im Ordner\n"
            for f in files:
                desc += f"* `{f}`\n"
            desc += "\n"
            
            if matching_messages:
                desc += "## 💬 Community-Kommentare (Was die User schreiben)\n"
                for m in matching_messages:
                    desc += f"> *\"{m}\"*\n\n"
            else:
                desc += "## 💬 Community-Kommentare\nKeine spezifischen Zitate extrahiert.\n"
                
            with open(robot_folder / "beschreibung.md", "w", encoding="utf-8") as f_out:
                f_out.write(desc)
                
    print(f"  [+] {dynamic_count} weitere vielbesprochene Roboter dynamisch geclustert und organisiert.")
    print(f"[+] Insgesamt {len(ROBOTS_CONFIG) + dynamic_count} Roboter-Verzeichnisse unter {ROBOTS_DIR} erfolgreich aktualisiert!")

def main():
    print("=== START ANALYSE & ORGANISATIONS-SUBROUTINE ===")
    analyze_chats()
    organize_robots()
    print("=== ANLYSE-SUBROUTINE ERFOLGREICH BEENDET ===")

if __name__ == "__main__":
    main()
