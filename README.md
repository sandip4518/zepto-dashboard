# Zepto Dashboard

A Flask-based inventory analytics dashboard for Zepto product data.

## Overview

This project provides a responsive dashboard to explore Zepto catalog data, including inventory health, discount distribution, pricing trends, and category analytics.

The frontend is served from `templates/dashboard.html` and `static/dashboard.js`, while the backend API is implemented in `app.py`. PostgreSQL is used as the data store via `db.py`.

## Features

- Interactive filters for categories, stock status, MRP, discount, weight, and text search
- KPI cards for total SKUs, out-of-stock percentage, average discount, and potential revenue
- Discount distribution histogram
- Category pricing comparison (MRP vs discounted selling price)
- MRP vs discount scatter plot
- Stock availability analysis
- Live frontend refresh and SQL-driven analytics

## Getting Started

### Prerequisites

- Python 3.8+ installed
- PostgreSQL database available
- `pip` package manager

### Install dependencies

```bash
pip install -r requirements.txt
```

### Database configuration

Create a `.env` file in the project root with your PostgreSQL connection settings:

```env
DB_HOST=localhost
DB_NAME=zepto_SQL_Analysis
DB_USER=postgres
DB_PASS=your_password
DB_PORT=5432
```

The app loads these values via `python-dotenv` in `db.py`.

### Load data

Place or import your Zepto dataset into the `zepto` table in the configured PostgreSQL database. The dashboard expects columns such as:

- `sku_id`
- `name`
- `category`
- `mrp`
- `discountpercent`
- `discountedsellingprice`
- `availablequantity`
- `outofstock`
- `weightingms`

The `sql/` directory contains queries and schema files that can help with analysis and dataset preparation.

### Run the app

From the project root:

```bash
python app.py
```

Then open `http://127.0.0.1:5000/` in your browser.

## Project Structure

- `app.py` - Flask application and API endpoints
- `db.py` - PostgreSQL connection helper
- `templates/dashboard.html` - HTML dashboard layout
- `static/dashboard.js` - frontend logic, filters, and Chart.js configuration
- `static/style.css` - dashboard styling
- `requirements.txt` - Python dependencies
- `sql/` - SQL queries and schema scripts

## Notes

- The app uses Chart.js for charts and frontend visualizations.
- Filter and data requests are handled through `/api/init` and `/api/data`.
- Adjust the database connection settings and dataset schema to match your local environment.

## Troubleshooting

- If data does not load, verify PostgreSQL connectivity and the `zepto` table schema.
- If the dashboard fails to start, ensure dependencies are installed and Flask is available.
- For SQL debugging, inspect the routes in `app.py` and database helper logic in `db.py`.
