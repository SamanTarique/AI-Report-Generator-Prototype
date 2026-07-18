"""
ai_report_generator.py
AI Report Generator Prototype — SafeX Solutions Business Automation Research
Individual Module — Group 27 — Week 2

This is the core business-logic module: data cleaning, KPI calculation,
business analysis, chart building, and AI report writing. It contains
ONLY function/constant definitions — nothing runs on import. This is
what makes it safe for app.py (Flask) to import: importing this file
has zero side effects (no downloads, no chart windows, no API calls).

Run this file directly to see a sample input/output demo:
    python ai_report_generator.py
"""

import os
import json
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")  # non-interactive backend — safe for scripts/servers
import matplotlib.pyplot as plt
import seaborn as sns
from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# FIX: load_dotenv() with no arguments searches the current working
# directory (and upward), which depends on WHERE you clicked "Run" from
# in VS Code -- not always this script's folder. Pointing it explicitly
# at SCRIPT_DIR/.env makes it work no matter how you run the script.
load_dotenv(dotenv_path=os.path.join(SCRIPT_DIR, ".env"))

SAMPLE_CSV_PATH = os.path.join(SCRIPT_DIR, "dataset", "Sample_Superstore.csv")
OUTPUT_DIR = "output_charts"


# ===========================================================
# STEP 1: Load Data
# ===========================================================
def load_data(csv_path: str) -> pd.DataFrame:
    """Encoding-safe CSV loader — real-world CSVs are rarely clean UTF-8."""
    for encoding in ["utf-8", "utf-8-sig", "latin1", "cp1252"]:
        try:
            return pd.read_csv(csv_path, encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Could not read {csv_path} with any known encoding.")


# ===========================================================
# STEP 2: Data Cleaning
# ===========================================================
def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans the dataset without assuming it's already clean:
      - fills missing numeric values (mean), categorical values (mode)
      - drops any rows where missing values couldn't be handled
      - removes duplicate rows
      - strips whitespace from text columns
      - auto-converts numeric/date columns still stored as text
        (tries multiple date formats for robustness)
      - drops fully empty rows/columns
    """
    df = df.copy()

    # --- Missing values ---
    numeric_cols = df.select_dtypes(include=np.number).columns
    object_cols = df.select_dtypes(include="object").columns
    for col in numeric_cols:
        if df[col].isnull().any():
            df[col] = df[col].fillna(df[col].mean())
    for col in object_cols:
        if df[col].isnull().any() and not df[col].mode().empty:
            df[col] = df[col].fillna(df[col].mode().iloc[0])
    df = df.dropna()  # catches anything imputation couldn't fix

    # --- Duplicate rows ---
    df = df.drop_duplicates()

    # --- Whitespace ---
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].astype(str).str.strip()

    # --- Auto-convert numeric/date columns (content-based, not by column name) ---
    date_formats = ["%m-%d-%Y", "%d-%m-%Y", "%m/%d/%Y", "%d/%m/%Y"]
    for col in df.select_dtypes(include="object").columns:
        numeric_attempt = pd.to_numeric(df[col], errors="coerce")
        if numeric_attempt.notna().mean() >= 0.9:
            df[col] = numeric_attempt
            continue

        converted_date = pd.Series(index=df.index, dtype="datetime64[ns]")
        for fmt in date_formats:
            converted_date = converted_date.fillna(pd.to_datetime(df[col], format=fmt, errors="coerce"))
        if converted_date.notna().mean() >= 0.7:
            df[col] = converted_date

    # --- Drop fully empty rows/columns ---
    df = df.dropna(how="all", axis=0)
    df = df.dropna(how="all", axis=1)

    return df


# ===========================================================
# STEP 3: Synonym-Based Column Finder
# ===========================================================
SYNONYMS = {
    "sales": ["sales", "revenue", "turnover", "amount"],
    "profit": ["profit", "gain", "margin", "earning"],
    "quantity": ["quantity", "qty", "units"],
    "category": ["category", "type", "segment"],
    "region": ["region", "area", "zone", "location"],
    "present": ["present", "attend"],
    "absent": ["absent", "leave"],
    "stock": ["stock", "inventory", "warehouse"],
    "reorder": ["reorder", "threshold", "minlevel"],
    "income": ["income", "revenue", "earning"],
    "expense": ["expense", "cost", "spending"],
    "salary": ["salary", "wage", "pay"],
    "department": ["department", "dept", "team"],
    "sub_category": ["sub-category", "subcategory", "sub category"],
    "product": ["product name", "product", "item name", "item"],
    "date": ["order date", "date", "invoice date", "transaction date"],
    "customer": ["customer name", "customer", "client"],
    "employee": ["employee name", "employee", "staff"],
    "warehouse": ["warehouse"],
}


def find(df: pd.DataFrame, concept: str):
    """
    Finds the column matching a business concept regardless of its exact
    name. Exact match is tried FIRST (avoids collisions — e.g. "category"
    wrongly matching a "Segment" column just because "segment" is a listed
    synonym, when an exact "Category" column exists). Partial/substring
    match is the fallback for real-world naming variety.
    """
    keywords = SYNONYMS.get(concept, [concept])
    cols_lower = {c.lower(): c for c in df.columns}
    for kw in keywords:
        if kw in cols_lower:
            return cols_lower[kw]
    for col in df.columns:
        if any(kw in col.lower() for kw in keywords):
            return col
    return None


# ===========================================================
# STEP 4: KPI Calculation
# ===========================================================
def calculate_kpis(df: pd.DataFrame, dataset_type: str) -> dict:
    kpis = {}

    if dataset_type == "Sales":
        sales, profit, qty = find(df, "sales"), find(df, "profit"), find(df, "quantity")
        cat, region, product = find(df, "category"), find(df, "region"), find(df, "product")
        if sales: kpis["Total Sales"] = round(float(df[sales].sum()), 2)
        if profit: kpis["Total Profit"] = round(float(df[profit].sum()), 2)
        if profit and sales and df[sales].sum() != 0:
            kpis["Profit Margin %"] = round(float(df[profit].sum() / df[sales].sum() * 100), 2)
        if qty: kpis["Total Units Sold"] = int(df[qty].sum())
        if cat and sales: kpis["Top Category"] = str(df.groupby(cat)[sales].sum().idxmax())
        if region and sales: kpis["Top Region"] = str(df.groupby(region)[sales].sum().idxmax())
        if product and sales: kpis["Top Selling Product"] = str(df.groupby(product)[sales].sum().idxmax())

    elif dataset_type == "Attendance":
        present, absent = find(df, "present"), find(df, "absent")
        if present: kpis["Total Present Days"] = int(df[present].sum())
        if absent: kpis["Total Absent Days"] = int(df[absent].sum())
        if present and absent:
            total = df[present].sum() + df[absent].sum()
            if total != 0:
                kpis["Attendance Rate %"] = round(float(df[present].sum() / total * 100), 2)

    elif dataset_type == "Inventory":
        stock, reorder = find(df, "stock"), find(df, "reorder")
        if stock and len(df) > 0:
            kpis["Total Stock Units"] = int(df[stock].sum())
            kpis["Average Stock per Item"] = round(float(df[stock].mean()), 2)
        if stock and reorder:
            kpis["Items Below Reorder Level"] = int((df[stock] < df[reorder]).sum())

    elif dataset_type == "Finance":
        income, expense = find(df, "income"), find(df, "expense")
        if income: kpis["Total Income"] = round(float(df[income].sum()), 2)
        if expense: kpis["Total Expenses"] = round(float(df[expense].sum()), 2)
        if income and expense: kpis["Net Balance"] = round(float(df[income].sum() - df[expense].sum()), 2)

    elif dataset_type == "Employee":
        salary, dept = find(df, "salary"), find(df, "department")
        if salary and len(df) > 0:
            kpis["Total Salary Expense"] = round(float(df[salary].sum()), 2)
            kpis["Average Salary"] = round(float(df[salary].mean()), 2)
        if dept and salary:
            kpis["Highest Paying Department"] = str(df.groupby(dept)[salary].sum().idxmax())

    if not kpis:
        for col in df.select_dtypes(include="number").columns[:3]:
            kpis[f"Total {col}"] = round(float(df[col].sum()), 2)

    return kpis


# ===========================================================
# STEP 5: Business Analysis (groupby breakdowns + Monthly/Yearly trends)
# ===========================================================
ANALYSIS_CONFIG = {
    "Sales": [
        ("Sales by Region", "region", "sales", "sum", None),
        ("Sales by Category", "category", "sales", "sum", None),
        ("Profit by Category", "category", "profit", "sum", None),
        ("Top 10 Products by Sales", "product", "sales", "sum", 10),
        ("Average Sales by Region", "region", "sales", "mean", None),
    ],
    "Attendance": [
        ("Attendance by Department", "department", "present", "sum", None),
        ("Absent by Department", "department", "absent", "sum", None),
        ("Top 10 Employees by Attendance", "employee", "present", "sum", 10),
        ("Employees per Department", "department", None, "count", None),
    ],
    "Inventory": [
        ("Stock by Category", "category", "stock", "sum", None),
        ("Stock by Warehouse", "warehouse", "stock", "sum", None),
        ("Top 10 Stock Items", "product", "stock", "sum", 10),
        ("Lowest 5 Stock Items", "product", "stock", "sum", -5),
    ],
    "Finance": [
        ("Income by Category", "category", "income", "sum", None),
        ("Expense by Category", "category", "expense", "sum", None),
        ("Average Expense by Category", "category", "expense", "mean", None),
    ],
    "Employee": [
        ("Salary by Department", "department", "salary", "sum", None),
        ("Average Salary by Department", "department", "salary", "mean", None),
        ("Top 10 Paid Employees", "employee", "salary", "sum", 10),
        ("Employees per Department", "department", None, "count", None),
    ],
}


def business_report_analysis(df: pd.DataFrame, dataset_type: str) -> dict:
    analysis = {}
    entries = ANALYSIS_CONFIG.get(dataset_type, [])

    for title, group_key, value_key, agg, top_n in entries:
        group_col = find(df, group_key)
        value_col = find(df, value_key) if value_key else None
        if not group_col or (value_key and not value_col):
            continue
        result = df.groupby(group_col).size() if agg == "count" else getattr(df.groupby(group_col)[value_col], agg)()
        result = result.sort_values(ascending=False)
        if top_n:
            result = result.head(top_n) if top_n > 0 else result.tail(abs(top_n))
        analysis[title] = result

    # Monthly AND Yearly trends for every "sum" metric used above
    date_col = find(df, "date")
    if date_col and pd.api.types.is_datetime64_any_dtype(df[date_col]):
        metrics = {v for _, _, v, agg, _ in entries if v and agg == "sum"}
        for metric in metrics:
            metric_col = find(df, metric)
            if metric_col:
                analysis[f"Monthly {metric.title()} Trend"] = df.groupby(df[date_col].dt.to_period("M"))[metric_col].sum()
                analysis[f"Yearly {metric.title()} Trend"] = df.groupby(df[date_col].dt.to_period("Y"))[metric_col].sum()

    return analysis


# ===========================================================
# STEP 6: Visualization — reusable chart builders (return Figures, no I/O)
# ===========================================================
def build_kpi_card_figure(kpis: dict):
    """
    Returns a matplotlib Figure of colorful KPI number cards.
    Cards are wide enough for long values (e.g. product names), and the
    value's font size auto-shrinks so long text never gets cut off or
    overflows the card edge.
    """
    if not kpis:
        return None
    colors = ["#2563eb", "#16a34a", "#dc2626", "#9333ea", "#ea580c", "#0891b2"]
    fig, axes = plt.subplots(1, len(kpis), figsize=(4.2 * len(kpis), 2.6))
    if len(kpis) == 1:
        axes = [axes]
    for ax, (k, v), color in zip(axes, kpis.items(), colors * 3):
        val = f"{v:.1f}%" if isinstance(v, float) and "%" in k else \
              f"{v:,.0f}" if isinstance(v, (int, float)) else str(v)

        # Shrink font size for longer text so it fits inside the card
        # width instead of being clipped at the edges.
        text_len = len(val)
        if text_len <= 10:
            font_size = 18
        elif text_len <= 20:
            font_size = 13
        elif text_len <= 35:
            font_size = 10
        else:
            font_size = 8

        ax.set_facecolor(color)
        ax.text(0.5, 0.62, val, ha="center", va="center", fontsize=font_size, fontweight="bold",
                 color="white", transform=ax.transAxes, wrap=True)
        ax.text(0.5, 0.22, k, ha="center", va="center", fontsize=10, color="white", transform=ax.transAxes)
        ax.set_xticks([]); ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)
    plt.tight_layout()
    return fig


def build_chart_figure(title: str, data: pd.Series):
    """
    Picks the chart type from what the DATA actually is (not fragile
    title-string guessing alone):
      - DatetimeIndex/PeriodIndex           -> Line chart (time trend)
      - <=5 categories, all non-negative     -> Pie chart (share of whole)
      - "Top" in title OR long index labels  -> Horizontal bar (readable)
      - everything else                      -> Vertical bar, with labels
    """
    sns.set_style("whitegrid")
    plt.rcParams["axes.titleweight"] = "bold"
    fig, ax = plt.subplots(figsize=(9, 5))

    if isinstance(data.index, (pd.DatetimeIndex, pd.PeriodIndex)):
        x = data.index.to_timestamp() if isinstance(data.index, pd.PeriodIndex) else data.index
        ax.plot(x, data.values, marker="o", linewidth=2.5, color="#dc2626")
        if len(x) > 12:
            step = max(1, len(x) // 8)
            ax.set_xticks(x[::step])
        plt.xticks(rotation=45)

    elif len(data) <= 5 and data.min() >= 0:
        ax.pie(data.values, labels=data.index.astype(str), autopct="%1.1f%%",
               startangle=90, colors=plt.cm.Set3(np.linspace(0, 1, len(data))))

    elif "top" in title.lower() or any(len(str(i)) > 12 for i in data.index):
        top_data = data.head(10)
        sns.barplot(x=top_data.values, y=top_data.index.astype(str), hue=top_data.index.astype(str),
                    palette="viridis", legend=False, ax=ax)
        for i, v in enumerate(top_data.values):
            ax.text(v, i, f" {v:,.0f}", va="center", fontsize=8)

    else:
        top_data = data.head(10)
        sns.barplot(x=top_data.index.astype(str), y=top_data.values, hue=top_data.index.astype(str),
                    palette="viridis", legend=False, ax=ax)
        plt.xticks(rotation=30)
        if len(top_data) <= 8:
            for container in ax.containers:
                ax.bar_label(container, fmt="%.0f", fontsize=8)

    ax.set_title(title, fontsize=14)
    ax.set_xlabel(""); ax.set_ylabel("")
    plt.tight_layout()
    return fig


def visualize_report(df: pd.DataFrame, dataset_type: str, kpis: dict, analysis: dict, output_dir: str):
    """Script mode: builds every chart and SAVES it as a PNG file in output_dir."""
    os.makedirs(output_dir, exist_ok=True)

    kpi_fig = build_kpi_card_figure(kpis)
    if kpi_fig:
        kpi_fig.savefig(os.path.join(output_dir, "kpi_cards.png"), dpi=110, bbox_inches="tight")
        plt.close(kpi_fig)

    for title, data in analysis.items():
        if data is None or len(data) == 0:
            continue
        fig = build_chart_figure(title, data)
        filename = title.replace(" ", "_").replace("/", "-") + ".png"
        fig.savefig(os.path.join(output_dir, filename), dpi=110, bbox_inches="tight")
        plt.close(fig)


# ===========================================================
# STEP 7: AI Written Report (Google GenAI SDK — google-genai package)
# ===========================================================
def _get_gemini_api_key() -> str:
    """
    Looks up the Gemini API key from environment variables.

    FIX: environment variable names are CASE-SENSITIVE. Your key is set
    as "Saman_Gemini_API_Key" (mixed case), so a plain
    os.environ.get("Saman_GEMINI_API_KEY") would silently miss it and
    fall back to mock mode -- no crash, no error, just quietly wrong.
    This does a case-insensitive scan of all env vars instead, so it
    finds your key regardless of exactly how the casing was typed when
    it was set (locally in .env, or in Railway's Variables tab).
    """
    candidate_names = ["Saman_Gemini_API_Key", "GEMINI_API_KEY"]
    env_lower = {k.lower(): v for k, v in os.environ.items()}
    for name in candidate_names:
        val = env_lower.get(name.lower(), "").strip()
        if val:
            return val
    return ""


def generate_ai_report(dataset_type: str, kpis: dict, analysis: dict) -> dict:
    """
    Uses Gemini (via the current google-genai SDK) to turn the KPIs +
    business analysis into a narrative report. Falls back to a clearly
    labeled placeholder if no API key is configured or the call fails,
    so the pipeline always produces complete output.
    """
    api_key = _get_gemini_api_key()

    if not api_key:
        return {
            "executive_summary": f"[MOCK] {dataset_type} dataset analyzed. Add Saman_Gemini_API_Key to .env for live AI insights.",
            "key_findings": ["Placeholder — no Saman_Gemini_API_Key configured."],
            "insights": "Placeholder — configure Saman_Gemini_API_Key to generate a real analysis.",
            "recommendations": ["Add Saman_Gemini_API_Key to .env and re-run."],
            "is_mock": True,
        }

    try:
        from google import genai

        kpi_text = "\n".join(f"- {k}: {v}" for k, v in kpis.items())
        analysis_text = "\n".join(f"{t}: {dict(d.head(3))}" for t, d in analysis.items())

        prompt = f"""You are a senior business analyst. Analyze ONLY the data below.

Dataset Type: {dataset_type}
KPIs:
{kpi_text}
Business Analysis:
{analysis_text}

Return ONLY valid JSON, no markdown, no ```json fences:
{{"executive_summary": "...", "key_findings": ["...","...","..."], "insights": "...", "recommendations": ["...","...","..."]}}"""

        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(model="gemini-flash-latest", contents=prompt)
        raw = response.text.strip().strip("`").replace("json\n", "", 1)
        result = json.loads(raw)
        result["is_mock"] = False
        return result

    except Exception as e:
        return {
            "executive_summary": f"[AI generation failed: {e}]",
            "key_findings": [], "insights": "", "recommendations": [], "is_mock": True,
        }


# ===========================================================
# MAIN — Sample Input/Output Demo (only runs when executed directly)
# ===========================================================
def run_pipeline(csv_path: str, dataset_type: str) -> dict:
    """Runs the full pipeline and returns everything as a dict."""
    df = load_data(csv_path)
    df = clean_data(df)
    kpis = calculate_kpis(df, dataset_type)
    analysis = business_report_analysis(df, dataset_type)
    visualize_report(df, dataset_type, kpis, analysis, OUTPUT_DIR)
    ai_report = generate_ai_report(dataset_type, kpis, analysis)
    return {"kpis": kpis, "analysis": analysis, "ai_report": ai_report}


if __name__ == "__main__":
    # If the sample dataset isn't found locally (e.g. only this .py file
    # was copied without the dataset/ folder), download it from GitHub
    # so the demo always works out of the box.
    if not os.path.exists(SAMPLE_CSV_PATH):
        import urllib.request
        github_csv_url = ("https://raw.githubusercontent.com/SamanTarique/"
                           "AI-Report-Generator-Prototype/refs/heads/main/dataset/Sample_%20Superstore.csv")
        os.makedirs(os.path.dirname(SAMPLE_CSV_PATH), exist_ok=True)
        print(f"'{SAMPLE_CSV_PATH}' not found locally — downloading sample dataset from GitHub...")
        urllib.request.urlretrieve(github_csv_url, SAMPLE_CSV_PATH)
        print("Download complete.\n")

    print("=" * 60)
    print("AI REPORT GENERATOR — SAMPLE RUN")
    print("=" * 60)
    print(f"Input file  : {SAMPLE_CSV_PATH}")
    print("Dataset type: Sales\n")

    result = run_pipeline(SAMPLE_CSV_PATH, dataset_type="Sales")

    print("--- KEY PERFORMANCE INDICATORS ---")
    for k, v in result["kpis"].items():
        print(f"{k:<28}: {v}")

    print("\n--- BUSINESS ANALYSIS (sample) ---")
    for title, data in result["analysis"].items():
        print(f"\n{title}:")
        print(data.head(3).to_string())

    print("\n--- AI REPORT ---")
    ai = result["ai_report"]
    print("Executive Summary:", ai["executive_summary"])
    print("Key Findings:", ai["key_findings"])

    print(f"\nCharts saved to: {OUTPUT_DIR}/")
    print("=" * 60)
    print("DONE")
    print("=" * 60)