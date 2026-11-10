import logging
import sqlite3
from datetime import datetime
from flask import Flask, jsonify, request

app = Flask(__name__)
DB_FILE = "monitoring.db"

logging.basicConfig(
    filename="api.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                hostname TEXT NOT NULL,
                metric TEXT NOT NULL,
                value REAL NOT NULL
            )
        """)

@app.get("/health")
def health():
    return jsonify({"status": "ok"}), 200

@app.post("/metrics")
def add_metric():
    data = request.get_json(silent=True)

    if not data:
        logging.error("POST /metrics failed: no JSON body")
        return jsonify({"error": "JSON body required"}), 400

    required = {"hostname", "metric", "value"}
    if not required.issubset(data):
        logging.error("POST /metrics failed: missing required fields")
        return jsonify({"error": "hostname, metric and value are required"}), 400

    try:
        value = float(data["value"])
    except (TypeError, ValueError):
        logging.error("POST /metrics failed: value is not numeric")
        return jsonify({"error": "value must be numeric"}), 400

    timestamp = data.get("timestamp", datetime.now().isoformat())

    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            "INSERT INTO metrics (timestamp, hostname, metric, value) VALUES (?, ?, ?, ?)",
            (timestamp, data["hostname"], data["metric"], value)
        )

    logging.info(
        "Stored metric: host=%s metric=%s value=%s",
        data["hostname"], data["metric"], value
    )

    return jsonify({"status": "stored"}), 201

@app.get("/metrics")
def get_metrics():
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, timestamp, hostname, metric, value FROM metrics ORDER BY id DESC"
        ).fetchall()

    return jsonify([dict(row) for row in rows]), 200

@app.errorhandler(Exception)
def handle_error(error):
    logging.exception("Unhandled API error")
    return jsonify({"error": "internal server error"}), 500

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)
