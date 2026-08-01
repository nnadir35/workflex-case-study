# --------------------------------------------------------------------------- #
# View Layer - UI Templates & CSS                                             #
# --------------------------------------------------------------------------- #

CUSTOM_CSS = """
body, html {
    background-color: #0b0f19 !important;
    color: #f1f5f9 !important;
}
.gradio-container {
    max-width: 100% !important;
    width: 100% !important;
    background: #0b0f19 !important;
    color: #f1f5f9 !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
}

/* Header styling */
.app-header {
    text-align: center;
    padding: 2.5rem 1rem;
    margin-bottom: 2rem;
    background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%);
    border-radius: 16px;
    color: white;
    box-shadow: 0 4px 20px -2px rgba(49, 46, 129, 0.5);
    border: 1px solid #4338ca;
}
.app-header h1 {
    font-size: 2.25rem;
    font-weight: 800;
    margin: 0 0 0.5rem 0;
    color: white !important;
    letter-spacing: -0.025em;
}
.app-header p {
    font-size: 1.1rem;
    color: #e0e7ff;
    max-width: 800px;
    margin: 0 auto;
    opacity: 0.95;
    line-height: 1.6;
}

/* KPI metrics container */
.kpi-container {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
    margin-bottom: 2rem;
}
.kpi-card {
    background: #111827;
    border: 1px solid #1f2937;
    border-radius: 12px;
    padding: 1.25rem;
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.2);
    display: flex;
    flex-direction: column;
}
.kpi-label {
    font-size: 0.75rem;
    font-weight: 600;
    color: #9ca3af;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.kpi-val {
    font-size: 1.75rem;
    font-weight: 700;
    color: #f9fafb;
    margin-top: 0.25rem;
}
.kpi-sub {
    font-size: 0.8rem;
    color: #6b7280;
    margin-top: 0.15rem;
}

/* Log Collapsible */
.log-details {
    background: #1f2937;
    border: 1px solid #374151;
    border-radius: 8px;
    padding: 0.75rem;
    margin-bottom: 2rem;
}
.log-details summary {
    font-weight: 600;
    color: #e5e7eb;
    cursor: pointer;
}
.log-list {
    margin-top: 0.5rem;
    padding-left: 1.25rem;
    font-size: 0.85rem;
    color: #9ca3af;
    list-style-type: disc;
}

/* Card list and individual cards */
.card-list {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
    margin-top: 1rem;
    margin-bottom: 2.5rem;
}
.issue-card {
    background: #111827;
    border: 1px solid #1f2937;
    border-radius: 16px;
    box-shadow: 0 10px 15px -3px rgba(0,0,0,0.3);
    overflow: hidden;
    transition: transform 0.2s, box-shadow 0.2s;
}
.issue-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 20px 25px -5px rgba(0,0,0,0.4);
}
.issue-card.skipped {
    opacity: 0.5;
    background: #1f2937;
}
.card-header {
    background: #1f2937;
    padding: 1rem 1.5rem;
    border-bottom: 1px solid #374151;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.75rem;
}
.card-title-area {
    display: flex;
    align-items: center;
    gap: 0.75rem;
}
.card-num {
    background: #374151;
    color: #f3f4f6;
    font-weight: 700;
    width: 24px;
    height: 24px;
    border-radius: 9999px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.8rem;
}
.badge {
    font-size: 0.75rem;
    font-weight: 700;
    padding: 0.25rem 0.75rem;
    border-radius: 9999px;
    letter-spacing: 0.025em;
}
.badge-create {
    background-color: #064e3b;
    color: #6ee7b7;
}
.badge-update {
    background-color: #1e3a8a;
    color: #93c5fd;
}
.badge-skip {
    background-color: #374151;
    color: #d1d5db;
}
.badge-arr {
    background-color: #78350f;
    color: #fde68a;
    font-weight: 600;
}
.client-info {
    font-size: 0.95rem;
    font-weight: 600;
    color: #f3f4f6;
}

/* Two column layout inside card */
.card-body {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1.5rem;
    padding: 1.5rem;
}
@media (max-width: 768px) {
    .card-body {
        grid-template-columns: 1fr;
    }
}
.column {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
}
.column-title {
    font-size: 0.75rem;
    font-weight: 700;
    color: #9ca3af;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    border-bottom: 2px solid #374151;
    padding-bottom: 0.25rem;
    margin-bottom: 0.5rem;
}
.sender-meta {
    font-size: 0.85rem;
    color: #9ca3af;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
.sender-avatar {
    width: 20px;
    height: 20px;
    border-radius: 9999px;
    background: #6366f1;
    color: white;
    font-weight: bold;
    font-size: 0.7rem;
    display: flex;
    align-items: center;
    justify-content: center;
}
.msg-text {
    background: #1f2937;
    border-left: 4px solid #4f46e5;
    padding: 0.75rem 1rem;
    border-radius: 0 8px 8px 0;
    font-size: 0.9rem;
    color: #e5e7eb;
    line-height: 1.5;
    word-break: break-word;
}
.extracted-info {
    font-size: 0.85rem;
    color: #d1d5db;
    background: #1f2937;
    padding: 0.5rem;
    border-radius: 6px;
    border: 1px solid #374151;
}
.draft-container {
    background: #1f2937;
    border: 1px solid #374151;
    border-radius: 8px;
    padding: 1rem;
}
.draft-title {
    font-weight: 700;
    color: #f9fafb;
    font-size: 0.95rem;
    margin-bottom: 0.5rem;
    border-bottom: 1px solid #374151;
    padding-bottom: 0.25rem;
}
.draft-body {
    font-size: 0.85rem;
    color: #e5e7eb;
    white-space: pre-wrap;
    background: #111827;
    border: 1px dashed #4b5563;
    padding: 0.75rem;
    border-radius: 6px;
    line-height: 1.4;
}
.warning-banner {
    background-color: #78350f;
    border-top: 1px solid #b45309;
    color: #fef3c7;
    padding: 0.75rem 1.5rem;
    font-size: 0.85rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
.error-banner {
    background-color: #7f1d1d;
    border-top: 1px solid #b91c1c;
    color: #fef2f2;
    padding: 0.75rem 1.5rem;
    font-size: 0.85rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

/* Submit Log area styling */
.submit-log-container {
    background: #030712;
    color: #38bdf8;
    padding: 1.25rem;
    border-radius: 12px;
    font-family: monospace;
    font-size: 0.9rem;
    margin-top: 1.5rem;
    box-shadow: 0 4px 6px -1px rgba(0,0,0,0.5);
    max-height: 400px;
    overflow-y: auto;
    border: 1px solid #1f2937;
}
.submit-log-title {
    color: #ffffff;
    font-weight: 700;
    margin-bottom: 0.75rem;
    border-bottom: 1px solid #1f2937;
    padding-bottom: 0.5rem;
}
.submit-log-line {
    margin-bottom: 0.25rem;
    line-height: 1.4;
}
.submit-log-line.done {
    color: #4ade80;
}
.submit-log-line.error {
    color: #f87171;
}

/* Result panel styling */
.result-panel {
    background: #111827;
    border: 1px solid #1f2937;
    border-radius: 12px;
    padding: 1.5rem;
    margin-top: 1.5rem;
    box-shadow: 0 10px 15px -3px rgba(0,0,0,0.3);
}
.result-header {
    font-size: 1.25rem;
    font-weight: 700;
    color: #f9fafb;
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
.result-item {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    padding: 0.75rem 0;
    border-bottom: 1px solid #1f2937;
}
.result-item:last-child {
    border-bottom: none;
}
"""


def render_review(items: list[dict], log: list[str]) -> str:
    if not items:
        return "<div class='text-center py-8 text-gray-500 font-medium'>No messages to process. Click 'Process Messages' to run the pipeline.</div>"

    creates = sum(1 for i in items if i.get("action") == "CREATE")
    updates = sum(1 for i in items if i.get("action") == "UPDATE")
    skipped = sum(1 for i in items if i.get("action") == "SKIP")
    
    total_arr = 0
    for i in items:
        if i.get("action") in ("CREATE", "UPDATE"):
            total_arr += i.get("arr") or 0

    from agent import format_arr
    arr_display_val = format_arr(total_arr) if total_arr > 0 else "$0"

    html = []
    
    # KPI Dashboard Summary
    html.append(f"""
    <div class="kpi-container">
        <div class="kpi-card">
            <span class="kpi-label">Messages Processed</span>
            <span class="kpi-val">{len(items)}</span>
            <span class="kpi-sub">Total candidates</span>
        </div>
        <div class="kpi-card">
            <span class="kpi-label">Total Potential ARR</span>
            <span class="kpi-val" style="color: #059669;">{arr_display_val}</span>
            <span class="kpi-sub">Active deals context</span>
        </div>
        <div class="kpi-card">
            <span class="kpi-label">Tickets to Create</span>
            <span class="kpi-val" style="color: #2563eb;">{creates}</span>
            <span class="kpi-sub">New Jira issues</span>
        </div>
        <div class="kpi-card">
            <span class="kpi-label">Comments to Add</span>
            <span class="kpi-val" style="color: #4f46e5;">{updates}</span>
            <span class="kpi-sub">Jira backlog comments</span>
        </div>
    </div>
    """)

    # Pipeline Log Details
    if log:
        log_items = "".join(f"<li>{line}</li>" for line in log)
        html.append(f"""
        <details class="log-details">
            <summary>⚙️ View Pipeline Execution Log ({len(log)} steps)</summary>
            <ul class="log-list">
                {log_items}
            </ul>
        </details>
        """)

    # Cards list
    html.append("<div class='card-list'>")
    for i, item in enumerate(items, start=1):
        action = item.get("action", "SKIP")
        is_skipped = (action == "SKIP")
        
        badge_cls = {
            "CREATE": "badge-create",
            "UPDATE": "badge-update",
            "SKIP": "badge-skip"
        }.get(action, "badge-skip")
        
        badge_icon = {
            "CREATE": "🆕 CREATE",
            "UPDATE": "🔁 UPDATE",
            "SKIP": "⏭️ SKIP"
        }.get(action, action)

        client = item.get("client") or "Unknown Customer"
        arr = item.get("arr_display", "no ARR data")
        requester = item.get("requester") or item.get("sender") or "Unknown"
        sender_initial = requester[0].upper() if requester else "?"

        card_class = "issue-card" + (" skipped" if is_skipped else "")
        
        html.append(f"<div class='{card_class}'>")
        
        # Card Header
        html.append(f"""
        <div class="card-header">
            <div class="card-title-area">
                <span class="card-num">{i}</span>
                <span class="badge {badge_cls}">{badge_icon}</span>
                <span class="client-info">{client}</span>
            </div>
            <div>
                <span class="badge badge-arr">{arr}</span>
            </div>
        </div>
        """)
        
        # Card Body
        html.append("<div class='card-body'>")
        
        # Left Column: Microsoft Teams Input
        html.append(f"""
        <div class="column">
            <div class="column-title">Microsoft Teams Source</div>
            <div class="sender-meta">
                <div class="sender-avatar">{sender_initial}</div>
                <strong>{requester}</strong> in #feature-requests
            </div>
            <div class="msg-text">"{item.get('text') or ''}"</div>
        </div>
        """)
        
        # Right Column: Action & Output
        html.append("<div class='column'>")
        html.append("<div class='column-title'>Bridge Recommendation & Draft</div>")
        
        if is_skipped:
            html.append("""
            <div style="color: #64748b; font-style: italic; padding: 1rem 0;">
                Skipped: This message does not seem to contain an actionable feature request, or lacks necessary details.
            </div>
            """)
        else:
            # Show extracted data
            hs_match_info = ""
            if item.get("hubspot_match") and item["hubspot_match"] != client:
                hs_match_info = f"<br>• HubSpot Match: <strong>{item['hubspot_match']}</strong>"
                
            html.append(f"""
            <div class="extracted-info">
                • Target Customer: <strong>{client}</strong> ({arr}){hs_match_info}<br>
                • Request Summary: <strong>{item.get('request') or 'N/A'}</strong>
            </div>
            """)
            
            if action == "UPDATE":
                parent = item.get("duplicate_ticket") or {}
                confidence = item.get("duplicate_confidence")
                conf_display = f"{int(confidence * 100)}%" if confidence is not None else "N/A"
                html.append(f"""
                <div style="background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; padding: 0.75rem; font-size: 0.85rem; color: #1e3a8a;">
                    🔗 Duplicate detected: <strong>{parent.get('key')}</strong> — {parent.get('summary')}<br>
                    • Match Confidence: <strong>{conf_display}</strong><br>
                    • Reason: <em>{item.get('duplicate_reason') or 'Matched capability'}</em>
                </div>
                """)

            # Draft content
            html.append("<div class='draft-container'>")
            if action == "CREATE":
                html.append(f"""
                <div class="draft-title">🏷️ Jira Title: {item.get('draft_title') or '_(empty)_'}</div>
                <div class="draft-body">{item.get('draft_body') or ''}</div>
                """)
            else:  # UPDATE
                html.append(f"""
                <div class="draft-title">💬 Jira Comment to append:</div>
                <div class="draft-body">{item.get('draft_body') or ''}</div>
                """)
            html.append("</div>")

        html.append("</div>") # End column
        html.append("</div>") # End card-body
        
        # Error check
        if item.get("error"):
            html.append(f"""
            <div class="error-banner">
                <span>⚠️</span>
                <span><strong>Enrichment/Processing Error:</strong> {item['error']}</span>
            </div>
            """)
            
        html.append("</div>") # End issue-card
        
    html.append("</div>") # End card-list
    return "\n".join(html)


def render_results(results: list[dict]) -> str:
    if not results:
        return ""

    ok = sum(1 for r in results if r.get("ok") and not r.get("skipped"))
    skipped = sum(1 for r in results if r.get("skipped"))
    failed = sum(1 for r in results if not r.get("ok"))

    html = []
    html.append("<div class='result-panel'>")
    html.append(f"""
    <div class="result-header">
        <span>📊</span>
        <span>Submission Sync Summary — {ok} Succeeded · {skipped} Skipped · {failed} Failed</span>
    </div>
    """)
    
    for i, r in enumerate(results, start=1):
        if r.get("skipped"):
            html.append(f"""
            <div class="result-item">
                <span class="badge badge-skip">⏭️ SKIP</span>
                <div style="font-size: 0.9rem; color: #64748b;">
                    Item {i}: Skipped (No request extracted)
                </div>
            </div>
            """)
            continue
            
        if not r.get("ok"):
            html.append(f"""
            <div class="result-item">
                <span class="badge" style="background-color: #fef2f2; color: #991b1b; border: 1px solid #fca5a5;">❌ FAILED</span>
                <div style="font-size: 0.9rem; color: #991b1b;">
                    Item {i} ({r.get('client', 'Unknown')}): <strong>{r.get('error')}</strong>
                </div>
            </div>
            """)
            continue
            
        action = r.get("action", "?")
        badge_cls = "badge-create" if action == "CREATE" else "badge-update"
        action_icon = "🆕 CREATE" if action == "CREATE" else "🔁 UPDATE"
        
        html.append(f"""
        <div class="result-item">
            <span class="badge {badge_cls}">{action_icon}</span>
            <div style="font-size: 0.9rem; color: #1e293b;">
                Item {i}: Synced ticket <strong>{r.get('ticket_key')}</strong> — <span style="color: #475569;">{r.get('feedback')}</span>
            </div>
        </div>
        """)
        
    html.append("</div>")
    return "\n".join(html)


def render_live_submit_log(log_lines: list[str], done: bool = False) -> str:
    title = "🚀 Submit sync in progress..." if not done else "✅ Submit sync completed"
    lines_html = []
    
    for line in log_lines:
        cls = "submit-log-line"
        if "✅" in line or "Done" in line:
            cls += " done"
        elif "❌" in line or "Failed" in line:
            cls += " error"
        lines_html.append(f"<div class='{cls}'>{line}</div>")
        
    if not lines_html:
        lines_html.append("<div class='submit-log-line'>Starting execution...</div>")
        
    return f"""
    <div class="submit-log-container">
        <div class="submit-log-title">{title}</div>
        {"".join(lines_html)}
    </div>
    """


def render_fatal_error(title: str, exc: Exception) -> str:
    details = f"{type(exc).__name__}: {exc}"
    return f"""
    <div class="error-banner" style="margin-top: 1.5rem; border-radius: 8px; border: 1px solid #fca5a5; padding: 1.25rem;">
        <div>
            <h4 style="font-weight: 700; margin: 0 0 0.5rem 0;">❌ {title}</h4>
            <p style="margin: 0 0 0.5rem 0; font-size: 0.9rem;">İşlem tamamlanamadı. Lütfen ayarları kontrol edip tekrar deneyin.</p>
            <code style="font-family: monospace; background: rgba(255,255,255,0.6); padding: 0.2rem 0.4rem; border-radius: 4px;">{details}</code>
        </div>
    </div>
    """
