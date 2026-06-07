import os
import re
import sys
import json
import time
import threading
import subprocess
import webbrowser
from pathlib import Path
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

PORT = 8000
WORKSPACE_DIR = Path(__file__).parent.parent.resolve()

# Legacy state to track report generation progress (backwards compatibility)
processing_state = {
    "running": False,
    "progress": 0,
    "status": "Bereit",
    "error": None
}

# New Pipeline state for Process Automation Workflow
pipeline_state = {
    "running": False,
    "current_step_index": -1,
    "steps": [
        {
            "id": "extraction",
            "name": "1. Telegram-Extraktion",
            "description": "Extrahiert Forex-Dateien und teilt Chats in Chunks",
            "script": "src/telegram_extractor.py",
            "status": "pending",  # pending, running, completed, failed
            "progress": 0
        },
        {
            "id": "analysis",
            "name": "2. EA-Details Analyse (LLM)",
            "description": "Analysiert Postings auf Timeframe, Paare und Sentiment mit Gemini 1.5 Flash",
            "script": "src/extract_ea_details_llm.py",
            "status": "pending",
            "progress": 0
        },
        {
            "id": "dashboard_gen",
            "name": "3. Dashboard-Update",
            "description": "Aktualisiert die HTML-Dashboard-Statistiken",
            "script": "src/generate_dashboard.py",
            "status": "pending",
            "progress": 0
        },
        {
            "id": "backtest_config",
            "name": "4. Backtest-Konfiguration",
            "description": "Qualifiziert EAs und erzeugt batch_config.json",
            "script": "src/run_batch_backtests.py",
            "args": ["--dry-run"],
            "status": "pending",
            "progress": 0
        },
        {
            "id": "backtest_run",
            "name": "5. Backtest-Lauf (MT5)",
            "description": "Führt EAs im Strategy Tester über Java-Backtester aus",
            "script": "src/run_batch_backtests.py",
            "status": "pending",
            "progress": 0
        },
        {
            "id": "backtest_results",
            "name": "6. Ergebnis-Dashboard",
            "description": "Erzeugt die Übersicht der Backtest-Ergebnisse",
            "script": "src/generate_backtest_dashboard.py",
            "status": "pending",
            "progress": 0
        }
    ]
}

pipeline_logs = []
pipeline_lock = threading.Lock()

class DashboardRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Serve files relative to workspace directory
        super().__init__(*args, directory=str(WORKSPACE_DIR), **kwargs)

    def do_GET(self):
        # API Routes
        if self.path == "/api/generate-report":
            self.handle_generate_report()
        elif self.path == "/api/progress":
            self.handle_progress()
        elif self.path.startswith("/api/pipeline/state"):
            self.handle_pipeline_state()
        elif self.path.startswith("/api/pipeline/run"):
            self.handle_pipeline_run()
        elif self.path.startswith("/api/pipeline/logs"):
            self.handle_pipeline_logs()
        elif self.path.startswith("/api/pipeline/reset-cache"):
            self.handle_pipeline_reset_cache()
        elif self.path.startswith("/api/pipeline/reset"):
            self.handle_pipeline_reset()
        elif self.path.startswith("/api/config/save"):
            self.handle_config_save()
        elif self.path.startswith("/api/config/get"):
            self.handle_config_get()
        elif self.path.startswith("/api/config/test-llm"):
            self.handle_config_test_llm()
        elif self.path.startswith("/api/robots"):
            self.handle_robots()
        elif self.path.startswith("/api/stats"):
            self.handle_stats()
        elif self.path.startswith("/api/backtest/run"):
            self.handle_backtest_run()
        else:
            # Fallback to serving static files
            super().do_GET()

    def handle_generate_report(self):
        global processing_state
        if processing_state["running"]:
            self.send_json_response({"status": "already_running", "progress": processing_state["progress"]})
            return

        # Start the generation process in a background thread
        threading.Thread(target=run_generation_process).start()
        self.send_json_response({"status": "started"})

    def handle_progress(self):
        global processing_state
        self.send_json_response(processing_state)

    def handle_pipeline_state(self):
        global pipeline_state
        import copy
        with pipeline_lock:
            state_copy = copy.deepcopy(pipeline_state)
        self.send_json_response(state_copy)

    def handle_pipeline_run(self):
        global pipeline_state
        is_running = False
        with pipeline_lock:
            if pipeline_state["running"]:
                is_running = True
        
        if is_running:
            self.send_json_response({"status": "already_running"})
            return
        
        parsed_url = urlparse(self.path)
        params = parse_qs(parsed_url.query)
        step_id = params.get("step", ["all"])[0]
        limit = params.get("limit", [None])[0]
        
        # Start the pipeline execution in a background thread
        threading.Thread(target=run_pipeline_thread, args=(step_id, limit)).start()
        self.send_json_response({"status": "started", "step": step_id})

    def handle_pipeline_logs(self):
        global pipeline_logs
        parsed_url = urlparse(self.path)
        params = parse_qs(parsed_url.query)
        try:
            offset = int(params.get("offset", [0])[0])
        except (ValueError, TypeError):
            offset = 0
            
        with pipeline_lock:
            current_len = len(pipeline_logs)
            logs_slice = list(pipeline_logs[offset:])
            
        self.send_json_response({
            "offset": current_len,
            "logs": logs_slice
        })

    def handle_pipeline_reset(self):
        global pipeline_state, pipeline_logs
        is_running = False
        with pipeline_lock:
            if pipeline_state["running"]:
                is_running = True
            else:
                pipeline_logs.clear()
                pipeline_logs.append(f"[{time.strftime('%H:%M:%S')}] [SYSTEM] Pipeline-Status zurückgesetzt.")
                pipeline_state["current_step_index"] = -1
                for step in pipeline_state["steps"]:
                    step["status"] = "pending"
                    step["progress"] = 0
                
        if is_running:
            self.send_json_response({"status": "error", "message": "Pipeline läuft gerade"})
        else:
            self.send_json_response({"status": "reset"})

    def handle_pipeline_reset_cache(self):
        insights_path = WORKSPACE_DIR / "extracted_data" / "ea_insights.json"
        try:
            insights_path.write_text("{}", encoding="utf-8")
            
            # Run generate_dashboard.py asynchronously to clear DB values from front-end
            import sys
            py_executable = sys.executable or "python"
            subprocess.Popen([py_executable, "src/generate_dashboard.py"], cwd=str(WORKSPACE_DIR))
            
            self.send_json_response({"status": "success", "message": "Analyse-Cache geleert und Dashboard-Update gestartet."})
        except Exception as e:
            self.send_json_response({"status": "error", "message": str(e)})

    def handle_config_save(self):
        parsed_url = urlparse(self.path)
        params = parse_qs(parsed_url.query)
        key = params.get("key", [""])[0].strip()
        model = params.get("model", ["meta-llama/llama-3.1-8b-instruct"])[0].strip()
        
        config_path = WORKSPACE_DIR / "config.local.json"
        config = {}
        if config_path.exists():
            try:
                config = json.loads(config_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        
        if key:
            config["openrouter_api_key"] = key
        config["openrouter_model"] = model
        
        try:
            config_path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
            self.send_json_response({"status": "success"})
        except Exception as e:
            self.send_json_response({"status": "error", "message": str(e)})
 
    def handle_config_get(self):
        config_path = WORKSPACE_DIR / "config.local.json"
        has_key = False
        masked_key = ""
        model = "meta-llama/llama-3.1-8b-instruct"
        
        # Check environment variable first
        env_key = os.environ.get("OPENROUTER_API_KEY")
        if env_key:
            has_key = True
            masked_key = env_key[:8] + "..." + env_key[-4:] if len(env_key) > 12 else "Aktiv (Umgebungsvariable)"
            
        if config_path.exists():
            try:
                config = json.loads(config_path.read_text(encoding="utf-8"))
                key = config.get("openrouter_api_key")
                if key:
                    has_key = True
                    masked_key = key[:8] + "..." + key[-4:] if len(key) > 12 else "Aktiv (config.local.json)"
                model = config.get("openrouter_model", model)
            except Exception:
                pass
                
        self.send_json_response({"has_key": has_key, "masked_key": masked_key, "model": model})

    def handle_config_test_llm(self):
        import requests
        config_path = WORKSPACE_DIR / "config.local.json"
        key = None
        model = "meta-llama/llama-3.1-8b-instruct"
        
        # Load key and model from env or config.local.json
        env_key = os.environ.get("OPENROUTER_API_KEY")
        if env_key:
            key = env_key
            
        if config_path.exists():
            try:
                config = json.loads(config_path.read_text(encoding="utf-8"))
                if config.get("openrouter_api_key"):
                    key = config["openrouter_api_key"]
                if config.get("openrouter_model"):
                    model = config["openrouter_model"]
            except Exception:
                pass
                
        if not key:
            self.send_json_response({"status": "error", "message": "API-Key nicht konfiguriert."})
            return
            
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/AntigravitySoftware/TelegramScraper",
            "X-Title": "Telegram Scraper Forex Robot Dashboard"
        }
        
        payload = {
            "model": model,
            "messages": [
                {"role": "user", "content": "Antworte kurz mit 'Verbindung erfolgreich!'."}
            ],
            "temperature": 0.2
        }
        
        try:
            res = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                data=json.dumps(payload),
                timeout=15
            )
            
            if res.status_code == 200:
                res_data = res.json()
                choices = res_data.get("choices", [])
                if choices:
                    response_text = choices[0].get("message", {}).get("content", "").strip()
                    self.send_json_response({"status": "success", "response": response_text})
                else:
                    self.send_json_response({"status": "error", "message": f"Keine Antwort vom Modell erhalten: {res.text}"})
            else:
                self.send_json_response({"status": "error", "message": f"API-Fehler {res.status_code}: {res.text}"})
        except Exception as e:
            self.send_json_response({"status": "error", "message": f"Netzwerkfehler: {str(e)}"})

    def handle_backtest_run(self):
        parsed_url = urlparse(self.path)
        params = parse_qs(parsed_url.query)
        
        expert = params.get("expert", [""])[0].strip()
        platform = params.get("platform", ["MT5"])[0].strip()
        symbol = params.get("symbol", ["EURUSD"])[0].strip()
        period = params.get("period", ["M15"])[0].strip()
        from_date = params.get("from", ["2025-01-01"])[0].strip()
        to_date = params.get("to", ["2026-06-01"])[0].strip()
        model = params.get("model", ["1"])[0].strip()
        deposit = params.get("deposit", ["10000"])[0].strip()
        leverage = params.get("leverage", ["1:100"])[0].strip()
        keep_open = params.get("keep_open", ["false"])[0].strip().lower() == "true"
        
        if not expert:
            self.send_json_response({"status": "error", "message": "Expert-Name fehlt."})
            return
            
        py_executable = sys.executable or "python"
        cmd = [
            py_executable, 
            "src/run_single_backtest.py",
            "--expert", expert,
            "--platform", platform,
            "--symbol", symbol,
            "--period", period,
            "--from-date", from_date,
            "--to-date", to_date,
            "--model", model,
            "--deposit", deposit,
            "--leverage", leverage
        ]
        if keep_open:
            cmd.append("--keep-open")
        
        try:
            # Execute run_single_backtest.py
            p = subprocess.run(
                cmd,
                cwd=str(WORKSPACE_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=180
            )
            
            # Re-generate the backtest results dashboard HTML
            subprocess.run([py_executable, "src/generate_backtest_dashboard.py"], cwd=str(WORKSPACE_DIR))
            
            if p.returncode == 0:
                self.send_json_response({
                    "status": "success",
                    "output": p.stdout
                })
            else:
                self.send_json_response({
                    "status": "error",
                    "message": f"Backtest fehlgeschlagen (Fehlercode {p.returncode})",
                    "output": p.stdout
                })
        except subprocess.TimeoutExpired:
            self.send_json_response({
                "status": "error",
                "message": "Timeout: Der Backtest hat länger als 3 Minuten gedauert."
            })
        except Exception as e:
            self.send_json_response({
                "status": "error",
                "message": f"Fehler bei Backtest-Ausführung: {str(e)}"
            })

    def send_json_response(self, data):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def handle_stats(self):
        stats_path = WORKSPACE_DIR / "extracted_data" / "stats.json"
        stats = {
            "clustered_files": 0,
            "scanned_messages": 0,
            "identified_robots": 0,
            "global_sentiment_rate": 50
        }
        if stats_path.exists():
            try:
                stats = json.loads(stats_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        
        # Add LLM insights count dynamically
        insights_path = WORKSPACE_DIR / "extracted_data" / "ea_insights.json"
        insights_count = 0
        if insights_path.exists():
            try:
                insights_count = len(json.loads(insights_path.read_text(encoding="utf-8")))
            except Exception:
                pass
        stats["insights_count"] = insights_count
        
        self.send_json_response(stats)

    def handle_robots(self):
        parsed_url = urlparse(self.path)
        params = parse_qs(parsed_url.query)
        
        # Parse pagination parameters
        try:
            page = int(params.get("page", [1])[0])
        except (ValueError, TypeError):
            page = 1
            
        try:
            page_size = int(params.get("pageSize", [20])[0])
        except (ValueError, TypeError):
            page_size = 20
            
        search = params.get("search", [""])[0].strip()
        cat_filter = params.get("filter", ["all"])[0].strip()
        sort_col = params.get("sort", ["rank"])[0].strip()
        sort_dir = params.get("direction", ["desc"])[0].strip().upper()
        if sort_dir not in ["ASC", "DESC"]:
            sort_dir = "DESC"
            
        db_path = WORKSPACE_DIR / "data" / "telegram_scraper.db"
        if not db_path.exists():
            self.send_json_response({
                "robots": [],
                "total": 0,
                "page": page,
                "pageSize": page_size,
                "totalPages": 0,
                "db_missing": True
            })
            return
            
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Build query
        where_clauses = []
        query_args = []
        
        # 1. Category filter
        if cat_filter == "mt5":
            where_clauses.append("EXISTS (SELECT 1 FROM robot_files rf WHERE rf.robot_id = robots.id AND (rf.filename LIKE '%.ex5' OR rf.filename LIKE '%.mq5'))")
        elif cat_filter == "mt4":
            where_clauses.append("EXISTS (SELECT 1 FROM robot_files rf WHERE rf.robot_id = robots.id AND (rf.filename LIKE '%.ex4' OR rf.filename LIKE '%.mq4'))")
        elif cat_filter == "grid":
            where_clauses.append("(robots.strategy LIKE ? OR robots.strategy LIKE ?)")
            query_args.extend(["%grid%", "%martingale%"])
        elif cat_filter == "scalper":
            where_clauses.append("robots.strategy LIKE ?")
            query_args.append("%scalp%")
        elif cat_filter == "ai":
            where_clauses.append("(robots.strategy LIKE ? OR robots.strategy LIKE ?)")
            query_args.extend(["%ai%", "%ki%"])
        elif cat_filter == "scam":
            where_clauses.append("robots.risk LIKE ?")
            query_args.append("%scam%")
            
        # 2. Search term
        if search:
            where_clauses.append("(robots.name LIKE ? OR robots.strategy LIKE ? OR robots.pairs LIKE ?)")
            search_val = f"%{search}%"
            query_args.extend([search_val, search_val, search_val])
            
        # Combine WHERE clauses
        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)
            
        # Count total
        count_sql = f"SELECT COUNT(*) FROM robots {where_sql}"
        cursor.execute(count_sql, query_args)
        total_records = cursor.fetchone()[0]
        
        # 3. Order By
        # Map sort columns
        sort_map = {
            "name": "robots.name",
            "mentions": "robots.mentions",
            "score": "robots.score",
            "strategy": "robots.strategy",
            "risk": "robots.risk",
            "files": "(SELECT COUNT(*) FROM robot_files rf WHERE rf.robot_id = robots.id)"
        }
        
        order_col = sort_map.get(sort_col, "robots.mentions")
        order_sql = f"ORDER BY {order_col} {sort_dir}"
        
        # If order_col is not mentions, sub-order by mentions DESC to keep ranking clean
        if order_col != "robots.mentions":
            order_sql += ", robots.mentions DESC"
            
        # 4. Limit and Offset
        offset = (page - 1) * page_size
        
        # Fetch robots
        fetch_sql = f"""
        SELECT id, name, strategy, risk, timeframe, pairs, description, mentions, score
        FROM robots
        {where_sql}
        {order_sql}
        LIMIT ? OFFSET ?
        """
        
        cursor.execute(fetch_sql, query_args + [page_size, offset])
        robots_rows = cursor.fetchall()
        
        robots_list = []
        for row in robots_rows:
            r_id, name, strategy, risk, timeframe, pairs, description, mentions, score = row
            
            # Fetch files
            cursor.execute("SELECT filename FROM robot_files WHERE robot_id = ?", (r_id,))
            files = [f[0] for f in cursor.fetchall()]
            
            # Fetch positive comments
            cursor.execute("SELECT comment_text FROM robot_comments WHERE robot_id = ? AND is_negative = 0", (r_id,))
            pos_comments = [c[0] for c in cursor.fetchall()]
            
            # Fetch negative comments
            cursor.execute("SELECT comment_text FROM robot_comments WHERE robot_id = ? AND is_negative = 1", (r_id,))
            neg_comments = [c[0] for c in cursor.fetchall()]
            
            robots_list.append({
                "id": r_id,
                "name": name,
                "strategy": strategy,
                "risk": risk,
                "timeframe": timeframe,
                "pairs": pairs,
                "description": description,
                "mentions": mentions,
                "score": score,
                "files": files,
                "pos_comments": pos_comments,
                "neg_comments": neg_comments
            })
            
        conn.close()
        
        total_pages = (total_records + page_size - 1) // page_size if total_records > 0 else 0
        
        self.send_json_response({
            "robots": robots_list,
            "total": total_records,
            "page": page,
            "pageSize": page_size,
            "totalPages": total_pages
        })

def run_pipeline_thread(step_id, limit=None):
    global pipeline_state, pipeline_logs
    
    with pipeline_lock:
        if pipeline_state["running"]:
            return
        pipeline_state["running"] = True
        
    try:
        steps = pipeline_state["steps"]
        
        # Determine step index or indices to execute
        if step_id == "all":
            # Reset all step statuses first
            with pipeline_lock:
                pipeline_logs.append(f"[{time.strftime('%H:%M:%S')}] [SYSTEM] Starte gesamten automatischen Workflow...")
                for s in steps:
                    s["status"] = "pending"
                    s["progress"] = 0
            indices_to_run = list(range(len(steps)))
        else:
            # Find specific step
            idx = -1
            for i, s in enumerate(steps):
                if s["id"] == step_id:
                    idx = i
                    break
            if idx == -1:
                with pipeline_lock:
                    pipeline_logs.append(f"[{time.strftime('%H:%M:%S')}] [ERROR] Schritt '{step_id}' nicht gefunden.")
                return
            with pipeline_lock:
                steps[idx]["status"] = "pending"
                steps[idx]["progress"] = 0
                pipeline_logs.append(f"[{time.strftime('%H:%M:%S')}] [SYSTEM] Starte Schritt: {steps[idx]['name']}...")
            indices_to_run = [idx]
            
        for step_idx in indices_to_run:
            step = steps[step_idx]
            with pipeline_lock:
                pipeline_state["current_step_index"] = step_idx
                step["status"] = "running"
                step["progress"] = 10
                
            # Check for result.json fallback on extraction
            if step["id"] == "extraction":
                result_json_path = WORKSPACE_DIR / "result.json"
                if not result_json_path.exists():
                    with pipeline_lock:
                        pipeline_logs.append(f"[{time.strftime('%H:%M:%S')}] [SYSTEM] result.json nicht im Hauptordner gefunden.")
                        pipeline_logs.append(f"[{time.strftime('%H:%M:%S')}] [SYSTEM] Da bereits extrahierte Daten in 'extracted_data' existieren, wird dieser Schritt übersprungen.")
                        step["status"] = "completed"
                        step["progress"] = 100
                    continue
            
            # Execute step subprocess
            py_executable = sys.executable or "python"
            script_path = step["script"]
            args = list(step.get("args", []))
            
            # If executing analysis step, append limit
            if step["id"] == "analysis" and limit:
                try:
                    limit_int = int(limit)
                    args += ["--limit", str(limit_int)]
                except ValueError:
                    pass
            
            cmd = [py_executable, script_path] + args
            
            with pipeline_lock:
                pipeline_logs.append(f"[{time.strftime('%H:%M:%S')}] [SYSTEM] Führe aus: {' '.join(cmd)}")
                
            try:
                # Redirect stderr to stdout to catch all console logs
                p = subprocess.Popen(
                    cmd,
                    cwd=str(WORKSPACE_DIR),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    encoding="utf-8",
                    errors="replace"
                )
                
                while True:
                    line = p.stdout.readline()
                    if not line:
                        break
                    line_str = line.rstrip()
                    if line_str:
                        with pipeline_lock:
                            timestamp = time.strftime('%H:%M:%S')
                            # Identify error outputs or warnings to add prefix formatting if needed
                            prefix = ""
                            if "[!]" in line_str or "error" in line_str.lower() or "fehler" in line_str.lower():
                                prefix = "[ERROR] " if not line_str.startswith("[ERROR]") and not line_str.startswith("[!]") else ""
                            elif "[+]" in line_str or "success" in line_str.lower() or "erfolgreich" in line_str.lower():
                                prefix = "[SUCCESS] " if not line_str.startswith("[SUCCESS]") and not line_str.startswith("[+]") else ""
                            
                            formatted_line = f"[{timestamp}] {prefix}{line_str}"
                            pipeline_logs.append(formatted_line)
                            
                            # Keep only last 1000 lines
                            if len(pipeline_logs) > 1000:
                                pipeline_logs.pop(0)
                                
                            # Parse progress percentage from output
                            progress_match = re.search(r'(?:PROGRESS:\s*|\[PROGRESS\]\s*)(\d+)', line_str, re.IGNORECASE)
                            if progress_match:
                                progress_val = int(progress_match.group(1))
                                step["progress"] = min(100, max(0, progress_val))
                            elif step["id"] != "analysis" and step["progress"] < 95:
                                # Only fake-increment for steps other than LLM analysis to prevent erratic jumps/resets
                                step["progress"] += 1
                                
                p.wait()
                
                with pipeline_lock:
                    if p.returncode == 0:
                        step["status"] = "completed"
                        step["progress"] = 100
                        pipeline_logs.append(f"[{time.strftime('%H:%M:%S')}] [SYSTEM] Schritt '{step['name']}' erfolgreich beendet.")
                    else:
                        step["status"] = "failed"
                        pipeline_logs.append(f"[{time.strftime('%H:%M:%S')}] [ERROR] Schritt '{step['name']}' mit Fehlercode {p.returncode} beendet.")
                        if step_id == "all":
                            pipeline_logs.append(f"[{time.strftime('%H:%M:%S')}] [SYSTEM] Automatischer Workflow abgebrochen.")
                            break
                            
            except Exception as e:
                with pipeline_lock:
                    step["status"] = "failed"
                    pipeline_logs.append(f"[{time.strftime('%H:%M:%S')}] [ERROR] Fehler bei Ausführung von '{step['name']}': {str(e)}")
                    if step_id == "all":
                        break
                        
    finally:
        with pipeline_lock:
            pipeline_state["running"] = False
            pipeline_state["current_step_index"] = -1

def run_generation_process():
    global processing_state
    processing_state["running"] = True
    processing_state["progress"] = 5
    processing_state["status"] = "Starte Analyse-Prozess..."
    processing_state["error"] = None

    try:
        py_executable = sys.executable or "python"
        
        processing_state["progress"] = 30
        processing_state["status"] = "Aktualisiere interaktives Dashboard..."
        time.sleep(0.5)

        # Run generate_dashboard.py to regenerate dashboard HTML
        p2 = subprocess.Popen(
            [py_executable, "src/generate_dashboard.py"], 
            cwd=str(WORKSPACE_DIR), 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        
        for i in range(40, 95, 10):
            if p2.poll() is not None:
                break
            processing_state["progress"] = i
            processing_state["status"] = f"Aktualisiere interaktives Dashboard... ({i}%)"
            time.sleep(0.3)
            
        stdout, stderr = p2.communicate()
        if p2.returncode != 0:
            raise Exception(f"Fehler bei generate_dashboard: {stderr.decode('utf-8', errors='ignore')}")

        processing_state["progress"] = 100
        processing_state["status"] = "Fertiggestellt!"
    except Exception as e:
        print(f"[!] Fehler bei der Berichterstellung: {e}")
        processing_state["error"] = str(e)
        processing_state["status"] = "Fehler aufgetreten"
    finally:
        time.sleep(1)
        processing_state["running"] = False

def kill_existing_server(port):
    import subprocess
    import os
    try:
        output = subprocess.check_output("netstat -ano", shell=True).decode("utf-8", errors="ignore")
        pids = set()
        for line in output.splitlines():
            if f":{port}" in line and ("LISTENING" in line or "ABH" in line or "Listening" in line):
                parts = line.strip().split()
                if len(parts) >= 5:
                    try:
                        pids.add(int(parts[-1]))
                    except ValueError:
                        pass
        
        my_pid = os.getpid()
        for pid in pids:
            if pid != my_pid:
                print(f"[*] Gefunden: Alter Server-Prozess mit PID {pid} belegt Port {port}. Beende...")
                try:
                    subprocess.run(f"taskkill /F /PID {pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    time.sleep(0.5)
                except Exception as e:
                    print(f"[!] Fehler beim Beenden von PID {pid}: {e}")
    except Exception as e:
        print(f"[!] Fehler beim Suchen/Beenden von Prozessen auf Port {port}: {e}")

def start_server():
    kill_existing_server(PORT)
    server_address = ("", PORT)
    httpd = ThreadingHTTPServer(server_address, DashboardRequestHandler)
    print(f"=========================================")
    print(f"[*] Forex EA Dashboard Server gestartet")
    print(f"[*] Server laeuft unter http://localhost:{PORT}/")
    print(f"[*] Dashboard: http://localhost:{PORT}/report/dashboard.html")
    print(f"=========================================")
    print(f"[*] Drücke Strg+C zum Beenden.")
    
    # Auto-open dashboard in default browser
    webbrowser.open(f"http://localhost:{PORT}/report/dashboard.html")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Server wird beendet...")
        httpd.server_close()
        print("[+] Server gestoppt.")

if __name__ == "__main__":
    start_server()
