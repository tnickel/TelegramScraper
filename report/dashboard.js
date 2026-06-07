// ========== Global Error Handler ==========
// Shows a visible error toast when any JS error occurs
window.onerror = function(message, source, lineno, colno, error) {
    console.error("JS Error:", message, source, lineno, colno, error);
    showErrorToast("JavaScript Fehler: " + message);
    return false;
};
window.addEventListener('unhandledrejection', function(event) {
    console.error("Unhandled Promise:", event.reason);
    showErrorToast("Async Fehler: " + (event.reason ? event.reason.message || event.reason : "Unbekannt"));
});

function showErrorToast(msg) {
    let errorToast = document.getElementById("error-toast");
    if (!errorToast) {
        errorToast = document.createElement("div");
        errorToast.id = "error-toast";
        errorToast.style.cssText = "position:fixed;top:20px;right:20px;z-index:99999;background:linear-gradient(135deg,#dc2626,#b91c1c);color:white;padding:1rem 1.5rem;border-radius:12px;font-family:Inter,sans-serif;font-size:0.9rem;max-width:500px;box-shadow:0 8px 32px rgba(0,0,0,0.4);cursor:pointer;transition:opacity 0.3s;";
        errorToast.onclick = function() { errorToast.style.display = 'none'; };
        document.body.appendChild(errorToast);
    }
    errorToast.innerText = "⚠️ " + msg;
    errorToast.style.display = "block";
    errorToast.style.opacity = "1";
    setTimeout(() => {
        errorToast.style.opacity = "0";
        setTimeout(() => { errorToast.style.display = "none"; }, 300);
    }, 8000);
}

// ========== Helper: Escape HTML ==========
function escapeHtml(str) {
    if (typeof str !== 'string') return str;
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

let currentPage = 1;
const pageSize = 20;
let totalRecords = 0;
let totalPages = 0;
let currentFilter = "all";
let currentSearch = "";
let currentSort = "rank";
let currentDirection = "desc";
let searchTimeout = null;

function loadRobotsPage(page) {
    if (page !== undefined) currentPage = page;
    
    const tbody = document.getElementById("robots-table-body");
    if (tbody) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 3rem;"><div class="loading-spinner" style="display: inline-block; width: 30px; height: 30px; border: 3px solid rgba(255,255,255,0.1); border-radius: 50%; border-top-color: var(--accent-purple); animation: spin 1s ease-in-out infinite;"></div><p style="margin-top: 1rem; color: var(--text-secondary);">Lade Daten...</p></td></tr>';
    }
    
    const url = `/api/robots?page=${currentPage}&pageSize=${pageSize}&filter=${encodeURIComponent(currentFilter)}&search=${encodeURIComponent(currentSearch)}&sort=${encodeURIComponent(currentSort)}&direction=${encodeURIComponent(currentDirection)}`;
    
    fetch(url)
        .then(res => {
            if (!res.ok) throw new Error("Server-Fehler beim Laden");
            return res.json();
        })
        .then(data => {
            totalRecords = data.total;
            totalPages = data.totalPages;
            renderTable(data.robots, (currentPage - 1) * pageSize);
            renderPaginationControls();
        })
        .catch(err => {
            console.error("Error loading robots:", err);
            showErrorToast("Fehler beim Laden der Roboter: " + err.message);
            if (tbody) {
                tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 3rem; color: var(--accent-red);">⚠️ Fehler beim Laden der Daten vom Server. Bitte stelle sicher, dass der Server läuft.</td></tr>`;
            }
        });
}

function renderPaginationControls() {
    const prevBtn = document.getElementById("prev-page-btn");
    const nextBtn = document.getElementById("next-page-btn");
    const infoEl = document.getElementById("pagination-info");
    const pageDisplay = document.getElementById("page-num-display");
    
    if (!prevBtn || !nextBtn || !infoEl || !pageDisplay) return;
    
    prevBtn.disabled = (currentPage <= 1);
    prevBtn.style.opacity = (currentPage <= 1) ? "0.4" : "1";
    prevBtn.style.pointerEvents = (currentPage <= 1) ? "none" : "auto";
    
    nextBtn.disabled = (currentPage >= totalPages);
    nextBtn.style.opacity = (currentPage >= totalPages) ? "0.4" : "1";
    nextBtn.style.pointerEvents = (currentPage >= totalPages) ? "none" : "auto";
    
    const start = totalRecords > 0 ? (currentPage - 1) * pageSize + 1 : 0;
    const end = Math.min(currentPage * pageSize, totalRecords);
    infoEl.innerHTML = `Zeige <strong>${start}-${end}</strong> von <strong>${totalRecords}</strong> EAs`;
    
    pageDisplay.innerText = `Seite ${currentPage} von ${Math.max(1, totalPages)}`;
}

function changePage(page) {
    if (page < 1 || page > totalPages) return;
    currentPage = page;
    loadRobotsPage();
    const tableContainer = document.getElementById("table-view-container");
    if (tableContainer) {
        tableContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

// Render Table
function renderTable(data, startIndex) {
    if (startIndex === undefined) startIndex = 0;
    const tbody = document.getElementById("robots-table-body");
    if (!tbody) { showErrorToast("Tabelle konnte nicht gefunden werden (robots-table-body)"); return; }
    let html = "";

    data.forEach((r, idx) => {
        // Determine Risk badge color class
        let riskClass = "badge-medium";
        if (r.risk.toLowerCase().includes("very high") || r.risk.toLowerCase().includes("extrem")) riskClass = "badge-high";
        else if (r.risk.toLowerCase().includes("low") || r.risk.toLowerCase().includes("gering")) riskClass = "badge-low";
        else if (r.risk.toLowerCase().includes("scam")) riskClass = "badge-scam";

        // Build comments HTML using string concatenation
        let posCommentsHtml = '';
        if (r.pos_comments.length > 0) {
            r.pos_comments.forEach(c => {
                posCommentsHtml += '<div class="comment-box">"' + escapeHtml(c) + '"</div>';
            });
        } else {
            posCommentsHtml = '<p class="empty-text">Keine spezifischen positiven Kommentare gefunden.</p>';
        }

        let negCommentsHtml = '';
        if (r.neg_comments.length > 0) {
            negCommentsHtml = '<h4>Kritik &amp; Warnungen</h4>';
            r.neg_comments.forEach(c => {
                negCommentsHtml += '<div class="comment-box neg">"' + escapeHtml(c) + '"</div>';
            });
        }

        // Build files HTML
        let filesHtml = '';
        let filesListStr = '';
        if (r.files.length > 0) {
            r.files.forEach(f => {
                filesHtml += '<li class="file-item"><a href="/extracted_data/forex_files/' + encodeURIComponent(f) + '" target="_blank">' + escapeHtml(f) + '</a></li>';
            });
            filesListStr = r.files.slice(0, 3).map(f => escapeHtml(f)).join(', ');
            if (r.files.length > 3) {
                filesListStr += ' (+ ' + (r.files.length - 3) + ' weitere)';
            }
        } else {
            filesHtml = '<li class="empty-text">Keine übereinstimmenden Dateien im Verzeichnis gefunden.</li>';
            filesListStr = 'Keine Dateien';
        }

        html += '<tr class="table-row" id="row-' + r.id + '" onclick="selectRow(\'' + r.id + '\')" ondblclick="toggleExpand(\'' + r.id + '\')">'
            + '<td><strong>#' + (startIndex + idx + 1) + '</strong></td>'
            + '<td class="robot-name">'
                + '<div>' + escapeHtml(r.name) + (r.mentions > 300 ? ' 🔥' : '') + '</div>'
                + '<div class="robot-inline-files" style="font-size: 0.725rem; color: var(--text-secondary); margin-top: 0.25rem; font-weight: normal; max-width: 320px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="' + escapeHtml(r.files.join(', ')) + '">'
                    + filesListStr
                + '</div>'
            + '</td>'
            + '<td>' + r.mentions + ' Postings</td>'
            + '<td><span class="score-box" style="color: ' + (r.score > 75 ? 'var(--accent-green)' : (r.score > 40 ? 'var(--accent-orange)' : 'var(--accent-red)')) + '">' + r.score + '/100</span></td>'
            + '<td>' + escapeHtml(r.strategy) + '</td>'
            + '<td><span class="badge ' + riskClass + '">' + escapeHtml(r.risk) + '</span></td>'
            + '<td>' + r.files.length + ' Dateien</td>'
            + '</tr>'
            + '<tr class="detail-row" id="detail-' + r.id + '">'
            + '<td colspan="7"><div class="detail-content"><div class="detail-grid">'
            + '<div class="detail-section">'
            + '<h4>Beschreibung</h4><p>' + escapeHtml(r.description) + '</p>'
            + '<h4>Community Comments (English Mentions)</h4>' + posCommentsHtml
            + negCommentsHtml
            + '</div>'
            + '<div class="detail-section">'
            + '<h4>⚙️ Empfehlungen</h4>'
            + '<p><strong>Zeiteinheit:</strong> ' + escapeHtml(r.timeframe) + '<br><strong>Paare:</strong> ' + escapeHtml(r.pairs) + '</p>'
            + '<h4>📁 Lokale Dateien (' + r.files.length + ')</h4>'
            + '<ul class="file-list">' + filesHtml + '</ul>'
            + '</div>'
            + '</div></div></td></tr>';
    });
    try {
        tbody.innerHTML = html;
    } catch(renderErr) {
        showErrorToast("Fehler beim Rendern der Tabelle: " + renderErr.message);
        console.error("renderTable innerHTML error:", renderErr);
    }
}

// Select Row
function selectRow(id) {
    const rows = document.querySelectorAll(".table-row");
    rows.forEach(r => r.classList.remove("selected"));
    const row = document.getElementById(`row-${id}`);
    if (row) {
        row.classList.add("selected");
    }
}

// Expand/Collapse Row
let expandedId = null;
function toggleExpand(id) {
    const detailRow = document.getElementById(`detail-${id}`);
    if (expandedId && expandedId !== id) {
        const prev = document.getElementById(`detail-${expandedId}`);
        if (prev) prev.classList.remove("expanded");
    }
    
    if (detailRow.classList.contains("expanded")) {
        detailRow.classList.remove("expanded");
        expandedId = null;
    } else {
        detailRow.classList.add("expanded");
        expandedId = id;
    }
}

// Search Input handler with debounce
document.getElementById("search-input").addEventListener("input", (e) => {
    currentSearch = e.target.value;
    currentPage = 1;
    
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
        loadRobotsPage();
    }, 300);
});

// Filter Strategy
function filterStrategy(type) {
    try {
        // Hide analytics, workflow and show table view
        document.getElementById("analytics-section").style.display = "none";
        document.getElementById("workflow-section").style.display = "none";
        document.getElementById("table-view-container").style.display = "block";
        document.getElementById("search-input").style.display = "block";
        stopWorkflowPolling();

        // Update active buttons styling
        const buttons = document.querySelectorAll(".btn");
        buttons.forEach(b => {
            b.classList.remove("active");
            const onClickAttr = b.getAttribute("onclick") || "";
            if (onClickAttr.includes(`filterStrategy('${type}')`)) {
                b.classList.add("active");
            }
        });

        currentFilter = type;
        currentPage = 1;

        loadRobotsPage();
    } catch(filterErr) {
        console.error("filterStrategy error:", filterErr);
        showErrorToast("Fehler beim Filtern: " + filterErr.message);
    }
}

// Sort Table
function sortTable(column) {
    try {
        if (currentSort === column) {
            currentDirection = currentDirection === "asc" ? "desc" : "asc";
        } else {
            currentSort = column;
            if (["name", "strategy", "risk"].includes(column)) {
                currentDirection = "asc";
            } else {
                currentDirection = "desc";
            }
        }
        
        currentPage = 1;
        loadRobotsPage();
    } catch(sortErr) {
        console.error("sortTable error:", sortErr);
        showErrorToast("Fehler beim Sortieren: " + sortErr.message);
    }
}

// Modal functions
function openSummaryModal() {
    const modal = document.getElementById("summary-modal");
    const textarea = document.getElementById("summary-text");
    if (!modal || !textarea) return;
    
    textarea.value = "Lade Zusammenfassung von allen Robotern...";
    modal.classList.add("show");
    
    fetch(`/api/robots?page=1&pageSize=1000&sort=mentions&direction=desc`)
        .then(res => {
            if (!res.ok) throw new Error("Server-Fehler");
            return res.json();
        })
        .then(data => {
            const allRobots = data.robots;
            let text = "==================================================\n";
            text += "      FOREX EXPERT ADVISOR CATALOG SUMMARY\n";
            text += "==================================================\n";
            text += `Generiert am: ${new Date().toLocaleDateString('de-DE')} ${new Date().toLocaleTimeString('de-DE')}\n`;
            text += `Gesamtzahl gefundener Roboter: ${data.total}\n`;
            text += "--------------------------------------------------\n\n";

            allRobots.forEach((r, idx) => {
                text += `${idx + 1}. ${r.name.toUpperCase()}\n`;
                text += `   - Strategie:   ${r.strategy}\n`;
                text += `   - Risiko-Typ:  ${r.risk}\n`;
                text += `   - Mentions:    ${r.mentions} Postings im Chat\n`;
                text += `   - EA Score:    ${r.score}/100\n`;
                text += `   - Timeframe:   ${r.timeframe} | Paare: ${r.pairs}\n`;
                text += `   - Dateianzahl: ${r.files.length} zugeordnete Dateien\n`;
                text += `   - Sentiment:   ${r.pos_comments.length} positive / ${r.neg_comments.length} negative Aspekte\n`;
                text += `   - Kurzbeschreibung: ${r.description.substring(0, 120)}...\n`;
                text += "--------------------------------------------------\n";
            });
            
            textarea.value = text;
        })
        .catch(err => {
            textarea.value = "Fehler beim Laden der Zusammenfassung: " + err.message;
        });
}

function closeSummaryModal() {
    document.getElementById("summary-modal").classList.remove("show");
}

function copySummaryText() {
    const textarea = document.getElementById("summary-text");
    textarea.select();
    document.execCommand("copy");
    
    // Show toast
    const toast = document.getElementById("toast-notification");
    toast.innerText = "Kopiert!";
    toast.classList.add("show");
    setTimeout(() => {
        toast.classList.remove("show");
    }, 2000);
}

function downloadSummaryText() {
    const textarea = document.getElementById("summary-text");
    const text = textarea.value;
    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "Forex_Roboter_Katalog_Zusammenfassung.txt";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// Close modal on click outside content
window.onclick = function(event) {
    const summaryModal = document.getElementById("summary-modal");
    const insightsModal = document.getElementById("insights-modal");
    if (event.target === summaryModal) {
        closeSummaryModal();
    } else if (event.target === insightsModal) {
        closeInsightsModal();
    }
}

function openInsightsModal() {
    const modal = document.getElementById("insights-modal");
    const tbody = document.getElementById("insights-modal-table-body");
    if (!modal || !tbody) return;
    
    tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 2rem; color: var(--text-secondary);">Lade analysierte Details und zugehörige Dateien...</td></tr>';
    modal.classList.add("show");
    
    Promise.all([
        fetch('/extracted_data/ea_insights.json').then(res => {
            if (!res.ok) throw new Error("Keine cached Insights gefunden oder Datei existiert nicht.");
            return res.json();
        }),
        fetch('/api/robots?page=1&pageSize=1000').then(res => res.json())
    ])
    .then(([insightsData, robotsData]) => {
        const normalizeName = (str) => {
            if (!str) return "";
            return str.toLowerCase().replace(/[\s\-_]/g, "");
        };

        const filesMap = {};
        if (robotsData && robotsData.robots) {
            robotsData.robots.forEach(r => {
                filesMap[r.name.toLowerCase()] = r.files;
                filesMap[r.id.toLowerCase()] = r.files;
                filesMap[normalizeName(r.name)] = r.files;
                filesMap[normalizeName(r.id)] = r.files;
            });
        }

        let html = "";
        const keys = Object.keys(insightsData);
        if (keys.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 2rem; color: var(--text-secondary);">Noch keine analysierten EAs im Cache vorhanden.</td></tr>';
            return;
        }
        
        keys.forEach((key, idx) => {
            const item = insightsData[key];
            const tf = Array.isArray(item.timeframes) ? item.timeframes.join(", ") : (item.timeframes || "-");
            const pairs = Array.isArray(item.pairs) ? item.pairs.join(", ") : (item.pairs || "-");
            const desc = item.description || "";
            const warnings = item.warnings || "";
            
            // Files matching
            let files = filesMap[key.toLowerCase()] || [];
            if (files.length === 0) {
                files = filesMap[normalizeName(key)] || [];
            }
            if (files.length === 0 && robotsData && robotsData.robots) {
                const keyNorm = normalizeName(key);
                const matchedRobot = robotsData.robots.find(r => {
                    const rNameNorm = normalizeName(r.name);
                    const rIdNorm = normalizeName(r.id);
                    return rNameNorm.includes(keyNorm) || keyNorm.includes(rNameNorm) || rIdNorm.includes(keyNorm) || keyNorm.includes(rIdNorm);
                });
                if (matchedRobot) {
                    files = matchedRobot.files;
                }
            }

            let filesHtml = '';
            if (files.length > 0) {
                filesHtml = files.slice(0, 3).map(f => `<code style="font-size:0.7rem; color:#c084fc; background:rgba(192,132,252,0.1); padding:0.1rem 0.35rem; border-radius:4px; display:inline-block; margin-bottom:0.2rem; max-width:100%; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; border:1px solid rgba(192,132,252,0.15);" title="${escapeHtml(f)}">${escapeHtml(f)}</code>`).join('<br>');
                if (files.length > 3) {
                    filesHtml += `<div style="font-size:0.7rem; color:var(--text-secondary); margin-top:0.2rem;">(+ ${files.length - 3} weitere)</div>`;
                }
            } else {
                filesHtml = '<span style="font-style:italic; opacity:0.5; font-size:0.75rem;">Keine Dateien</span>';
            }

            let detailHtml = `<p style="margin: 0; font-size: 0.9rem; line-height: 1.4; color: var(--text-secondary); white-space: pre-wrap;">${escapeHtml(desc)}</p>`;
            if (warnings && typeof warnings === 'string' && warnings.trim() && warnings.toLowerCase() !== "none" && warnings.toLowerCase() !== "keine" && warnings.toLowerCase() !== "n/a") {
                detailHtml += `<p style="margin-top: 0.5rem; color: #fca5a5; font-size: 0.85rem; font-weight: 600;">⚠️ Risiken: ${escapeHtml(warnings)}</p>`;
            }
            
            html += `<tr style="border-bottom: 1px solid var(--border-glass);">
                <td style="padding: 0.75rem 1rem; font-weight: 600; color: var(--text-primary); vertical-align: top;">
                    <div style="font-size:1rem; margin-bottom:0.4rem; color:var(--text-primary);"><strong style="color:var(--accent-purple); margin-right:0.35rem;">#${idx + 1}</strong> ${escapeHtml(key)}</div>
                    <div class="robot-inline-files-container" style="display:flex; flex-direction:column;">
                        ${filesHtml}
                    </div>
                </td>
                <td style="padding: 0.75rem 1rem; color: var(--text-secondary); vertical-align: top;">${escapeHtml(item.strategy || "-")}</td>
                <td style="padding: 0.75rem 1rem; vertical-align: top;"><span class="badge ${getInsightsRiskClass(item.risk)}">${escapeHtml(item.risk || "-")}</span></td>
                <td style="padding: 0.75rem 1rem; color: var(--text-secondary); vertical-align: top;">${escapeHtml(tf)}</td>
                <td style="padding: 0.75rem 1rem; color: var(--text-secondary); vertical-align: top;">${escapeHtml(pairs)}</td>
                <td style="padding: 0.75rem 1rem; color: var(--text-secondary); vertical-align: top; font-size: 0.85rem; line-height: 1.4;">${detailHtml}</td>
            </tr>`;
        });
        tbody.innerHTML = html;
    })
    .catch(err => {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; padding: 2rem; color: var(--accent-orange);">⚠️ ${err.message}</td></tr>`;
    });
}

function closeInsightsModal() {
    document.getElementById("insights-modal").classList.remove("show");
}

function getInsightsRiskClass(risk) {
    if (!risk) return "badge-medium";
    const r = risk.toLowerCase();
    if (r.includes("very high") || r.includes("extrem")) return "badge-high";
    if (r.includes("low") || r.includes("gering")) return "badge-low";
    if (r.includes("scam")) return "badge-scam";
    return "badge-medium";
}

// Analytics Functions
function showAnalyticsSection() {
    try {
        // Hide table view and search bar
        document.getElementById("table-view-container").style.display = "none";
        document.getElementById("search-input").style.display = "none";
        document.getElementById("workflow-section").style.display = "none";

        // Update active buttons styling
        const buttons = document.querySelectorAll(".btn");
        buttons.forEach(b => b.classList.remove("active"));
        document.getElementById("analytics-tab-btn").classList.add("active");

        // Show analytics section
        document.getElementById("analytics-section").style.display = "block";
        stopWorkflowPolling();

        // Load the report
        loadReportContent();
    } catch(e) {
        showErrorToast("Fehler beim Öffnen der Analytics: " + e.message);
        console.error("showAnalyticsSection error:", e);
    }
}

function loadReportContent() {
    const reportBox = document.getElementById("report-content");
    reportBox.innerHTML = '<div style="text-align: center; padding: 3rem;"><div class="loading-spinner" style="display: inline-block; width: 30px; height: 30px; border: 3px solid rgba(255,255,255,0.1); border-radius: 50%; border-top-color: var(--accent-purple); animation: spin 1s ease-in-out infinite;"></div><p style="margin-top: 1rem; color: var(--text-secondary);">Lade KI-Analysen und zugehörige Dateien...</p></div>';

    Promise.all([
        fetch('/extracted_data/ea_insights.json').then(res => {
            if (!res.ok) throw new Error("Keine cached Insights gefunden oder Datei existiert nicht.");
            return res.json();
        }),
        fetch('/api/robots?page=1&pageSize=1000').then(res => res.json())
    ])
    .then(([insightsData, robotsData]) => {
        const normalizeName = (str) => {
            if (!str) return "";
            return str.toLowerCase().replace(/[\s\-_]/g, "");
        };

        // Map robot name and ID to files list
        const filesMap = {};
        if (robotsData && robotsData.robots) {
            robotsData.robots.forEach(r => {
                filesMap[r.name.toLowerCase()] = r.files;
                filesMap[r.id.toLowerCase()] = r.files;
                filesMap[normalizeName(r.name)] = r.files;
                filesMap[normalizeName(r.id)] = r.files;
            });
        }

        const keys = Object.keys(insightsData);
        if (keys.length === 0) {
            reportBox.innerHTML = `
                <div style="text-align: center; padding: 3rem 1rem;">
                    <p style="font-size: 3.5rem; margin-bottom: 1rem; color: var(--accent-orange);">⚠️</p>
                    <p style="color: var(--text-primary); font-weight: 600; font-size: 1.1rem; margin-bottom: 0.5rem;">
                        Keine KI-Analysedaten vorhanden
                    </p>
                    <p style="color: var(--text-secondary); max-width: 500px; margin: 0 auto 1.5rem auto; font-size: 0.9rem;">
                        Es wurden noch keine EAs vom LLM analysiert. Bitte gehe zum <strong>Workflow-Tab</strong> und führe <strong>Schritt 2 (EA-Details Analyse)</strong> aus, um die KI-Auswertung zu starten.
                    </p>
                    <button class="btn" style="background: linear-gradient(135deg, var(--accent-purple), var(--accent-blue)); color: white; border: none;" onclick="showWorkflowSection()">
                        ⚙️ Zum Workflow wechseln
                    </button>
                </div>
            `;
            return;
        }

        let html = '<h3>🤖 KI-gestützte EA-Analysen &amp; Dateizuordnung (' + keys.length + ' EAs im Cache)</h3>';
        html += '<p style="color: var(--text-secondary); margin-bottom: 1.5rem; font-size: 0.95rem;">Diese Daten wurden durch das Sprachmodell (LLM) autonom extrahiert und mit den zugeordneten Softwarepaketen (.ex4/.ex5/.set) abgeglichen.</p>';
        
        html += '<div class="report-table-container" style="overflow-x: auto;"><table style="width:100%; table-layout: fixed; border-collapse:collapse; min-width: 900px;">';
        html += '<thead><tr style="border-bottom: 2px solid var(--border-glass); text-align: left; background: rgba(255,255,255,0.02);">';
        html += '<th style="padding: 1rem; color: var(--text-primary); cursor: default; width: 25%;">EA Name &amp; Dateien</th>';
        html += '<th style="padding: 1rem; color: var(--text-primary); cursor: default; width: 10%;">Strategie</th>';
        html += '<th style="padding: 1rem; color: var(--text-primary); cursor: default; width: 8%;">Risiko</th>';
        html += '<th style="padding: 1rem; color: var(--text-primary); cursor: default; width: 8%;">Timeframe</th>';
        html += '<th style="padding: 1rem; color: var(--text-primary); cursor: default; width: 10%;">Paare</th>';
        html += '<th style="padding: 1rem; color: var(--text-primary); cursor: default; width: 39%;">Beschreibung &amp; Warnungen</th>';
        html += '</tr></thead><tbody>';

        keys.forEach((key, idx) => {
            const item = insightsData[key];
            const tf = Array.isArray(item.timeframes) ? item.timeframes.join(", ") : (item.timeframes || "-");
            const pairs = Array.isArray(item.pairs) ? item.pairs.join(", ") : (item.pairs || "-");
            const desc = item.description || "";
            const warnings = item.warnings || "";
            
            // Files matching
            let files = filesMap[key.toLowerCase()] || [];
            if (files.length === 0) {
                files = filesMap[normalizeName(key)] || [];
            }
            if (files.length === 0 && robotsData && robotsData.robots) {
                const keyNorm = normalizeName(key);
                const matchedRobot = robotsData.robots.find(r => {
                    const rNameNorm = normalizeName(r.name);
                    const rIdNorm = normalizeName(r.id);
                    return rNameNorm.includes(keyNorm) || keyNorm.includes(rNameNorm) || rIdNorm.includes(keyNorm) || keyNorm.includes(rIdNorm);
                });
                if (matchedRobot) {
                    files = matchedRobot.files;
                }
            }

            let filesHtml = '';
            if (files.length > 0) {
                filesHtml = files.slice(0, 3).map(f => `<code style="font-size:0.7rem; color:#c084fc; background:rgba(192,132,252,0.1); padding:0.1rem 0.35rem; border-radius:4px; display:inline-block; margin-bottom:0.2rem; max-width:100%; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; border:1px solid rgba(192,132,252,0.15);" title="${escapeHtml(f)}">${escapeHtml(f)}</code>`).join('<br>');
                if (files.length > 3) {
                    filesHtml += `<div style="font-size:0.7rem; color:var(--text-secondary); margin-top:0.2rem;">(+ ${files.length - 3} weitere)</div>`;
                }
            } else {
                filesHtml = '<span style="font-style:italic; opacity:0.5; font-size:0.75rem;">Keine Dateien</span>';
            }

            let detailHtml = `<p style="margin: 0; font-size: 0.9rem; line-height: 1.4; color: var(--text-secondary); white-space: pre-wrap;">${escapeHtml(desc)}</p>`;
            if (warnings && typeof warnings === 'string' && warnings.trim() && warnings.toLowerCase() !== "none" && warnings.toLowerCase() !== "keine" && warnings.toLowerCase() !== "n/a") {
                detailHtml += `<p style="margin-top: 0.5rem; color: #fca5a5; font-size: 0.85rem; font-weight: 600;">⚠️ Risiken: ${escapeHtml(warnings)}</p>`;
            }
            
            html += `<tr style="border-bottom: 1px solid var(--border-glass);">
                <td style="padding: 1rem; font-weight: 600; color: var(--text-primary); vertical-align: top;">
                    <div style="font-size:1.05rem; margin-bottom:0.5rem; color:var(--text-primary); font-family:var(--font-display);"><strong style="color:var(--accent-purple); margin-right:0.4rem;">#${idx + 1}</strong> ${escapeHtml(key)}</div>
                    <div class="robot-inline-files-container" style="display:flex; flex-direction:column;">
                        ${filesHtml}
                    </div>
                </td>
                <td style="padding: 1rem; color: var(--text-secondary); vertical-align: top; font-size: 0.9rem;">${escapeHtml(item.strategy || "-")}</td>
                <td style="padding: 1rem; vertical-align: top;"><span class="badge ${getInsightsRiskClass(item.risk)}">${escapeHtml(item.risk || "-")}</span></td>
                <td style="padding: 1rem; color: var(--text-secondary); vertical-align: top; font-size: 0.9rem;">${escapeHtml(tf)}</td>
                <td style="padding: 1rem; color: var(--text-secondary); vertical-align: top; font-size: 0.9rem;">${escapeHtml(pairs)}</td>
                <td style="padding: 1rem; vertical-align: top; line-height: 1.4;">${detailHtml}</td>
            </tr>`;
        });
        html += '</tbody></table></div>';
        
        reportBox.innerHTML = html;
    })
    .catch(err => {
        reportBox.innerHTML = `
            <div style="text-align: center; padding: 3rem 1rem;">
                <p style="font-size: 3.5rem; margin-bottom: 1rem; color: var(--accent-red);">⚠️</p>
                <p style="color: var(--text-primary); font-weight: 600; font-size: 1.1rem; margin-bottom: 0.5rem;">
                    Fehler beim Laden der Analysedaten
                </p>
                <p style="color: var(--text-secondary); max-width: 500px; margin: 0 auto; font-size: 0.9rem;">
                    ${err.message}
                </p>
            </div>
        `;
    });
}

function renderMarkdown(mdText) {
    let html = "";
    let lines = mdText.split("\n");
    let inTable = false;
    let tableRows = [];
    
    let parsedLines = [];
    
    for (let i = 0; i < lines.length; i++) {
        let line = lines[i].trim();
        
        // Handle Table lines
        if (line.startsWith("|") && line.endsWith("|")) {
            let cells = line.split("|").map(c => c.trim()).slice(1, -1);
            // Skip separator rows like |:---|:---:|
            if (cells.every(c => c.match(/^:?-+:?$/))) {
                continue;
            }
            tableRows.push(cells);
            inTable = true;
            continue;
        } else {
            if (inTable) {
                let tHtml = '<div class="report-table-container"><table>';
                tableRows.forEach((row, rIdx) => {
                    let tag = rIdx === 0 ? 'th' : 'td';
                    tHtml += '<tr>';
                    row.forEach(cell => {
                        tHtml += `<${tag}>${formatInline(cell)}</${tag}>`;
                    });
                    tHtml += '</tr>';
                });
                tHtml += '</table></div>';
                parsedLines.push(tHtml);
                tableRows = [];
                inTable = false;
            }
        }
        
        if (line.startsWith("# ")) {
            parsedLines.push(`<h1>${formatInline(line.substring(2))}</h1>`);
        } else if (line.startsWith("## ")) {
            parsedLines.push(`<h2>${formatInline(line.substring(3))}</h2>`);
        } else if (line.startsWith("### ")) {
            parsedLines.push(`<h3>${formatInline(line.substring(4))}</h3>`);
        } else if (line.startsWith("* ") || line.startsWith("- ")) {
            parsedLines.push(`<ul><li>${formatInline(line.substring(2))}</li></ul>`);
        } else if (line.startsWith(">") || line.startsWith("&gt;")) {
            let text = line.replace(/^[>&gt;\s]+/, "");
            parsedLines.push(`<blockquote>${formatInline(text)}</blockquote>`);
        } else if (line === "---") {
            parsedLines.push("<hr>");
        } else if (line !== "") {
            parsedLines.push(`<p>${formatInline(line)}</p>`);
        }
    }
    
    if (inTable) {
        let tHtml = '<div class="report-table-container"><table>';
        tableRows.forEach((row, rIdx) => {
            let tag = rIdx === 0 ? 'th' : 'td';
            tHtml += '<tr>';
            row.forEach(cell => {
                tHtml += `<${tag}>${formatInline(cell)}</${tag}>`;
            });
            tHtml += '</tr>';
        });
        tHtml += '</table></div>';
        parsedLines.push(tHtml);
    }
    
    return parsedLines.join("\n");
}

function formatInline(text) {
    // Simple inline formatting for bold, italics, code and absolute file links
    let formatted = text
        .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/`(.*?)`/g, '<code>$1</code>')
        .replace(/\[(.*?)\]\((.*?)\)/g, (match, linkText, url) => {
            return '<a href="' + url + '" target="_blank">' + linkText + '</a>';
        });
    return formatted;
}

let isGenerating = false;
function generateReport() {
    if (isGenerating) return;
    isGenerating = true;

    const progressContainer = document.getElementById("progress-container");
    const progressBarFill = document.getElementById("progress-bar-fill");
    const progressStatus = document.getElementById("progress-status");
    const progressPercentage = document.getElementById("progress-percentage");
    const generateBtn = document.getElementById("generate-report-btn");

    progressContainer.style.display = "block";
    progressBarFill.classList.add("pulsing");
    generateBtn.disabled = true;
    generateBtn.innerText = "⏳ Erzeuge Bericht...";

    // Trigger the report generation on the local server backend
    fetch("/api/generate-report")
        .then(response => {
            if (!response.ok) throw new Error("Server antwortet nicht");
            return response.json();
        })
        .then(data => {
            // Start polling progress
            pollProgress();
        })
        .catch(error => {
            // Fallback simulation if running offline as static file
            simulateOfflineProgress();
        });
}

function simulateOfflineProgress() {
    const progressBarFill = document.getElementById("progress-bar-fill");
    const progressStatus = document.getElementById("progress-status");
    const progressPercentage = document.getElementById("progress-percentage");
    
    let progress = 0;
    const steps = [
        { p: 10, s: "Lese Telegram Chat-Chunks ein..." },
        { p: 25, s: "Analysiere Währungspaare..." },
        { p: 50, s: "Scanne Timeframe-Erwähnungen..." },
        { p: 75, s: "Erstelle Community-Insights Bericht..." },
        { p: 90, s: "Aktualisiere interaktives Dashboard..." },
        { p: 100, s: "Erfolgreich beendet!" }
    ];

    let currentStepIdx = 0;
    const interval = setInterval(() => {
        if (currentStepIdx < steps.length) {
            const step = steps[currentStepIdx];
            progress = step.p;
            progressStatus.innerText = "Offline-Modus: " + step.s;
            progressBarFill.style.width = progress + "%";
            progressPercentage.innerText = progress + "%";
            currentStepIdx++;
        } else {
            clearInterval(interval);
            finishGeneration();
        }
    }, 800);
}

function pollProgress() {
    const progressBarFill = document.getElementById("progress-bar-fill");
    const progressStatus = document.getElementById("progress-status");
    const progressPercentage = document.getElementById("progress-percentage");

    const interval = setInterval(() => {
        fetch("/api/progress")
            .then(res => res.json())
            .then(state => {
                const progress = state.progress;
                progressStatus.innerText = state.status;
                progressBarFill.style.width = progress + "%";
                progressPercentage.innerText = progress + "%";

                if (state.error) {
                    clearInterval(interval);
                    progressStatus.innerText = "Fehler: " + state.error;
                    progressStatus.style.color = "var(--accent-red)";
                    resetGenerateBtn();
                } else if (progress >= 100) {
                    clearInterval(interval);
                    finishGeneration();
                }
            })
            .catch(err => {
                clearInterval(interval);
                progressStatus.innerText = "Verbindungsfehler zum Server";
                resetGenerateBtn();
            });
    }, 400);
}

function finishGeneration() {
    const progressStatus = document.getElementById("progress-status");
    const progressBarFill = document.getElementById("progress-bar-fill");
    
    progressStatus.innerText = "Erfolgreich beendet! Lade Seite neu...";
    progressBarFill.classList.remove("pulsing");
    
    // Show toast
    const toast = document.getElementById("toast-notification");
    toast.innerText = "Bericht erfolgreich aktualisiert!";
    toast.classList.add("show");
    
    setTimeout(() => {
        toast.classList.remove("show");
        // Reload page to reflect new dashboard data
        window.location.reload();
    }, 1500);
}

function resetGenerateBtn() {
    isGenerating = false;
    const generateBtn = document.getElementById("generate-report-btn");
    generateBtn.disabled = false;
    generateBtn.innerText = "🔄 Vollständigen Bericht erzeugen";
    document.getElementById("progress-bar-fill").classList.remove("pulsing");
}

let workflowInterval = null;
let logOffset = 0;
let isWorkflowPolling = false;

function showWorkflowSection() {
    try {
        // Hide table view, search bar and analytics section
        document.getElementById("table-view-container").style.display = "none";
        document.getElementById("search-input").style.display = "none";
        document.getElementById("analytics-section").style.display = "none";

        // Update active buttons styling
        const buttons = document.querySelectorAll(".btn");
        buttons.forEach(b => b.classList.remove("active"));
        document.getElementById("workflow-tab-btn").classList.add("active");

        // Show workflow section
        const wfSection = document.getElementById("workflow-section");
        if (!wfSection) {
            showErrorToast("Workflow-Section nicht gefunden! Bitte Dashboard neu generieren.");
            return;
        }
        wfSection.style.display = "block";

        // Start workflow polling immediately
        startWorkflowPolling();
    } catch(e) {
        showErrorToast("Fehler beim Öffnen des Workflow: " + e.message);
        console.error("showWorkflowSection error:", e);
    }
}

function startWorkflowPolling() {
    if (isWorkflowPolling) return;
    isWorkflowPolling = true;
    pollWorkflowState();
}

function stopWorkflowPolling() {
    isWorkflowPolling = false;
    if (workflowInterval) {
        clearTimeout(workflowInterval);
        workflowInterval = null;
    }
}

function pollWorkflowState() {
    if (!isWorkflowPolling) return;

    fetch("/api/pipeline/state")
        .then(res => {
            if (!res.ok) throw new Error("Server-Fehler");
            return res.json();
        })
        .then(state => {
            updateWorkflowUI(state);
            
            // If running, poll logs
            if (state.running) {
                pollWorkflowLogs();
            }
            
            // Schedule next poll
            if (isWorkflowPolling) {
                workflowInterval = setTimeout(pollWorkflowState, 1000);
            }
        })
        .catch(err => {
            console.error("Fehler beim Abrufen des Pipeline-Status:", err);
            if (isWorkflowPolling) {
                workflowInterval = setTimeout(pollWorkflowState, 2000);
            }
        });
}

function updateWorkflowUI(state) {
    // Update step cards
    state.steps.forEach(step => {
        const card = document.getElementById("node-" + step.id);
        const badge = document.getElementById("badge-" + step.id);
        const progressFill = document.getElementById("progress-" + step.id);
        
        if (!card) return;
        
        // Clear old status classes
        card.classList.remove("pending", "running", "completed", "failed");
        card.classList.add(step.status);
        
        // Update badge and progress
        if (step.status === "pending") {
            badge.innerText = "Bereit";
        } else if (step.status === "running") {
            badge.innerText = "In Arbeit (" + step.progress + "%)";
        } else if (step.status === "completed") {
            badge.innerText = "Fertig";
        } else if (step.status === "failed") {
            badge.innerText = "Fehler";
        }
        
        progressFill.style.width = step.progress + "%";
    });

    // Disable buttons if pipeline is running
    const runAllBtn = document.getElementById("run-all-btn");
    const resetBtn = document.getElementById("reset-pipeline-btn");
    const stepButtons = document.querySelectorAll(".btn-run-step");
    
    if (state.running) {
        runAllBtn.disabled = true;
        runAllBtn.style.opacity = 0.5;
        runAllBtn.innerText = "⏳ Workflow läuft...";
        resetBtn.disabled = true;
        resetBtn.style.opacity = 0.5;
        stepButtons.forEach(btn => {
            btn.disabled = true;
            btn.style.opacity = 0.5;
        });
    } else {
        runAllBtn.disabled = false;
        runAllBtn.style.opacity = 1;
        runAllBtn.innerText = "▶️ Gesamten Workflow ausführen";
        resetBtn.disabled = false;
        resetBtn.style.opacity = 1;
        stepButtons.forEach(btn => {
            btn.disabled = false;
            btn.style.opacity = 1;
        });
    }
}

function pollWorkflowLogs() {
    fetch("/api/pipeline/logs?offset=" + logOffset)
        .then(res => {
            if (!res.ok) throw new Error("Fehler beim Laden der Logs");
            return res.json();
        })
        .then(data => {
            if (data.logs && data.logs.length > 0) {
                const consoleBox = document.getElementById("console-box-content");
                
                // Clear welcome message on first load of logs
                if (logOffset === 0) {
                    consoleBox.innerHTML = "";
                }
                
                data.logs.forEach(log => {
                    const lineDiv = document.createElement("div");
                    lineDiv.className = "log-line";
                    
                    // Color coding based on prefixes
                    if (log.includes("[SYSTEM]")) {
                        lineDiv.classList.add("system");
                    } else if (log.includes("[ERROR]")) {
                        lineDiv.classList.add("error");
                    } else if (log.includes("[SUCCESS]")) {
                        lineDiv.classList.add("success");
                    } else {
                        lineDiv.classList.add("stdout");
                    }
                    
                    lineDiv.innerText = log;
                    consoleBox.appendChild(lineDiv);
                });
                
                logOffset = data.offset;
                // Scroll to bottom
                consoleBox.scrollTop = consoleBox.scrollHeight;
            }
        })
        .catch(err => console.error("Fehler beim Abrufen der Logs:", err));
}

function runPipeline(stepId) {
    // If running "all", clear logs first in UI
    if (stepId === "all" || logOffset === 0) {
        const consoleBox = document.getElementById("console-box-content");
        consoleBox.innerHTML = '<div style="color: var(--text-secondary);">Workflow gestartet...</div>';
        logOffset = 0;
    }
    
    let url = "/api/pipeline/run?step=" + stepId;
    if (stepId === "analysis" || stepId === "all") {
        const slider = document.getElementById("limit-slider");
        if (slider) {
            url += "&limit=" + slider.value;
        }
    }
    
    fetch(url)
        .then(res => res.json())
        .then(data => {
            if (data.status === "started") {
                startWorkflowPolling();
            } else if (data.status === "already_running") {
                alert("Es läuft bereits ein Prozess!");
            }
        })
        .catch(err => alert("Verbindungsfehler zum Server: " + err));
}

function resetPipeline() {
    if (confirm("Möchten Sie den Status aller Schritte zurücksetzen und die Logs löschen?")) {
        fetch("/api/pipeline/reset")
            .then(res => res.json())
            .then(data => {
                if (data.status === "reset") {
                    logOffset = 0;
                    const consoleBox = document.getElementById("console-box-content");
                    consoleBox.innerHTML = '<div style="color: var(--text-secondary);">Status zurückgesetzt. Bereit.</div>';
                    // Query state once to update cards
                    fetch("/api/pipeline/state")
                        .then(res => res.json())
                        .then(state => updateWorkflowUI(state));
                }
            })
            .catch(err => alert("Fehler beim Zurücksetzen: " + err));
    }
}

function copyConsoleLogs() {
    const lines = document.querySelectorAll("#console-box-content .log-line");
    let logText = "";
    lines.forEach(l => {
        logText += l.innerText + "\n";
    });
    
    if (!logText) {
        logText = document.getElementById("console-box-content").innerText;
    }
    
    navigator.clipboard.writeText(logText)
        .then(() => {
            const toast = document.getElementById("toast-notification");
            toast.innerText = "Logs in die Zwischenablage kopiert!";
            toast.classList.add("show");
            setTimeout(() => {
                toast.classList.remove("show");
            }, 1500);
        })
        .catch(err => alert("Kopieren fehlgeschlagen: " + err));
}

// API Key functions
let hasSavedKey = false;

function checkApiKey() {
    fetch("/api/config/get")
        .then(res => res.json())
        .then(data => {
            const statusEl = document.getElementById("api-key-status");
            const inputEl = document.getElementById("gemini-api-key-input");
            const modelSelect = document.getElementById("openrouter-model-select");
            
            if (data.has_key) {
                hasSavedKey = true;
                statusEl.innerText = "Aktiv: " + data.masked_key;
                statusEl.style.color = "var(--accent-green)";
                inputEl.placeholder = "API-Key ist aktiv (" + data.masked_key + ")";
            } else {
                hasSavedKey = false;
                statusEl.innerText = "Nicht konfiguriert";
                statusEl.style.color = "var(--accent-red)";
                inputEl.placeholder = "OpenRouter API-Key";
            }
            
            if (data.model && modelSelect) {
                modelSelect.value = data.model;
            }
        })
        .catch(err => console.error("Fehler beim Abrufen des API-Keys:", err));
}

function saveApiKey() {
    const inputEl = document.getElementById("gemini-api-key-input");
    const modelSelect = document.getElementById("openrouter-model-select");
    const key = inputEl.value.trim();
    const model = modelSelect ? modelSelect.value : "meta-llama/llama-3.1-8b-instruct";
    
    if (!key && !hasSavedKey) {
        alert("Bitte gib einen gültigen API-Key ein!");
        return;
    }
    
    fetch("/api/config/save?key=" + encodeURIComponent(key) + "&model=" + encodeURIComponent(model))
        .then(res => res.json())
        .then(data => {
            if (data.status === "success") {
                inputEl.value = "";
                checkApiKey();
                
                // Show toast
                const toast = document.getElementById("toast-notification");
                toast.innerText = "API-Key & Modell erfolgreich gespeichert!";
                toast.classList.add("show");
                setTimeout(() => {
                    toast.classList.remove("show");
                }, 2000);
            } else {
                alert("Fehler beim Speichern: " + data.message);
            }
        })
        .catch(err => alert("Verbindungsfehler: " + err));
}

function testLlm() {
    const btn = document.getElementById("btn-test-llm");
    const resultEl = document.getElementById("llm-test-result");
    
    btn.disabled = true;
    btn.innerText = "🧪 Teste...";
    btn.style.opacity = "0.7";
    
    resultEl.style.display = "block";
    resultEl.style.background = "rgba(0, 0, 0, 0.2)";
    resultEl.style.color = "var(--text-secondary)";
    resultEl.style.borderColor = "var(--border-glass)";
    resultEl.innerText = "Sende Test-Anfrage an OpenRouter... Bitte warten.";
    
    fetch("/api/config/test-llm")
        .then(res => res.json())
        .then(data => {
            btn.disabled = false;
            btn.innerText = "🧪 LLM Testen";
            btn.style.opacity = "1";
            
            if (data.status === "success") {
                resultEl.style.background = "rgba(16, 185, 129, 0.05)";
                resultEl.style.borderColor = "rgba(16, 185, 129, 0.2)";
                resultEl.style.color = "var(--accent-green)";
                resultEl.innerHTML = "<strong>Verbindung erfolgreich!</strong><br>Modell-Antwort: <em>\"" + data.response + "\"</em>";
            } else {
                resultEl.style.background = "rgba(239, 68, 68, 0.05)";
                resultEl.style.borderColor = "rgba(239, 68, 68, 0.2)";
                resultEl.style.color = "var(--accent-red)";
                resultEl.innerHTML = "<strong>Fehler bei Verbindung!</strong><br>" + data.message;
            }
        })
        .catch(err => {
            btn.disabled = false;
            btn.innerText = "🧪 LLM Testen";
            btn.style.opacity = "1";
            
            resultEl.style.background = "rgba(239, 68, 68, 0.05)";
            resultEl.style.borderColor = "rgba(239, 68, 68, 0.2)";
            resultEl.style.color = "var(--accent-red)";
            resultEl.innerHTML = "<strong>Netzwerkfehler:</strong> " + err;
        });
}

function toggleApiKeyVisibility() {
    const inputEl = document.getElementById("gemini-api-key-input");
    if (inputEl.type === "password") {
        inputEl.type = "text";
    } else {
        inputEl.type = "password";
    }
}

function loadStats() {
    fetch('/api/stats')
        .then(res => {
            if (!res.ok) throw new Error("Server-Fehler");
            return res.json();
        })
        .then(data => {
            document.getElementById("stat-files").innerText = data.clustered_files.toLocaleString('de-DE');
            document.getElementById("stat-messages").innerText = data.scanned_messages.toLocaleString('de-DE');
            document.getElementById("stat-robots").innerText = data.identified_robots.toLocaleString('de-DE');
            document.getElementById("top-sentiment").innerText = data.global_sentiment_rate + "%";
            
            // Update analyzed count in Step 2 card
            const countEl = document.getElementById("analyzed-count-display");
            if (countEl && data.insights_count !== undefined) {
                countEl.innerText = data.insights_count;
            }
        })
        .catch(err => {
            console.error("Fehler beim Laden der Statistiken:", err);
        });
}

function resetAnalysisCache() {
    if (confirm("Möchten Sie den Analyse-Cache wirklich leeren? Alle bisherigen LLM-Bewertungen gehen verloren und das Dashboard wird aktualisiert.")) {
        const btn = document.getElementById("reset-cache-btn");
        if (btn) {
            btn.disabled = true;
            btn.innerText = "Leert...";
        }
        
        fetch("/api/pipeline/reset-cache")
            .then(res => res.json())
            .then(data => {
                if (btn) {
                    btn.disabled = false;
                    btn.innerText = "Leeren 🗑️";
                }
                if (data.status === "success") {
                    // Show toast
                    const toast = document.getElementById("toast-notification");
                    toast.innerText = "Analyse-Cache erfolgreich zurückgesetzt!";
                    toast.classList.add("show");
                    setTimeout(() => {
                        toast.classList.remove("show");
                    }, 2000);
                    
                    // Reload stats and robots page
                    loadStats();
                    loadRobotsPage(1);
                } else {
                    alert("Fehler beim Zurücksetzen: " + data.message);
                }
            })
            .catch(err => {
                if (btn) {
                    btn.disabled = false;
                    btn.innerText = "Leeren 🗑️";
                }
                alert("Verbindungsfehler: " + err);
            });
    }
}

// Initial Render
try {
    loadRobotsPage(1);
} catch(initErr) {
    showErrorToast("Fehler bei der Initialisierung: " + initErr.message);
    console.error("Init error:", initErr);
}
try {
    checkApiKey();
} catch(apiErr) {
    console.log("API Key Check nicht möglich (Server evtl. nicht aktiv)");
}
try {
    loadStats();
} catch(statsErr) {
    console.log("Stats Check nicht möglich (Server evtl. nicht aktiv)");
}

// Check if pipeline is running on load
fetch("/api/pipeline/state")
    .then(res => res.json())
    .then(state => {
        if (state.running) {
            showWorkflowSection();
        }
    })
    .catch(err => console.log("Lokal-Server nicht aktiv oder keine Pipeline-Unterstützung."));
