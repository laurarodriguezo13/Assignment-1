from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from stock import Stock

# ---------------------------------------------------------------
# Page config
# ---------------------------------------------------------------
st.set_page_config(page_title="Stock analysis", page_icon="📈", layout="wide")

st.title("Stock analysis")
st.caption("Assignment 1 — built on top of the Stock class")


# ---------------------------------------------------------------
# Cached data fetch: creating a Stock IS the fetch, so the cached
# function creates and returns the Stock object. Same arguments →
# cached object, no re-download on widget interaction.
# ---------------------------------------------------------------
@st.cache_data(ttl="1h", show_spinner=False)
def load_stock(symbol: str, start: date, end: date, ma_window: int, ma_window2: int) -> Stock:
    return Stock(symbol, start=start, end=end, ma_window=ma_window, ma_window2=ma_window2)


# ---------------------------------------------------------------
# Sidebar (shared by both tabs)
# ---------------------------------------------------------------
with st.sidebar:
    st.header("Inputs")
    ticker = st.text_input("Ticker symbol", value="AAPL")
    start = st.date_input(
        "Start date",
        value=date.today() - timedelta(days=365),
        max_value=date.today(),
    )
    end = st.date_input("End date", value=date.today(), max_value=date.today())
    ma_short = st.slider("Short moving average window (days)", 5, 200, 10)
    ma_long = st.slider("Long moving average window (days)", 5, 200, 50)
    fetch = st.button("Fetch data", type="primary", width="stretch")

if start >= end:
    st.error("Start date must be before end date.")
    st.stop()

# The button is only True on the click's rerun; remember that data was
# requested so the app keeps rendering on later widget interactions.
if fetch:
    st.session_state["fetched"] = True

tab1, tab2 = st.tabs(["Single stock analysis", "Portfolio comparison"])

# ---------------------------------------------------------------
# Tab 1 — Single stock analysis
# ---------------------------------------------------------------
with tab1:
    if not st.session_state.get("fetched"):
        st.info("Set your inputs in the sidebar and press **Fetch data**.")
    else:
        with st.spinner(f"Fetching {ticker}..."):
            stock = load_stock(ticker, start, end, ma_short, ma_long)

        if stock.data is None:
            st.error(stock.message)
        else:
            st.success(stock.message)
            data = stock.data

            # --- Metrics ---
            last_close = data["Close"].iloc[-1]
            cum_return = data["return"].sum()
            change_today = data["change"].iloc[-1]
            col1, col2, col3 = st.columns(3)
            col1.metric("Last close", f"${last_close:,.2f}", f"{change_today:+.2f}")
            col2.metric("Cumulative return", f"{cum_return:.2%}")
            col3.metric("Trading days", f"{len(data)}")

            # --- Price + moving averages (built here from stock.data) ---
            st.subheader(f"{stock.symbol} close price and moving averages")
            price_fig = px.line(
                data,
                x=data.index,
                y=["Close", "MA", "MA2"],
                labels={"x": "Date", "value": "Price ($)", "variable": "Series"},
            )
            new_names = {
                "Close": "Close",
                "MA": f"MA ({ma_short}d)",
                "MA2": f"MA ({ma_long}d)",
            }
            price_fig.for_each_trace(lambda t: t.update(name=new_names[t.name]))
            st.plotly_chart(price_fig, width="stretch")

            # --- Charts produced by the class ---
            left, right = st.columns(2)
            with left:
                st.plotly_chart(stock.plot_performance(), width="stretch")
            with right:
                st.plotly_chart(stock.plot_return_dist(), width="stretch")

            # --- Summary statistics for the return column ---
            st.subheader("Daily return summary statistics")
            st.dataframe(data["return"].describe().to_frame("return"), width="content")

# ---------------------------------------------------------------
# Tab 2 — Portfolio comparison
# ---------------------------------------------------------------
with tab2:
    symbols_text = st.text_input(
        "Ticker symbols (comma-separated)", value="AAPL, MSFT, GOOG"
    )
    symbols = [s.strip().upper() for s in symbols_text.split(",") if s.strip()]

    if not st.session_state.get("fetched"):
        st.info("Press **Fetch data** in the sidebar to load the comparison.")
    elif not symbols:
        st.warning("Enter at least one ticker symbol.")
    else:
        lines = []
        with st.spinner(f"Fetching {', '.join(symbols)}..."):
            for symbol in symbols:
                s = load_stock(symbol, start, end, ma_short, ma_long)
                if s.data is None:
                    st.error(s.message)
                    continue
                # Zero-based cumulative performance: cumulative sum of the
                # return column, shifted so every line starts at exactly 0.0
                cumulative = s.data["return"].cumsum()
                cumulative = cumulative - cumulative.iloc[0]
                lines.append(
                    pd.DataFrame(
                        {
                            "Date": s.data.index,
                            "Cumulative return": cumulative.values,
                            "Ticker": s.symbol,
                        }
                    )
                )

        if not lines:
            st.warning("No data could be loaded for any of the tickers above.")
        else:
            combined = pd.concat(lines, ignore_index=True)
            fig = px.line(
                combined,
                x="Date",
                y="Cumulative return",
                color="Ticker",
                title="Zero-based cumulative performance",
            )
            st.plotly_chart(fig, width="stretch")
