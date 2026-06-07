import os
import re
import json
import time
import sys
import argparse
from pathlib import Path
from collections import defaultdict
import pydantic
from pydantic import BaseModel, Field
import requests

# Pfade definieren
WORKSPACE_DIR = Path(__file__).parent.parent.resolve()
FOREX_FILES_DIR = WORKSPACE_DIR / "extracted_data" / "forex_files"
CHUNKS_DIR = WORKSPACE_DIR / "extracted_data" / "chat_chunks"
INSIGHTS_FILE = WORKSPACE_DIR / "extracted_data" / "ea_insights.json"
CONFIG_FILE = WORKSPACE_DIR / "config.local.json"

# Importiere ROBOTS_REGISTRY aus generate_dashboard
try:
    import sys
    sys.path.append(str(WORKSPACE_DIR / "src"))
    from generate_dashboard import ROBOTS_REGISTRY
except ImportError:
    ROBOTS_REGISTRY = {}

class EAInsights(BaseModel):
    description: str = Field(description="Kurzbeschreibung des EA (2-3 Sätze in Deutsch, basierend auf den Community-Meinungen)")
    timeframes: list[str] = Field(description="Liste der empfohlenen Zeiteinheiten / Timeframes (z.B. M1, M5, M15, H1, H4, D1)")
    pairs: list[str] = Field(description="Liste der empfohlenen Currency Pairs / Währungspaare (z.B. EURUSD, GBPUSD, XAUUSD, USDJPY)")
    strategy: str = Field(description="Kurze Bezeichnung der Strategie (z.B. Grid / Martingale, Scalper, Trendfolger)")
    risk: str = Field(description="Risiko-Einschätzung (z.B. Low, Medium, High, Very High, Extreme)")
    warnings: str = Field(description="Kritikpunkte, Risiken oder Warnungen der Community bezüglich dieses EA")

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

def load_api_key_and_model():
    model = "meta-llama/llama-3.1-8b-instruct"
    key = None
    if CONFIG_FILE.exists():
        try:
            config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            if "openrouter_api_key" in config:
                key = config["openrouter_api_key"]
            if "openrouter_model" in config:
                model = config["openrouter_model"]
        except Exception as e:
            print(f"[!] Fehler beim Lesen von config.local.json: {e}")
            
    if not key:
        key = os.environ.get("OPENROUTER_API_KEY")
        
    return key, model

def extract_json_from_text(text):
    text = text.strip()
    
    # Try direct json load first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
        
    # Search for markdown code block ```json ... ```
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL | re.IGNORECASE)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
            
    # Search for first occurrences of { and last occurrence of }
    first_brace = text.find('{')
    last_brace = text.rfind('}')
    if first_brace != -1 and last_brace != -1:
        json_candidate = text[first_brace:last_brace + 1]
        try:
            return json.loads(json_candidate)
        except json.JSONDecodeError:
            pass
            
    raise ValueError("JSON konnte nicht aus dem Text extrahiert werden.")

def clean_comment(comment):
    pattern = r'^\[\d+\]\s*\|\s*\[[^\]]+\]\s*\|\s*[^:]+:\s*'
    cleaned = re.sub(pattern, '', comment)
    cleaned = re.sub(r'\[Angehängte Forex-Datei:[^\]]+\]', '', cleaned)
    return cleaned.strip()

class Tee:
    def __init__(self, original_stream, log_file_path):
        self.original_stream = original_stream
        self.log_file_path = log_file_path

    def write(self, message):
        if self.original_stream:
            self.original_stream.write(message)
            self.original_stream.flush()
        
        if message and message.strip():
            try:
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                lines = message.split("\n")
                with open(self.log_file_path, "a", encoding="utf-8") as f:
                    for line in lines:
                        if line.strip():
                            f.write(f"[{timestamp}] [LLM_ANALYSIS] {line}\n")
            except Exception:
                pass

    def flush(self):
        if self.original_stream:
            self.original_stream.flush()

def main():
    # Setup Tee for logging to log/telegram_scraper.log
    try:
        log_dir = WORKSPACE_DIR / "log"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file_path = log_dir / "telegram_scraper.log"
        sys.stdout = Tee(sys.stdout, log_file_path)
        sys.stderr = Tee(sys.stderr, log_file_path)
    except Exception as e:
        print(f"[!] Fehler beim Einrichten der Log-Datei: {e}")

    parser = argparse.ArgumentParser(description="OpenRouter LLM Extraction Pipeline")
    parser.add_argument("--limit", type=int, default=None, help="Maximale Anzahl an EAs, die bewertet werden sollen")
    args = parser.parse_args()

    print("==================================================")
    print("      OPENROUTER LLM EXTRACTION PIPELINE (FREE)   ")
    print("==================================================")
    
    # API-Key laden
    api_key, model_name = load_api_key_and_model()
    if not api_key:
        print("[!] OPENROUTER_API_KEY konnte nicht gefunden werden.")
        print("    Bitte trage den API-Key im Dashboard ein")
        print("    oder setze die Umgebungsvariable OPENROUTER_API_KEY.")
        return
    
    # 1. Chat-Chunks einlesen
    print("[*] Lese Chat-Chunks ein...")
    messages = []
    if CHUNKS_DIR.exists():
        chunk_files = list(CHUNKS_DIR.glob("chat_chunk_*.txt"))
        for chunk_file in chunk_files:
            try:
                content = chunk_file.read_text(encoding="utf-8")
                parts = content.split("----------------------------------------")
                for p in parts:
                    clean_p = p.strip()
                    if clean_p:
                        messages.append(clean_p)
            except Exception:
                pass
    print(f"  [+] {len(messages)} Chat-Nachrichten geladen.")

    # 2. Aktive EAs ermitteln
    print("[*] Analysiere aktive EAs aus Dateinamen...")
    forex_files = os.listdir(FOREX_FILES_DIR) if FOREX_FILES_DIR.exists() else []
    robot_keys = {}
    for f in forex_files:
        c_name = clean_name(f)
        if c_name:
            robot_keys[c_name.lower()] = c_name

    # Vorhandene Registry einpflegen
    active_registry = {}
    for k, v in ROBOTS_REGISTRY.items():
        active_registry[k] = v.copy()
        if "search_terms" not in active_registry[k]:
            active_registry[k]["search_terms"] = [k.lower().replace("_", " ")]

    unified_text = "\n".join(messages).lower()
    
    # EAs mit mindestens 5 Erwähnungen ermitteln
    active_eas = {}
    for key, display_name in robot_keys.items():
        mentions_count = unified_text.count(key)
        if mentions_count >= 5:
            active_eas[display_name] = {
                "search_terms": [key],
                "mentions": mentions_count
            }

    # Registry EAs hinzufügen
    for robot_id, meta in active_registry.items():
        name = meta["name"]
        if name not in active_eas:
            active_eas[name] = {
                "search_terms": [term.lower() for term in meta["search_terms"]],
                "mentions": unified_text.count(name.lower())
            }

    print(f"  [+] {len(active_eas)} aktive EAs für LLM-Extraktion identifiziert.")

    # 3. Postings pro EA sammeln (Staging)
    print("[*] Gruppiere Postings pro EA...")
    ea_postings = defaultdict(list)
    # Pre-lowercase messages once to avoid 89 million lower() calls (463 EAs * 192k messages)
    messages_with_lower = [(msg, msg.lower()) for msg in messages]
    
    for name, data in active_eas.items():
        search_terms = data["search_terms"]
        for msg, msg_lower in messages_with_lower:
            if any(term in msg_lower for term in search_terms):
                cleaned = clean_comment(msg)
                if len(cleaned) > 15:
                    ea_postings[name].append(cleaned)
                    
    # 4. Cache laden (Progress Resuming)
    insights_cache = {}
    if INSIGHTS_FILE.exists():
        try:
            insights_cache = json.loads(INSIGHTS_FILE.read_text(encoding="utf-8"))
            print(f"  [+] Cache geladen: {len(insights_cache)} EAs bereits extrahiert.")
        except Exception as e:
            print(f"[!] Fehler beim Laden von ea_insights.json: {e}")

    # 5. LLM Extraktions-Schleife
    print("[*] Starte Batch-Extraktion über OpenRouter...")
    
    # Sort active_eas by mentions descending
    sorted_active_eas = sorted(active_eas.items(), key=lambda item: item[1]["mentions"], reverse=True)
    
    # Filter for EAs that are not in the cache yet
    eas_to_process = [name for name, _ in sorted_active_eas if name not in insights_cache]
    
    start_index = len(insights_cache)
    total_all_eas = len(sorted_active_eas)
    
    if args.limit is not None:
        print(f"  [*] Begrenze Extraktion auf die {args.limit} am häufigsten diskutierten EAs.")
        eas_to_process = eas_to_process[:args.limit]
        
    total_eas = len(eas_to_process)
    
    if total_eas == 0:
        print("[+] Alle aktiven EAs sind bereits extrahiert. Fertig!")
        print("PROGRESS: 100")
        sys.stdout.flush()
        return

    print(f"  [+] {total_eas} EAs müssen noch verarbeitet werden.")
    
    for idx, ea_name in enumerate(eas_to_process):
        postings = ea_postings[ea_name]
        
        # Begrenze auf die letzten 35 Postings, um Token-Limits zu wahren und Fokus zu halten
        postings_to_send = postings[-35:]
        postings_text = "\n---\n".join(postings_to_send)
        
        print(f"[*] [{start_index + idx + 1}/{total_all_eas}] Analysiere {ea_name} ({len(postings)} Postings insgesamt)...")
        
        if len(postings_to_send) == 0:
            print(f"  [!] Keine ausreichenden Postings für {ea_name} vorhanden. Überspringe...")
            # Still update progress
            progress_pct = int((idx + 1) / total_eas * 100)
            print(f"PROGRESS: {progress_pct}")
            sys.stdout.flush()
            continue
            
        prompt = f"""Du bist ein erfahrener Handelsroboter-Experte (Forex EAs). 
Analysiere die folgenden echten Telegram-Chatlogs über den EA '{ea_name}'.
Die Community diskutiert darin über Setups, Einstellungen und Ergebnisse.
Antworte AUSSCHLIESSLICH mit einem einzigen, validen JSON-Objekt im folgenden Format:

{{
  "description": "Kurzbeschreibung des EA (2-3 Sätze in Deutsch, basierend auf den Community-Meinungen)",
  "timeframes": ["M1", "M15"],
  "pairs": ["EURUSD", "GBPUSD"],
  "strategy": "Strategie-Bezeichnung (z.B. Grid / Martingale)",
  "risk": "Risiko-Einschätzung (z.B. Low, Medium, High)",
  "warnings": "Kritikpunkte, Risiken oder Warnungen"
}}

Achtung bei Währungspaaren und Timeframes:
- Ziehe nur Währungspaare (z.B. EURUSD, GBPUSD, XAUUSD) und Zeiteinheiten (z.B. M1, M15, H1) heraus, die explizit in den Diskussionen für diesen EA empfohlen oder genutzt werden.
- Fasse das Feedback kurz in einer verständlichen deutschen Beschreibung zusammen.
- Falls keine Zeiteinheiten oder Paare genannt werden, lasse das Feld leer oder trage "Keine Nennung" ein.

[CHATLOGS START]
{postings_text}
[CHATLOGS ENDE]
"""
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/AntigravitySoftware/TelegramScraper",
                "X-Title": "Telegram Scraper Forex Robot Dashboard"
            }
            
            payload = {
                "model": model_name,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.2
            }
            
            # JSON format mode only for OpenAI models
            if "gpt" in model_name or "openai" in model_name:
                payload["response_format"] = {"type": "json_object"}
                
            res = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                data=json.dumps(payload),
                timeout=30
            )
            
            if res.status_code != 200:
                raise Exception(f"API Fehler {res.status_code}: {res.text}")
                
            res_data = res.json()
            choices = res_data.get("choices", [])
            if not choices:
                raise Exception(f"Leere Antwort von OpenRouter erhalten: {res_data}")
                
            response_text = choices[0].get("message", {}).get("content", "")
            
            # Robust JSON parsing
            result_dict = extract_json_from_text(response_text)
            
            # Cleanup schema fields to match Pydantic model
            cleaned_dict = {
                "description": result_dict.get("description", "Keine Beschreibung verfügbar."),
                "timeframes": result_dict.get("timeframes", result_dict.get("timeframe", [])),
                "pairs": result_dict.get("pairs", result_dict.get("pair", [])),
                "strategy": result_dict.get("strategy", "Community EA"),
                "risk": result_dict.get("risk", "Medium"),
                "warnings": result_dict.get("warnings", "")
            }
            
            if isinstance(cleaned_dict["timeframes"], str):
                cleaned_dict["timeframes"] = [t.strip() for t in cleaned_dict["timeframes"].split(",") if t.strip()]
            if isinstance(cleaned_dict["pairs"], str):
                cleaned_dict["pairs"] = [p.strip() for p in cleaned_dict["pairs"].split(",") if p.strip()]
                
            # Validate and format with Pydantic
            validated = EAInsights(**cleaned_dict)
            result_json = validated.model_dump() if hasattr(validated, "model_dump") else validated.dict()
            
            insights_cache[ea_name] = result_json
            
            # Sofort speichern (iteratives Caching)
            INSIGHTS_FILE.write_text(json.dumps(insights_cache, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"  [+] Rohe LLM-Antwort:\n{response_text}")
            print(f"  [+] Validierte Insights:\n{json.dumps(result_json, indent=2, ensure_ascii=False)}")
            
        except Exception as e:
            print(f"  [!] Fehler bei {ea_name}: {e}")
            
        # Report progress
        progress_pct = int((idx + 1) / total_eas * 100)
        print(f"PROGRESS: {progress_pct}")
        sys.stdout.flush()
            
        # Free Tier Rate Limiting: 15 RPM max -> 4.5 Sekunden Pause
        if idx < total_eas - 1:
            time.sleep(4.5)

    print("==================================================")
    print(f"[+] Extraktion abgeschlossen. Ergebnisse in: {INSIGHTS_FILE}")
    print("==================================================")

if __name__ == "__main__":
    main()
