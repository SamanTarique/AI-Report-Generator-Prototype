import os
import uuid
import shutil

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS


from ai_report_generator import (
    load_data,
    clean_data,
    calculate_kpis,
    business_report_analysis,
    visualize_report,
    generate_ai_report,
)

app = Flask(__name__)
CORS(app)

UPLOAD_DIR = "uploads"
CHARTS_ROOT = "output_charts"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(CHARTS_ROOT, exist_ok=True)


def to_native(val):
    """
    Converts numpy/pandas scalar types (np.int64, np.float64, np.bool_...)
    to plain Python types. Without this, Flask's jsonify() crashes with
    "Object of type int64 is not JSON serializable" whenever a groupby
    result (e.g. .size(), integer column sums) is passed straight through
    -- this happens routinely with Attendance/Inventory/Employee datasets
    and with any integer-valued analysis.
    """
    if hasattr(val, "item"):
        return val.item()
    return val


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/generate-report", methods=["POST"])
def generate_report():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded. Send it as form field 'file'."}), 400

    file = request.files["file"]
    if not file.filename.endswith(".csv"):
        return jsonify({"error": "Please upload a .csv file"}), 400

    dataset_type = request.form.get("dataset_type", "Sales")

    request_id = uuid.uuid4().hex[:10]
    csv_path = os.path.join(UPLOAD_DIR, f"{request_id}.csv")
    chart_dir = os.path.join(CHARTS_ROOT, request_id)
    file.save(csv_path)

    try:
        df = load_data(csv_path)
        df = clean_data(df)
        kpis = calculate_kpis(df, dataset_type)
        analysis = business_report_analysis(df, dataset_type)
        visualize_report(df, dataset_type, kpis, analysis, chart_dir)
        ai_report = generate_ai_report(dataset_type, kpis, analysis)

        # FIX: wrap every value with to_native() so numpy int64/float64/bool_
        # scalars from groupby results never reach jsonify() directly.
        analysis_json = {
            title: {str(idx): to_native(val) for idx, val in series.items()}
            for title, series in analysis.items()
        }

        chart_files = os.listdir(chart_dir) if os.path.isdir(chart_dir) else []
        chart_urls = [f"/charts/{request_id}/{fname}" for fname in chart_files]

        return jsonify({
            "dataset_type": dataset_type,
            "kpis": kpis,
            "analysis": analysis_json,
            "ai_report": ai_report,
            "charts": chart_urls,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        os.remove(csv_path)


@app.route("/charts/<request_id>/<filename>")
def get_chart(request_id, filename):
    directory = os.path.join(CHARTS_ROOT, request_id)
    return send_from_directory(directory, filename)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
