"""
Zepto Inventory Dashboard — Flask Backend
Optimised: connection pooling, single-connection-per-request, batched queries
"""

import traceback
from flask import Flask, render_template, request, jsonify, g
from db import get_db_connection, release_db_connection

app = Flask(__name__)


# ── Per-request connection lifecycle ──────────────────────────

@app.before_request
def _open_conn():
    """Grab ONE pooled connection for the entire request."""
    g.db = get_db_connection()


@app.teardown_request
def _close_conn(exc):
    """Return the connection to the pool after the request."""
    conn = g.pop("db", None)
    if conn is not None:
        if exc:
            conn.rollback()
        release_db_connection(conn)


def run_query(query, params=(), fetchone=False):
    """Execute query on the per-request connection (no new connection)."""
    cur = g.db.cursor()
    cur.execute(query, params)
    result = cur.fetchone() if fetchone else cur.fetchall()
    cur.close()
    return result


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
    """Return filter ranges and distinct categories — single query."""
    try:
        # Combine 4 queries into 1 round trip
        row = run_query("""
            SELECT
                MIN(mrp), MAX(mrp),
                MIN(discountpercent), MAX(discountpercent),
                MIN(weightingms), MAX(weightingms)
            FROM zepto
        """, fetchone=True)

        cats_rows = run_query(
            "SELECT DISTINCT category FROM zepto WHERE category IS NOT NULL ORDER BY category"
        )
        categories = [r[0] for r in cats_rows]

        return jsonify({
            "categories":    categories,
            "mrpRange":      [safe_float(row[0]),  safe_float(row[1],  10000)],
            "discountRange": [safe_float(row[2]),  safe_float(row[3],  100)],
            "weightRange":   [safe_float(row[4]),  safe_float(row[5],  10000)],
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

        # ── KPIs: combine 4 queries into 1 ────────────────
        kpi_row = run_query(
            f"""SELECT
                    COUNT(sku_id),
                    ROUND(
                        SUM(CASE WHEN outofstock THEN 1 ELSE 0 END) * 100.0
                        / NULLIF(COUNT(*), 0), 1),
                    ROUND(AVG(discountpercent)::numeric, 1),
                    SUM(CASE WHEN outofstock = false
                        THEN discountedsellingprice * availablequantity
                        ELSE 0 END)
                FROM zepto WHERE {where}""",
            params, fetchone=True
        )

        # ── Charts 2, 4, 5, 7, 8, 9: combine into 1 category query ──
        cat_rows = run_query(
            f"""SELECT
                    category,
                    ROUND(AVG(mrp)::numeric, 2)                   AS avg_mrp,
                    ROUND(AVG(discountedsellingprice)::numeric, 2) AS avg_sp,
                    SUM(CASE WHEN outofstock = true  THEN 1 ELSE 0 END) AS oos_count,
                    SUM(CASE WHEN outofstock = false THEN 1 ELSE 0 END) AS is_count,
                    ROUND(SUM(CASE WHEN outofstock = false
                        THEN discountedsellingprice * availablequantity
                        ELSE 0 END)::numeric, 2)                 AS revenue,
                    COUNT(sku_id)                                  AS sku_count,
                    ROUND(AVG(discountpercent)::numeric, 1)       AS avg_discount
                FROM zepto WHERE {where}
                GROUP BY category
                ORDER BY category""",
            params
        )

        # Build charts 2, 4, 5, 7, 8, 9 from the single category query
        chart2 = sorted(
            [{"category": r[0], "avg_mrp": safe_float(r[1]), "avg_sp": safe_float(r[2])} for r in cat_rows],
            key=lambda x: x["avg_mrp"], reverse=True
        )

        # Chart 4: Donut stock ratio
        total_oos = sum(safe_int(r[3]) for r in cat_rows)
        total_is  = sum(safe_int(r[4]) for r in cat_rows)
        chart4 = []
        if total_is:
            chart4.append({"status": "In Stock", "count": total_is})
        if total_oos:
            chart4.append({"status": "Out of Stock", "count": total_oos})

        chart5 = [
            {"category": r[0], "out_of_stock": safe_int(r[3]), "in_stock": safe_int(r[4])}
            for r in cat_rows
        ]

        chart7 = sorted(
            [{"category": r[0], "revenue": safe_float(r[5])} for r in cat_rows],
            key=lambda x: x["revenue"], reverse=True
        )

        chart8 = sorted(
            [{"category": r[0], "count": safe_int(r[6])} for r in cat_rows],
            key=lambda x: x["count"], reverse=True
        )

        chart9 = sorted(
            [{"category": r[0], "avg_discount": safe_float(r[7])} for r in cat_rows],
            key=lambda x: x["avg_discount"], reverse=True
        )

        # ── Chart 1: Discount Histogram ────────────────────
        c1 = run_query(
            f"""SELECT FLOOR(discountpercent / 10) * 10 AS bucket, COUNT(*) AS cnt
                FROM zepto
                WHERE discountpercent IS NOT NULL AND {where}
                GROUP BY bucket ORDER BY bucket""",
            params
        )
        chart1 = [{"bucket": f"{int(r[0])}–{int(r[0])+10}%", "count": safe_int(r[1])} for r in c1]

        # ── Chart 3: Scatter MRP vs Discount ──────────────
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

        # ── Chart 11: Best / Worst Value per Gram (top 1 per category) ──
        c11_best = run_query(
            f"""SELECT DISTINCT ON (category) name, category,
                       ROUND((discountedsellingprice / NULLIF(weightingms, 0))::numeric, 4) AS ppg
                FROM zepto
                WHERE weightingms > 0 AND {where}
                ORDER BY category, discountedsellingprice / NULLIF(weightingms, 0) ASC""",
            params
        )
        chart11_best = [
            {"name": r[0], "category": r[1], "price_per_gram": safe_float(r[2])}
            for r in c11_best
        ]

        c11_worst = run_query(
            f"""SELECT DISTINCT ON (category) name, category,
                       ROUND((discountedsellingprice / NULLIF(weightingms, 0))::numeric, 4) AS ppg
                FROM zepto
                WHERE weightingms > 0 AND {where}
                ORDER BY category, discountedsellingprice / NULLIF(weightingms, 0) DESC""",
            params
        )
        chart11_worst = [
            {"name": r[0], "category": r[1], "price_per_gram": safe_float(r[2])}
            for r in c11_worst
        ]

        return jsonify({
            "kpis": {
                "total_skus":        safe_int(kpi_row[0]),
                "oos_pct":           safe_float(kpi_row[1]),
                "avg_discount":      safe_float(kpi_row[2]),
                "potential_revenue": safe_float(kpi_row[3]),
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