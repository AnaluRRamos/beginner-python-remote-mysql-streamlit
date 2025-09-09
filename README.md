
# Remote Database + MySQL + Yahoo Finance Pipeline (Beginner‑Friendly)

Build a tiny end‑to‑end pipeline that goes from a spreadsheet to a remote MySQL database on **Aiven** and then into a **Streamlit** dashboard, with credentials prompted at runtime (nothing sensitive hard‑coded).

---

## What you’ll build ??

* A remote **MySQL** database on Aiven (database name: `finance`) with a table `yahoo_data`
* An interactive Python connector that prompts for DB details — `src/connect_mysql.py`
* A tiny importer that reads **.xlsx** or **.csv** and batch‑inserts into MySQL — `src/import_data.py`
* A simple **Streamlit** dashboard to explore price and volume — `src/dashboard_app.py`

---

## Prerequisites

* **MySQL Workbench** ( helpful to verify connections)
* An **Aiven MySQL service** (host, port, user, password; we’ll create the `finance` DB)
* **Python 3.9+** and this project’s dependencies

Install the project requirements (from the file you already have):

```bash
pip install -r requirements.txt
```

**Why**: using `requirements.txt` guarantees everyone installs the same packages with one command.

---

## Project structure

A minimal layout that keeps things tidy:

```
.
├─ requirements.txt
├─ data/
│  └─ yahoo_data.xlsx         # or yahoo_data.csv
├─ src/
│  ├─ connect_mysql.py        # prompts for credentials and tests the connection
│  ├─ import_data.py          # reads CSV/XLSX and inserts into MySQL in batches
│  └─ dashboard_app.py        # Streamlit app to visualise Adj Close & Volume
└─ README.md
```

The data can be found: https://www.kaggle.com/datasets/suruchiarora/yahoo-finance-dataset-2018-2023/data


## 1) Create a connection in MySQL Workbench (remote)

**Why**: a visual test that your database is reachable (especially with SSL).

1. Open **MySQL Workbench** → *MySQL Connections* → **+** (add connection).
2. Fill in your Aiven **host** and **port** (Aiven often uses a non‑`3306` port).
3. In the **SSL** tab, enable SSL and select your **CA certificate** (if required by your service).
4. Click **Test Connection** → **OK**.

> If you prefer to skip Workbench, you can go straight to **Step 3** (the Python connection test).

---

## 2) Create the database (remote, on Aiven)

**Why**: you need a database to hold your table.

In Workbench (or any MySQL client), run:

```sql
CREATE DATABASE IF NOT EXISTS finance
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_0900_ai_ci;

USE finance;
```

> On Aiven, user creation may be restricted on some plans. Use the credentials Aiven gives you.

---

## 3) Verify the Python connection (prints ✅ on success)

**Why**: confirms your scripts can reach the remote DB before importing data.

Run:

```bash
python src/connect_mysql.py
```

**What happens**:
The script prompts you for host, port, user, password, database (`finance`), and (optionally) a CA path. On success, you’ll see a ✅ message (and SSL info if applicable).

So we have: 

Interactive connector for Aiven MySQL.
Prompts for credentials at runtime and prints a ✅ on success.
Nothing sensitive is stored in code or on disk.

---

## 4) Import your Yahoo Finance data into MySQL

**Why**: loads your spreadsheet (Excel or CSV) into a proper SQL table you can query and visualise.

Place your file here:

```
data/yahoo_data.xlsx   # or data/yahoo_data.csv
```

Run the importer:

```bash
# Excel
python src/import_data.py data/yahoo_data.xlsx

# OR CSV
# python src/import_data.py data/yahoo_data.csv
```

**What it does**:

* Prompts for your DB connection (again, nothing stored)
* Ensures table `yahoo_data` exists in the `finance` database
* Expects typical columns: `Date, Open, High, Low, Close, Adj Close, Volume`
* Handles small header variations (e.g., `Adj Close*`) and comma‑decimal numbers
* Inserts rows in batches and prints progress


---

## 5) Visualise the data

**Why**: quickly see trends without writing query code in a notebook.

### Streamlit dashboard 

Run the app:

```bash
streamlit run src/dashboard_app.py
```

* In the **left sidebar**, enter your Aiven host/port/user/password/database and (if needed) CA path.
* Click **Connect**, choose a **date range**, and view **Adj Close** and **Volume** charts.
* You can also **download** the filtered data as CSV from the app.


## Notes & troubleshooting

* **Wrong file format**: If you pass `.xlsx` to a CSV‑only tool you’ll see a Unicode error. This importer supports both `.xlsx` and `.csv`.
* **Access denied / Unknown database**: Re‑check the database name you type (`finance`). If it doesn’t exist, create it in **Step 2**.
* **Port mismatch**: Aiven often uses a non‑`3306` port. Use the exact port shown for your service.
* **IP allowlist**: If you enabled an allowlist on Aiven, add your current IP so you can connect.

---

## Security note

* All scripts **prompt** for credentials at runtime; nothing sensitive is committed to code.
* Prefer using **read‑only users** for dashboards when possible.

---

Happy building! 🎉 :)
