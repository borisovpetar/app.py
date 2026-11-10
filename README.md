# CS2 Monitoring API - Task 3

Routes:
- GET /health
- POST /metrics
- GET /metrics

POST example:
{
  "hostname": "MON01",
  "metric": "cpu",
  "value": 42.5
}

Storage:
- SQLite database: monitoring.db

Logging:
- API log file: api.log

Run:
pip install -r requirements.txt
python app.py
