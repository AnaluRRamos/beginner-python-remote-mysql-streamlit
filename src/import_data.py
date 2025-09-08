import sys
import os
import csv
from datetime import datetime

import pandas as pd  # requires: pip install pandas openpyxl
from connect_mysql import connect   # your connector that prompts for host/port/etc.

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS yahoo_data (
  id INT AUTO_INCREMENT PRIMARY KEY,
  `date` DATE NOT NULL,
  `open` DECIMAL(18,4) NULL,
  `high` DECIMAL(18,4) NULL,
  `low`  DECIMAL(18,4) NULL,
  `close` DECIMAL(18,4) NULL,
  `adj_close` DECIMAL(18,4) NULL,
  `volume` BIGINT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

INSERT_SQL = """
INSERT INTO yahoo_data (`date`,`open`,`high`,`low`,`close`,`adj_close`,`volume`)
VALUES (%s,%s,%s,%s,%s,%s,%s)
"""

def _to_date(s):
    if not s:
        return None
    s = str(s).strip()
    for fmt in ("%Y-%m-%d", "%b %d, %Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(s.split()[0]).date()
    except Exception:
        return None

def _to_float(s):
    if s is None:
        return None
    s = str(s).strip().replace("\u00A0", "").replace(" ", "")
    if "," in s and "." not in s:          # 33.795,70 -> 33795.70
        s = s.replace(".", "").replace(",", ".")
    else:                                   # 33,795.70 or 33795.70
        s = s.replace(",", "")
    return float(s) if s != "" else None

def _to_int(s):
    if s is None:
        return None
    s = str(s).strip().replace("\u00A0", "").replace(" ", "").replace(",", "")
    if s == "":
        return None
    try:
        return int(s)
    except ValueError:
        try:
            return int(float(s))
        except Exception:
            return None

def _insert_rows(cur, con, rows_iter, batch_size=500):
    batch = []
    total = 0
    for row in rows_iter:
        # row can be a dict (CSV) or a pandas Series (Excel). Series has .get().
        get = row.get if hasattr(row, "get") else row.__getitem__
        d = _to_date(get("Date", None) if hasattr(row, "get") else row.get("Date") or row.get("date"))
        if not d:
            d = _to_date(get("date") if hasattr(row, "get") else row.get("date"))
        o = _to_float(get("Open", None) if hasattr(row, "get") else row.get("Open"))
        h = _to_float(get("High", None) if hasattr(row, "get") else row.get("High"))
        l = _to_float(get("Low", None)  if hasattr(row, "get") else row.get("Low"))
        c = _to_float(get("Close", None) if hasattr(row, "get") else row.get("Close"))
        a = _to_float(
            (get("Adj Close", None) if hasattr(row, "get") else row.get("Adj Close"))
            or (get("AdjClose", None) if hasattr(row, "get") else row.get("AdjClose"))
            or (get("adj_close", None) if hasattr(row, "get") else row.get("adj_close"))
        )
        v = _to_int(get("Volume", None) if hasattr(row, "get") else row.get("Volume"))

        if not d:
            continue  # skip rows without a valid date

        batch.append((d, o, h, l, c, a, v))
        total += 1

        if len(batch) >= batch_size:
            cur.executemany(INSERT_SQL, batch)
            con.commit()
            print(f"Inserted {total} rows so far...")
            batch = []

    if batch:
        cur.executemany(INSERT_SQL, batch)
        con.commit()
    return total

def main(path_in):
    con = connect()
    cur = con.cursor()

    print("Creating table `yahoo_data` (if not exists)...")
    cur.execute(CREATE_SQL)
    con.commit()
    print("Table ready.")

    ext = os.path.splitext(path_in)[1].lower()
    print(f"Opening file: {path_in}")

    if ext in [".xlsx", ".xls"]:
        # Excel
        df = pd.read_excel(path_in, sheet_name=0)
        # Normalize headers (remove '*', trim extra spaces)
        df.columns = [(str(c).replace("*", "").strip() if isinstance(c, str) else c) for c in df.columns]
        total = _insert_rows(cur, con, (row for _, row in df.iterrows()))
    else:
        # CSV: try UTF-8, fall back to latin-1 if needed
        try:
            with open(path_in, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                if reader.fieldnames:
                    reader.fieldnames = [c.replace("*", "") if c else c for c in reader.fieldnames]
                total = _insert_rows(cur, con, reader)
        except UnicodeDecodeError:
            with open(path_in, newline="", encoding="latin-1") as f:
                reader = csv.DictReader(f)
                if reader.fieldnames:
                    reader.fieldnames = [c.replace("*", "") if c else c for c in reader.fieldnames]
                total = _insert_rows(cur, con, reader)

    cur.close()
    con.close()
    print(f"✅ Import finished!!! Total rows: {total}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python src/import_data.py data/yahoo_data.xlsx  (or .csv)")
        sys.exit(1)
    main(sys.argv[1])
