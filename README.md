# AI Report Generator

An AI-powered service that turns raw business CSV data into a complete
analytics report — KPIs, charts, an AI-written executive summary, and
recommendations — in seconds.

**Project for:** SafeX Solutions — Business Automation Research
**Module:** Individual Week 2 Contribution 

**Live demo:** https://ai-report-generator.ai.studio/

---

## What It Does

Upload a CSV, select the data type (Sales / Attendance / Inventory /
Finance / Employee), and get back:

- Key performance indicators, calculated directly from your data
- Charts (bar, pie, trend lines) auto-generated per breakdown
- An AI-written executive summary, key findings, and recommendations
- A downloadable PDF of the full report

## Tech Stack

**Backend:** Python · Flask · pandas · Matplotlib/Seaborn · Google Gemini API
**Frontend:** React, built with [Google AI Studio](https://aistudio.google.com/) (Build)
**Hosting:** SnapDeploy (backend container)

## API

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Service status check |
| `/generate-report` | POST | Upload a CSV (`file`) + `dataset_type` → returns full report JSON |

## Running Locally

```bash
pip install -r requirements.txt

# Create a .env file in this folder with:
# Saman_Gemini_API_Key=your_key_here

python app.py
# -> runs on http://localhost:5000
```

## Deployment

Hosted on SnapDeploy via the included `Procfile`. The Gemini API key is
set as an environment variable directly on the host — never committed to
the repo (`.env` is gitignored).

---

## Known Limitations

1. **Cold start (~1 min):** the backend sleeps after inactivity (free
   tier). The first request after idle time may take up to a minute to
   respond while the server wakes up — this is expected, not a bug.

2. **AI summary quota:** the Gemini free tier allows 20 AI-narrative
   requests/day. If that limit is reached, the AI-written text falls
   back to a placeholder — but all KPIs and charts, which come directly
   from your data, are unaffected and always fully accurate.

3. **Column recognition:** columns are matched by common naming
   patterns (e.g. `Sales`/`Revenue`/`Turnover` are all understood as the
   same field), not fully free-form. A column with an unrecognized name
   is simply skipped rather than causing an error.

   | Concept | Recognized column names |
   |---|---|
   | Sales | `sales`, `revenue`, `turnover`, `amount` |
   | Profit | `profit`, `gain`, `margin`, `earning` |
   | Quantity | `quantity`, `qty`, `units` |
   | Category | `category`, `type`, `segment` |
   | Sub-category | `sub-category`, `subcategory`, `sub category` |
   | Region | `region`, `area`, `zone`, `location` |
   | Product | `product name`, `product`, `item name`, `item` |
   | Date | `order date`, `date`, `invoice date`, `transaction date` |
   | Customer | `customer name`, `customer`, `client` |
   | Present (attendance) | `present`, `attend`, or a status column with values like "Present/Absent/Late" |
   | Absent (attendance) | `absent`, `leave` |
   | Employee | `employee name`, `employee`, `staff` |
   | Department | `department`, `dept`, `team` |
   | Salary | `salary`, `wage`, `pay` |
   | Stock | `stock`, `inventory`, `warehouse` |
   | Reorder level | `reorder`, `threshold`, `minlevel` |
   | Warehouse | `warehouse` |
   | Income | `income`, `revenue`, `earning` |
   | Expense | `expense`, `cost`, `spending` |


# Authur :**SamanTarique**
