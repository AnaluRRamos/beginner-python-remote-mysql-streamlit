
import pymysql
import pandas as pd
import plotly.express as px
import streamlit as st
from datetime import date

def connect_mysql(host, port, user, password, db, ca_path=""):
    ssl_args = {"ca": ca_path} if ca_path else None
    return pymysql.connect(
        host=host,
        port=int(port),
        user=user,
        password=password,
        database=db,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        ssl=ssl_args,
        connect_timeout=10,
    )

@st.cache_data(show_spinner=False, ttl=60)
def get_min_max_dates(params):
    with connect_mysql(**params) as con, con.cursor() as cur:
        cur.execute("SELECT MIN(`date`), MAX(`date`) FROM yahoo_data;")
        mn, mx = cur.fetchone().values()
    return mn, mx

@st.cache_data(show_spinner=False, ttl=60)
def get_distinct_tickers(params):
    # Only if the column exists
    with connect_mysql(**params) as con:
        df = pd.read_sql("SELECT * FROM yahoo_data LIMIT 1", con)
    if "ticker" in df.columns:
        with connect_mysql(**params) as con:
            tdf = pd.read_sql("SELECT DISTINCT ticker FROM yahoo_data ORDER BY ticker", con)
        return sorted(tdf["ticker"].dropna().astype(str).tolist())
    return []

@st.cache_data(show_spinner=False, ttl=60)
def fetch_data(params, start, end, tickers=None):
    where = "WHERE `date` BETWEEN %s AND %s"
    args = [start, end]
    if tickers:
        placeholders = ",".join(["%s"] * len(tickers))
        where += f" AND ticker IN ({placeholders})"
        args.extend(tickers)
    cols = "`date`,`open`,`high`,`low`,`close`,`adj_close`,`volume`"
    sel = f"SELECT {cols}" + (", ticker" if tickers is not None else "") + f" FROM yahoo_data {where} ORDER BY `date`"
    with connect_mysql(**params) as con:
        df = pd.read_sql(sel, con, params=args)
    # Make sure numbers are numeric and date is datetime
    for c in ["open","high","low","close","adj_close","volume"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df

st.set_page_config(page_title="Finance Dashboard", layout="wide")
st.title("📈 Finance Dashboard — `yahoo_data`")

with st.sidebar:
    st.subheader("Database connection")
    host = st.text_input("Host", "")
    port = st.number_input("Port", value=3306, step=1)
    user = st.text_input("User", "")
    password = st.text_input("Password", type="password")
    db = st.text_input("Database", "finance")
    ca_path = st.text_input("CA certificate path (optional, Aiven)")

    connect_clicked = st.button("Connect")

if "conn_params" not in st.session_state and connect_clicked:
    try:
        # sanity check
        with connect_mysql(host, port, user, password, db, ca_path) as con, con.cursor() as cur:
            cur.execute("SELECT 1")
        st.session_state.conn_params = dict(host=host, port=port, user=user, password=password, db=db, ca_path=ca_path)
        st.success("Connected!")
    except Exception as e:
        st.error(f"Connection failed: {e}")

if "conn_params" in st.session_state:
    params = st.session_state.conn_params

    # Date range
    try:
        mn, mx = get_min_max_dates(params)
    except Exception as e:
        st.error(f"Could not read date range from `yahoo_data`: {e}")
        st.stop()

    if not mn or not mx:
        st.warning("Table `yahoo_data` has no rows yet.")
        st.stop()

    c1, c2, c3 = st.columns([2,2,1])
    with c1:
        start = st.date_input("Start date", value=mn or date.today(), min_value=mn or date(2000,1,1), max_value=mx or date.today())
    with c2:
        end = st.date_input("End date", value=mx or date.today(), min_value=mn or date(2000,1,1), max_value=mx or date.today())

    # Optional ticker filter
    tickers = get_distinct_tickers(params)
    chosen_tickers = None
    if tickers:
        with c3:
            chosen = st.multiselect("Tickers", options=tickers, default=tickers[:1])
            chosen_tickers = chosen if chosen else None

    # Column to plot
    y_options = ["adj_close", "close"]
    y_col = st.selectbox("Price column", options=[c for c in y_options if c in ["adj_close","close"]], index=0)

    # Frequency
    freq = st.selectbox("Frequency", options=["Daily","Weekly","Monthly"], index=0)

    # Fetch & transform
    if start > end:
        st.error("Start date must be before end date.")
        st.stop()

    df = fetch_data(params, start, end, tickers=chosen_tickers)
    if df.empty:
        st.warning("No data for the selected filters.")
        st.stop()

    # Resample
    rule = {"Daily":"D","Weekly":"W","Monthly":"MS"}[freq]
    df = df.set_index("date")
    if chosen_tickers and "ticker" in df.columns:
        grouped = (df.groupby("ticker")
                     .resample(rule)
                     .agg({y_col:"mean","volume":"sum"})
                     .reset_index())
    else:
        grouped = (df.resample(rule)
                     .agg({y_col:"mean","volume":"sum"})
                     .reset_index())

    # Charts
    st.subheader("Price")
    if "ticker" in grouped.columns:
        fig = px.line(grouped, x="date", y=y_col, color="ticker", title=f"{y_col.replace('_',' ').title()} over time")
    else:
        fig = px.line(grouped, x="date", y=y_col, title=f"{y_col.replace('_',' ').title()} over time")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Volume")
    if "ticker" in grouped.columns:
        fig2 = px.bar(grouped, x="date", y="volume", color="ticker", title="Volume")
    else:
        fig2 = px.bar(grouped, x="date", y="volume", title="Volume")
    st.plotly_chart(fig2, use_container_width=True)

    st.download_button("Download filtered CSV", grouped.to_csv(index=False).encode("utf-8"), file_name="yahoo_data_filtered.csv", mime="text/csv")
else:
    st.info("Enter your DB credentials in the sidebar and click **Connect** to begin.")
