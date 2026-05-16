"""
Zepto Inventory Dashboard — Flask Backend
Fixed: consistent column names, error handling, safe SQL params
"""

import json
import traceback
from flask import Flask, render_template, request, jsonify
from db import get_db_connection

app = Flask(__name__)


# ── DB Helper ──────────────────────────────────────────────

def run_query(query, params=(), fetchone=False):
    """Execute query, return rows. Handles connection lifecycle."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        result = cur.fetchone() if fetchone else cur.fetchall()
        cur.close()
        return result
    finally:
        conn.close()


def safe_float(val, default=0.0):
    try:
        return float(val) if val is not None else default
    except (TypeError, ValueError):
        return default


def safe_int(val, default=0):
    try:
        return int(val) if val is not None else default
    except (TypeError, ValueError):
        return default


# ── Build WHERE clause ─────────────────────────────────────

def build_where(filters):
    """
    Returns (where_clause_str, params_list).
    Expects filters dict with keys:
      categories, stockStatus, mrpRange, discountRange, weightRange, search
    """
    conditions = ["1=1"]
    params = []

    cats = filters.get("categories", [])
    if cats:
        conditions.append("category = ANY(%s)")
        params.append(cats)

    stock = filters.get("stockStatus", "All")
    if stock == "In Stock":
        conditions.append("outofstock = false")
    elif stock == "Out of Stock":
        conditions.append("outofstock = true")

    mrp = filters.get("mrpRange")
    if mrp and len(mrp) == 2:
        conditions.append("mrp >= %s AND mrp <= %s")
        params.extend([safe_float(mrp[0]), safe_float(mrp[1])])

    disc = filters.get("discountRange")
    if disc and len(disc) == 2:
        conditions.append("discountpercent >= %s AND discountpercent <= %s")
        params.extend([safe_float(disc[0]), safe_float(disc[1])])

    wt = filters.get("weightRange")
    if wt and len(wt) == 2:
        conditions.append("weightingms >= %s AND weightingms <= %s")
        params.extend([safe_float(wt[0]), safe_float(wt[1])])

    search = filters.get("search", "").strip()
    if search:
        conditions.append("(name ILIKE %s OR sku_id::text ILIKE %s)")
        pattern = f"%{search}%"
        params.extend([pattern, pattern])

    return " AND ".join(conditions), params


# ── Routes ─────────────────────────────────────────────────

@app.route("/")
def dashboard():
    return render_template("dashboard.html")


@app.route("/api/init")
def init_data():
    """Return filter ranges and distinct categories."""
    try:
        cats_rows = run_query(
            "SELECT DISTINCT category FROM zepto WHERE category IS NOT NULL ORDER BY category"
        )
        categories = [r[0] for r in cats_rows]

        mrp_row  = run_query("SELECT MIN(mrp), MAX(mrp) FROM zepto", fetchone=True)
        disc_row = run_query("SELECT MIN(discountpercent), MAX(discountpercent) FROM zepto", fetchone=True)
        wt_row   = run_query("SELECT MIN(weightingms), MAX(weightingms) FROM zepto", fetchone=True)

        return jsonify({
            "categories":    categories,
            "mrpRange":      [safe_float(mrp_row[0]),  safe_float(mrp_row[1],  10000)],
            "discountRange": [safe_float(disc_row[0]), safe_float(disc_row[1], 100)],
            "weightRange":   [safe_float(wt_row[0]),   safe_float(wt_row[1],   10000)],
        })
    except Exception:
        traceback.print_exc()
        return jsonify({"error": "Init failed"}), 500


@app.route("/api/data", methods=["POST"])
def dashboard_data():
    """Return all chart data for the given filter state."""
    try:
        filters = request.get_json(force=True) or {}
        where, params = build_where(filters)
        low_qty = safe_int(filters.get("lowStockThreshold", 20), 20)

        # ── KPIs ───────────────────────────────────────────
        total_skus = run_query(
            f"SELECT COUNT(sku_id) FROM zepto WHERE {where}", params, fetchone=True
        )[0]

        oos_row = run_query(
            f"""SELECT ROUND(
                    SUM(CASE WHEN outofstock THEN 1 ELSE 0 END) * 100.0
                    / NULLIF(COUNT(*), 0), 1)
                FROM zepto WHERE {where}""",
            params, fetchone=True
        )
        oos_pct = safe_float(oos_row[0])

        disc_row = run_query(
            f"SELECT ROUND(AVG(discountpercent)::numeric, 1) FROM zepto WHERE {where}",
            params, fetchone=True
        )
        avg_discount = safe_float(disc_row[0])

        rev_row = run_query(
            f"""SELECT SUM(discountedsellingprice * availablequantity)
                FROM zepto WHERE outofstock = false AND {where}""",
            params, fetchone=True
        )
        potential_revenue = safe_float(rev_row[0])

        # ── Chart 1: Discount Histogram ────────────────────
        c1 = run_query(
            f"""SELECT FLOOR(discountpercent / 10) * 10 AS bucket, COUNT(*) AS cnt
                FROM zepto
                WHERE discountpercent IS NOT NULL AND {where}
                GROUP BY bucket ORDER BY bucket""",
            params
        )
        chart1 = [{"bucket": f"{int(r[0])}–{int(r[0])+10}%", "count": safe_int(r[1])} for r in c1]

        # ── Chart 2: MRP vs Selling Price ─────────────────
        c2 = run_query(
            f"""SELECT category,
                       ROUND(AVG(mrp)::numeric, 2)                   AS avg_mrp,
                       ROUND(AVG(discountedsellingprice)::numeric, 2) AS avg_sp
                FROM zepto WHERE {where}
                GROUP BY category
                ORDER BY avg_mrp DESC""",
            params
        )
        chart2 = [{"category": r[0], "avg_mrp": safe_float(r[1]), "avg_sp": safe_float(r[2])} for r in c2]

        # ── Chart 3: Scatter MRP vs Discount ──────────────
        # Limit to 500 rows for performance
        c3 = run_query(
            f"""SELECT name, mrp, discountpercent, category
                FROM zepto
                WHERE weightingms > 0 AND outofstock = false AND {where}
                LIMIT 500""",
            params
        )
        chart3 = [
            {"name": r[0], "mrp": safe_float(r[1]), "discount": safe_float(r[2]), "category": r[3]}
            for r in c3
        ]

        # ── Chart 4: Donut Stock Ratio ─────────────────────
        c4 = run_query(
            f"""SELECT outofstock, COUNT(*) AS cnt
                FROM zepto WHERE {where}
                GROUP BY outofstock""",
            params
        )
        chart4 = [{"status": "Out of Stock" if r[0] else "In Stock", "count": safe_int(r[1])} for r in c4]

        # ── Chart 5: Stacked Bar Stock by Category ─────────
        c5 = run_query(
            f"""SELECT category,
                       SUM(CASE WHEN outofstock = true  THEN 1 ELSE 0 END) AS out_of_stock,
                       SUM(CASE WHEN outofstock = false THEN 1 ELSE 0 END) AS in_stock
                FROM zepto WHERE {where}
                GROUP BY category
                ORDER BY category""",
            params
        )
        chart5 = [
            {"category": r[0], "out_of_stock": safe_int(r[1]), "in_stock": safe_int(r[2])}
            for r in c5
        ]

        # ── Chart 6: Low Stock Bar ─────────────────────────
        c6 = run_query(
            f"""SELECT name, category, availablequantity
                FROM zepto
                WHERE outofstock = false
                  AND availablequantity < %s
                  AND {where}
                ORDER BY availablequantity ASC
                LIMIT 20""",
            [low_qty] + params
        )
        chart6 = [{"name": r[0], "category": r[1], "qty": safe_int(r[2])} for r in c6]

        # ── Chart 7: Treemap Revenue ───────────────────────
        c7 = run_query(
            f"""SELECT category,
                       ROUND(SUM(discountedsellingprice * availablequantity)::numeric, 2) AS revenue
                FROM zepto
                WHERE outofstock = false AND {where}
                GROUP BY category
                ORDER BY revenue DESC""",
            params
        )
        chart7 = [{"category": r[0], "revenue": safe_float(r[1])} for r in c7]

        # ── Chart 8: SKU Count ─────────────────────────────
        c8 = run_query(
            f"""SELECT category, COUNT(sku_id) AS cnt
                FROM zepto WHERE {where}
                GROUP BY category
                ORDER BY cnt DESC""",
            params
        )
        chart8 = [{"category": r[0], "count": safe_int(r[1])} for r in c8]

        # ── Chart 9: Radar Avg Discount ───────────────────
        c9 = run_query(
            f"""SELECT category, ROUND(AVG(discountpercent)::numeric, 1) AS avg_d
                FROM zepto WHERE {where}
                GROUP BY category
                ORDER BY avg_d DESC""",
            params
        )
        chart9 = [{"category": r[0], "avg_discount": safe_float(r[1])} for r in c9]

        # ── Chart 10: Boxplot Price/Gram ──────────────────
        c10 = run_query(
            f"""SELECT category,
                       MIN(ppg),
                       PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY ppg) AS q1,
                       PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY ppg) AS median,
                       PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY ppg) AS q3,
                       MAX(ppg)
                FROM (
                    SELECT category,
                           discountedsellingprice / NULLIF(weightingms, 0) AS ppg
                    FROM zepto
                    WHERE weightingms > 0 AND outofstock = false AND {where}
                ) sub
                GROUP BY category
                HAVING MIN(ppg) IS NOT NULL
                ORDER BY median ASC""",
            params
        )
        chart10 = [
            {
                "category": r[0],
                "min":    safe_float(r[1]),
                "q1":     safe_float(r[2]),
                "median": safe_float(r[3]),
                "q3":     safe_float(r[4]),
                "max":    safe_float(r[5]),
            }
            for r in c10
        ]

        # ── Chart 11: Best / Worst Value per Gram ─────────
        c11 = run_query(
            f"""SELECT name, category,
                       ROUND((discountedsellingprice / NULLIF(weightingms, 0))::numeric, 4) AS ppg,
                       RANK() OVER (PARTITION BY category ORDER BY discountedsellingprice / NULLIF(weightingms, 0) ASC)  AS best_rank,
                       RANK() OVER (PARTITION BY category ORDER BY discountedsellingprice / NULLIF(weightingms, 0) DESC) AS worst_rank
                FROM zepto
                WHERE weightingms > 0 AND {where}""",
            params
        )
        chart11_best  = [
            {"name": r[0], "category": r[1], "price_per_gram": safe_float(r[2])}
            for r in c11 if r[3] == 1
        ]
        chart11_worst = [
            {"name": r[0], "category": r[1], "price_per_gram": safe_float(r[2])}
            for r in c11 if r[4] == 1
        ]

        return jsonify({
            "kpis": {
                "total_skus":        safe_int(total_skus),
                "oos_pct":           oos_pct,
                "avg_discount":      avg_discount,
                "potential_revenue": potential_revenue,
            },
            "charts": {
                "chart1":       chart1,
                "chart2":       chart2,
                "chart3":       chart3,
                "chart4":       chart4,
                "chart5":       chart5,
                "chart6":       chart6,
                "chart7":       chart7,
                "chart8":       chart8,
                "chart9":       chart9,
                "chart10":      chart10,
                "chart11_best":  chart11_best,
                "chart11_worst": chart11_worst,
            },
        })

    except Exception:
        traceback.print_exc()
        return jsonify({"error": "Data fetch failed"}), 500


# ── Run ────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, port=5000)