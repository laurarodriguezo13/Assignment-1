from datetime import date, timedelta

import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px

# ---------------------------------------------------------------
# Page config
# ---------------------------------------------------------------
st.set_page_config(page_title="Stock dashboard", page_icon="📈", layout="wide")

st.title("Stock dashboard")
st.caption("Modified demo — second moving average added directly in the script")


# ---------------------------------------------------------------
# Data loading (cached)
# ---------------------------------------------------------------
@st.cache_data(ttl="1h")
def get_stock_data(ticker: str, start_date: date, end_date: date) -> pd.DataFrame:
    """Download historical price data for a ticker from Yahoo Finance."""
    stock = yf.Ticker(ticker)
    df = stock.history(start=start_date, end=end_date)
    return df


# ---------------------------------------------------------------
# Sidebar inputs
# ---------------------------------------------------------------
with st.sidebar:
    st.header("Inputs")
    ticker = st.text_input("Main ticker", value="AAPL")
    comparison_ticker = st.text_input("Comparison ticker", value="SPY")
    start = st.date_input(
        "Start date",
        value=date.today() - timedelta(days=365),
        max_value=date.today(),
    )
    end = st.date_input(
        "End date",
        value=date.today(),
        max_value=date.today(),
    )
    # NEW: two moving-average windows, each with its own slider
    ma_short = st.slider("Short moving average (days)", 5, 200, 10)
    ma_long = st.slider("Long moving average (days)", 5, 200, 50)
    run_button = st.button("Run", type="primary", width="stretch")

if start >= end:
    st.error("Start date must be before end date.")
    st.stop()


# ---------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------
if run_button:
    # Fetch data for both tickers using the cached function
    df = get_stock_data(ticker, start, end)
    comparison_df = get_stock_data(comparison_ticker, start, end)

    if df.empty:
        st.error(f"No data found for ticker '{ticker}'. Please check the symbol.")
        st.stop()
    if comparison_df.empty:
        st.error(f"No data found for ticker '{comparison_ticker}'. Please check the symbol.")
        st.stop()

    # -----------------------------------------------------------
    # Calculations done directly in the script
    # -----------------------------------------------------------
    df["pct_chg"] = df["Close"].pct_change()
    df["normalized_close"] = (df["Close"] / df["Close"].iloc[0]) * 100
    comparison_df["normalized_close"] = (comparison_df["Close"] / comparison_df["Close"].iloc[0]) * 100

    # NEW: both moving averages calculated inline
    df["MA_short"] = df["Close"].rolling(ma_short).mean()
    df["MA_long"] = df["Close"].rolling(ma_long).mean()

    # -----------------------------------------------------------
    # Create tabs
    # -----------------------------------------------------------
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Chart", "📄 Data", "📋 Statistics", "📈 Comparison"])

    with tab1:
        st.subheader(f"{ticker} closing price")
        col1, col2, col3 = st.columns(3)
        col1.metric("Last Price", f"{df.Close.iloc[-1]:.2f}")
        col2.metric("Cum Change", f"{df.Close.iloc[-1] / df.Close.iloc[0] - 1:.2%}")
        col3.metric("Trading Days", f"{df.Close.count()}")

        # NEW: Plotly chart with Close and both moving averages
        price_fig = px.line(
            df,
            x=df.index,
            y=["Close", "MA_short", "MA_long"],
            labels={"x": "Date", "value": "Price ($)", "variable": "Series"},
            title=f"{ticker} close with {ma_short}d and {ma_long}d moving averages",
        )
        rename = {
            "Close": "Close",
            "MA_short": f"MA ({ma_short}d)",
            "MA_long": f"MA ({ma_long}d)",
        }
        price_fig.for_each_trace(lambda t: t.update(name=rename[t.name]))
        st.plotly_chart(price_fig, width="stretch")

    with tab2:
        st.subheader(f"{ticker} Summary statistics")
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Daily Change Stats**")
            summary = df["pct_chg"].describe()
            st.dataframe(summary)
        with col2:
            price_stats = pd.DataFrame({
                "Metric": ["High", "Low", "Mean", "Volatility"],
                "Values": [
                    f"{df.Close.max():.2f}",
                    f"{df.Close.min():.2f}",
                    f"{df.Close.mean():.2f}",
                    f"{df.Close.std():.2f}",
                ]
            })
            st.dataframe(price_stats)

        st.dataframe(df, width="stretch")

    with tab3:
        st.subheader(f"{ticker} summary statistics")
        st.dataframe(df.describe(), width="stretch")

    with tab4:
        st.subheader("Normalized performance comparison")

        # Combine both normalized series into one long-format DataFrame for plotly
        combined = pd.concat(
            [
                pd.DataFrame(
                    {
                        "Date": df.index,
                        "Normalized close": df["normalized_close"].values,
                        "Ticker": ticker,
                    }
                ),
                pd.DataFrame(
                    {
                        "Date": comparison_df.index,
                        "Normalized close": comparison_df["normalized_close"].values,
                        "Ticker": comparison_ticker,
                    }
                ),
            ],
            ignore_index=True,
        )

        fig = px.line(
            combined,
            x="Date",
            y="Normalized close",
            color="Ticker",
            title=f"{ticker} vs {comparison_ticker} Performance (Base 100)",
        )
        st.plotly_chart(fig, width="stretch")

        # Summary statistics for the normalized data
        st.subheader("Summary statistics (base 100)")
        summary = pd.DataFrame(
            {
                "Min": [
                    df["normalized_close"].min(),
                    comparison_df["normalized_close"].min(),
                ],
                "Max": [
                    df["normalized_close"].max(),
                    comparison_df["normalized_close"].max(),
                ],
                "Final normalized value": [
                    df["normalized_close"].iloc[-1],
                    comparison_df["normalized_close"].iloc[-1],
                ],
            },
            index=[ticker, comparison_ticker],
        )
        st.dataframe(summary.round(2), width="stretch")
else:
    st.info("Enter your tickers in the sidebar and press **Run** to load the dashboard.")
