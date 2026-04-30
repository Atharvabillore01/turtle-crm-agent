"""
Flask API server for the Turtle CRM Field-Filler Agent.
Exposes a single endpoint: POST /extract
"""

import json
import tempfile
from pathlib import Path
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory

from agents.orchestrator import Orchestrator
from utils.html_export import generate_html_report

app = Flask(__name__, static_folder="static")


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/extract", methods=["POST"])
def extract():
    data = request.get_json()
    client_id = data.get("client_id", "manual_input").strip() or "manual_input"
    transcript_text = data.get("transcript", "").strip()
    model = data.get("model", None)

    if not transcript_text:
        return jsonify({"error": "transcript is required"}), 400

    # Write transcript to a temp file so the existing pipeline can read it
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(transcript_text)
        tmp_path = tmp.name

    try:
        orchestrator = Orchestrator(client_id, model=model)
        start = datetime.now()
        results, per_agent = orchestrator.orchestrate(transcript_paths=[tmp_path])
        duration = round((datetime.now() - start).total_seconds(), 2)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    # Save to output dir as well
    from config import LLM_PROVIDER
    from main import _write_excel, _update_comparison_excel
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    used_model = model or orchestrator.model
    safe_model = used_model.replace("/", "-").replace(":", "-")
    run_dir = Path("output") / f"{LLM_PROVIDER}_{safe_model}_{ts}"
    run_dir.mkdir(parents=True, exist_ok=True)

    base = {
        "client_id": client_id,
        "provider": LLM_PROVIDER,
        "model": used_model,
        "extracted_at": datetime.now().isoformat(),
        "duration_seconds": duration,
    }

    for agent_name, agent_fields in per_agent.items():
        with open(run_dir / f"{client_id}_{agent_name}.json", "w", encoding="utf-8") as f:
            json.dump({**base, "agent": agent_name, "total_fields": len(agent_fields), "fields": agent_fields}, f, indent=2, ensure_ascii=False)

    combined_payload = {**base, "total_fields": len(results), "fields": results}
    with open(run_dir / f"{client_id}_combined.json", "w", encoding="utf-8") as f:
        json.dump(combined_payload, f, indent=2, ensure_ascii=False)

    _write_excel(run_dir / f"{client_id}_extraction.xlsx", client_id, used_model, results, per_agent)
    generate_html_report(run_dir / f"{client_id}_report.html", client_id, used_model, results)

    comparison_file = Path("output") / f"{client_id}_model_comparison.xlsx"
    _update_comparison_excel(comparison_file, LLM_PROVIDER, used_model, results, per_agent)

    # Return combined results in the API response
    return jsonify(combined_payload)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
