import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from jinja2 import Template

from src.core.models import BatchSummary

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Data Quality Certificate - {{ summary.dataset_name }}</title>
    <style>
        :root {
            --bg: #0d1117;
            --surface: #161b22;
            --surface-border: #30363d;
            --text-main: #f0f6fc;
            --text-muted: #8b949e;
            --pass-color: #238636;
            --fail-color: #da3633;
            --warn-color: #d29922;
            --accent: #58a6ff;
            --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background-color: var(--bg);
            color: var(--text-main);
            font-family: var(--font-family);
            padding: 32px 20px;
            line-height: 1.6;
        }
        .container {
            max-width: 1100px;
            margin: 0 auto;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--surface-border);
            padding-bottom: 24px;
            margin-bottom: 32px;
        }
        .header h1 {
            font-size: 26px;
            font-weight: 700;
            color: var(--text-main);
        }
        .header .badge {
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: 700;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .badge-pass { background: rgba(35, 134, 54, 0.2); color: #3fb950; border: 1px solid #238636; }
        .badge-fail { background: rgba(218, 54, 51, 0.2); color: #f85149; border: 1px solid #da3633; }
        
        .grid-cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 32px;
        }
        .card {
            background: var(--surface);
            border: 1px solid var(--surface-border);
            border-radius: 8px;
            padding: 20px;
        }
        .card-label {
            font-size: 12px;
            color: var(--text-muted);
            text-transform: uppercase;
            margin-bottom: 8px;
            font-weight: 600;
        }
        .card-value {
            font-size: 28px;
            font-weight: 700;
        }
        .text-pass { color: #3fb950; }
        .text-fail { color: #f85149; }
        .text-accent { color: var(--accent); }

        .section {
            background: var(--surface);
            border: 1px solid var(--surface-border);
            border-radius: 8px;
            padding: 24px;
            margin-bottom: 32px;
        }
        .section h2 {
            font-size: 18px;
            margin-bottom: 16px;
            border-bottom: 1px solid var(--surface-border);
            padding-bottom: 8px;
            color: var(--accent);
        }

        .dim-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 12px;
        }
        .dim-box {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--surface-border);
            border-radius: 6px;
            padding: 12px;
            text-align: center;
        }
        .dim-box .dim-name { font-size: 12px; color: var(--text-muted); }
        .dim-box .dim-val { font-size: 20px; font-weight: 700; margin-top: 4px; }

        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }
        th, td {
            text-align: left;
            padding: 12px;
            border-bottom: 1px solid var(--surface-border);
        }
        th {
            background: rgba(255, 255, 255, 0.02);
            color: var(--text-muted);
            font-weight: 600;
        }
        .footer {
            text-align: center;
            font-size: 12px;
            color: var(--text-muted);
            margin-top: 40px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>Data Quality Certificate</h1>
                <p style="color: var(--text-muted); font-size: 14px; margin-top: 4px;">
                    Dataset: <strong>{{ summary.dataset_name }}</strong> | Batch: <code>{{ summary.batch_id }}</code> | Generated: {{ summary.executed_at.strftime('%Y-%m-%d %H:%M:%S UTC') }}
                </p>
            </div>
            <div>
                {% if not summary.sla_breached %}
                <span class="badge badge-pass">✓ SLA Compliant</span>
                {% else %}
                <span class="badge badge-fail">✕ SLA Breached</span>
                {% endif %}
            </div>
        </div>

        <div class="grid-cards">
            <div class="card">
                <div class="card-label">Health Score</div>
                <div class="card-value {% if summary.health_score.overall_score >= 95 %}text-pass{% else %}text-fail{% endif %}">
                    {{ summary.health_score.overall_score }}%
                </div>
            </div>
            <div class="card">
                <div class="card-label">Total Records</div>
                <div class="card-value text-accent">{{ summary.total_records }}</div>
            </div>
            <div class="card">
                <div class="card-label">Clean Ingested</div>
                <div class="card-value text-pass">{{ summary.passed_records }}</div>
            </div>
            <div class="card">
                <div class="card-label">Quarantined</div>
                <div class="card-value {% if summary.quarantined_records > 0 %}text-fail{% else %}text-pass{% endif %}">
                    {{ summary.quarantined_records }}
                </div>
            </div>
            <div class="card">
                <div class="card-label">Latency</div>
                <div class="card-value">{{ summary.processing_duration_ms }} ms</div>
            </div>
        </div>

        <div class="section">
            <h2>Data Quality Dimensions</h2>
            <div class="dim-grid">
                <div class="dim-box">
                    <div class="dim-name">Completeness</div>
                    <div class="dim-val text-accent">{{ summary.health_score.completeness }}%</div>
                </div>
                <div class="dim-box">
                    <div class="dim-name">Validity</div>
                    <div class="dim-val text-accent">{{ summary.health_score.validity }}%</div>
                </div>
                <div class="dim-box">
                    <div class="dim-name">Uniqueness</div>
                    <div class="dim-val text-accent">{{ summary.health_score.uniqueness }}%</div>
                </div>
                <div class="dim-box">
                    <div class="dim-name">Timeliness</div>
                    <div class="dim-val text-accent">{{ summary.health_score.timeliness }}%</div>
                </div>
                <div class="dim-box">
                    <div class="dim-name">Consistency</div>
                    <div class="dim-val text-accent">{{ summary.health_score.consistency }}%</div>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>Schema Drift Analysis</h2>
            <p style="margin-bottom: 12px; color: var(--text-muted);">
                Drift Score: <strong>{{ summary.schema_drift.drift_score }}</strong> | Status: <strong>{{ summary.schema_drift.summary }}</strong>
            </p>
            {% if summary.schema_drift.detected %}
            <table>
                <thead>
                    <tr>
                        <th>Category</th>
                        <th>Details</th>
                    </tr>
                </thead>
                <tbody>
                    {% if summary.schema_drift.missing_columns %}
                    <tr>
                        <td>Missing Required Columns</td>
                        <td style="color: #f85149;">{{ summary.schema_drift.missing_columns | join(', ') }}</td>
                    </tr>
                    {% endif %}
                    {% if summary.schema_drift.unexpected_columns %}
                    <tr>
                        <td>Unexpected Columns</td>
                        <td style="color: #d29922;">{{ summary.schema_drift.unexpected_columns | join(', ') }}</td>
                    </tr>
                    {% endif %}
                    {% if summary.schema_drift.type_mismatches %}
                    <tr>
                        <td>Type Mismatches</td>
                        <td><pre>{{ summary.schema_drift.type_mismatches }}</pre></td>
                    </tr>
                    {% endif %}
                </tbody>
            </table>
            {% endif %}
        </div>

        {% if summary.violations_by_type %}
        <div class="section">
            <h2>Violation Breakdown</h2>
            <table>
                <thead>
                    <tr>
                        <th>Violation Type</th>
                        <th>Occurrences</th>
                    </tr>
                </thead>
                <tbody>
                    {% for v_type, count in summary.violations_by_type.items() %}
                    <tr>
                        <td><code>{{ v_type }}</code></td>
                        <td><strong>{{ count }}</strong></td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        {% endif %}

        <div class="footer">
            Automated Data Quality Gatekeeper & Observability Engine &bull; Zero Data Drift Protocol
        </div>
    </div>
</body>
</html>
"""


BASE_DIR = Path(__file__).resolve().parent.parent.parent


class DataDocsReporter:
    """Generates standalone HTML documentation certificates for quality audit batches."""

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or (BASE_DIR / "reports")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.template = Template(HTML_TEMPLATE)

    def generate_html(self, summary: BatchSummary) -> str:
        return self.template.render(summary=summary)

    def export_to_file(self, summary: BatchSummary, filename: Optional[str] = None) -> Path:
        html_content = self.generate_html(summary)
        fname = filename or f"data_docs_{summary.dataset_name}_{summary.batch_id}.html"
        target_path = self.output_dir / fname
        target_path.write_text(html_content, encoding="utf-8")
        return target_path
