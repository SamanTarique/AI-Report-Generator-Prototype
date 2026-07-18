 
import os
import io
import uuid
import base64
import traceback
 
from flask import Flask, request, jsonify
from flask_cors import CORS
import matplotlib.pyplot as plt
 
from ai_report_generator import (
    load_data,
    clean_data,
    calculate_kpis,
    business_report_analysis,
    build_kpi_card_figure,
    build_chart_figure,
    generate_ai_report,
)
 
app = Flask(__name__)
CORS(app)  # allows a frontend on a different domain (e.g. Lovable) to call this API
 
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
 
 
def to_native(val):
    """Converts numpy/pandas scalars (np.int64, np.float64, np.bool_...) to
    plain Python types so jsonify() never chokes on a groupby result."""
    if hasattr(val, "item"):
        return val.item()
    return val
 
 
def fig_to_base64(fig) -> str:
    """Encodes a matplotlib Figure straight into a data URI — no file, no disk."""
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", bbox_inches="tight", dpi=110)
    plt.close(fig)
    buffer.seek(0)
    return f"data:image/png;base64,{base64.b64encode(buffer.read()).decode('utf-8')}"
 
 
@app.route("/health", methods=["GET"])
def health():
    """Render/Railway pings this to confirm the service is alive."""
    return jsonify({"status": "ok"})
 
 
@app.route("/generate-report", methods=["POST"])
def generate_report():
    """
    Upload a CSV -> run the full ai_report_generator pipeline -> return
    KPIs, business analysis, the AI-written narrative, and charts as
    base64 PNG strings (ready to drop straight into an <img src="..."> tag).
 
    Form fields (multipart/form-data):
      - file: the CSV file (required)
      - dataset_type: "Sales" | "Attendance" | "Inventory" | "Finance" | "Employee"
    """
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded. Send it as form field 'file'."}), 400
 
    file = request.files["file"]
    if not file.filename.endswith(".csv"):
        return jsonify({"error": "Please upload a .csv file"}), 400
 
    dataset_type = request.form.get("dataset_type", "Sales")
 
    request_id = uuid.uuid4().hex[:10]
    csv_path = os.path.join(UPLOAD_DIR, f"{request_id}.csv")
    file.save(csv_path)
 
    try:
        df = load_data(csv_path)
        df = clean_data(df)
        kpis = calculate_kpis(df, dataset_type)
        analysis = business_report_analysis(df, dataset_type)
        ai_report = generate_ai_report(dataset_type, kpis, analysis)
 
        # --- Charts: build in-memory Figures, encode to base64, never touch disk ---
        charts = {}
        kpi_fig = build_kpi_card_figure(kpis)
        if kpi_fig:
            charts["kpi_cards"] = fig_to_base64(kpi_fig)
        for title, data in analysis.items():
            if data is None or len(data) == 0:
                continue
            fig = build_chart_figure(title, data)
            key = title.lower().replace(" ", "_")
            charts[key] = fig_to_base64(fig)
 
        # pandas Series -> plain dict, all numpy scalars converted to native types
        analysis_json = {
            title: {str(idx): to_native(val) for idx, val in series.items()}
            for title, series in analysis.items()
        }
        kpis_json = {k: to_native(v) for k, v in kpis.items()}
 
        return jsonify({
            "dataset_type": dataset_type,
            "kpis": kpis_json,
            "analysis": analysis_json,
            "ai_report": ai_report,
            "charts": charts,  # {chart_name: "data:image/png;base64,..."}
        })
 
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
 
    finally:
        if os.path.exists(csv_path):
            os.remove(csv_path)
 
 
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
