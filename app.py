import os
import logging
import psycopg

from flask import Flask, jsonify, request
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

logging.basicConfig(
    filename="api.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)


def get_db_connection():
    return psycopg.connect(
        host=os.getenv("DBHOST"),
        dbname=os.getenv("DBNAME"),
        user=os.getenv("DBUSER"),
        password=os.getenv("DBPASSWORD"),
        sslmode=os.getenv("SSLMODE", "require"),
        connect_timeout=5
    )


def init_db():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id SERIAL PRIMARY KEY,
                    hostname VARCHAR(100) NOT NULL,
                    metric VARCHAR(50) NOT NULL,
                    value DOUBLE PRECISION NOT NULL,
                    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
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

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO metrics (hostname, metric, value)
                    VALUES (%s, %s, %s)
                    """,
                    (data["hostname"], data["metric"], value)
                )

        logging.info(
            "Stored metric: host=%s metric=%s value=%s",
            data["hostname"],
            data["metric"],
            value
        )

        return jsonify({"status": "stored"}), 201

    except Exception as e:
        logging.error("Database error: %s", e)
        return jsonify({"error": "database error"}), 500


@app.get("/metrics")
def get_metrics():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, timestamp, hostname, metric, value
                FROM metrics
                ORDER BY id DESC
            """)

            rows = cur.fetchall()

    result = []

    for row in rows:
        result.append({
            "id": row[0],
            "timestamp": row[1].isoformat(),
            "hostname": row[2],
            "metric": row[3],
            "value": row[4]
        })

    return jsonify(result), 200


@app.errorhandler(Exception)
def handle_error(error):
    logging.exception("Unhandled API error")
    return jsonify({"error": "internal server error"}), 500


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)