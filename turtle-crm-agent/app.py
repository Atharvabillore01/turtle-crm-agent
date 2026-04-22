"""
Flask API server for the Turtle CRM Field-Filler Agent.
Exposes a single endpoint: POST /extract
"""

import csv
import json
import tempfile
from pathlib import Path
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory

from agents.orchestrator import Orchestrator
from main import _write_csv
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
        results = orchestrator.orchestrate(transcript_paths=[tmp_path])
        duration = round((datetime.now() - start).total_seconds(), 2)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    # Save to output dir as well
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    used_model = model or orchestrator.model

    filled_fields = {k: v for k, v in results.items() if v.get("value") is not None}
    base = {
        "client_id": client_id,
        "extracted_at": datetime.now().isoformat(),
        "duration_seconds": duration,
    }

    all_payload = {**base, "total_fields": len(results), "fields": results}
    filled_payload = {**base, "total_fields": len(filled_fields), "fields": filled_fields}

    with open(output_dir / f"{client_id}_extraction_{ts}_all.json", "w", encoding="utf-8") as f:
        json.dump(all_payload, f, indent=2, ensure_ascii=False)
    with open(output_dir / f"{client_id}_extraction_{ts}_filled.json", "w", encoding="utf-8") as f:
        json.dump(filled_payload, f, indent=2, ensure_ascii=False)

    _write_csv(output_dir / f"{client_id}_extraction_{ts}.csv", client_id, used_model, results)
    generate_html_report(output_dir / f"{client_id}_extraction_{ts}.html", client_id, used_model, results)

    # Return both in the API response
    return jsonify({**all_payload, "filled_fields": filled_payload["fields"]})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
