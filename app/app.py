from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

PORT_COLOR, BTC_COLOR = "#2a78d6", "#eb6834"
DATA_PATH = Path(__file__).parent.parent / "data" / "prices.csv"

st.set_page_config(page_title="Crypto Portfolio Risk Dashboard", layout="wide")
st.title("Crypto Portfolio Risk Dashboard")
st.write(
    "Does spreading money across 5 coins lower risk compared to holding only Bitcoin? "
    "Adjust the weights in the sidebar to test your own mix. Data: daily prices, "
    "Jan 2023 to Sep 2026, from Yahoo Finance."
)


@st.cache_data
def load_returns():
    prices = pd.read_csv(DATA_PATH, index_col=0, parse_dates=True).dropna()
    return prices.pct_change().dropna()


def risk_summary(daily_returns):
    value = 10000 * (1 + daily_returns).cumprod()
    drawdown = value / value.cummax() - 1
    return {
        "value": value,
        "drawdown": drawdown,
        "Total return": value.iloc[-1] / 10000 - 1,
        "Yearly volatility": daily_returns.std() * np.sqrt(365),
        "Max drawdown": drawdown.min(),
        "95% daily VaR": daily_returns.quantile(0.05),
    }


returns = load_returns()

# Sidebar: weights. Dividing by the total means the sliders don't need to add up to 100.
st.sidebar.header("Portfolio weights")
st.sidebar.caption("Sliders don't need to add up to 100. They're scaled automatically.")
defaults = {"BTC-USD": 40, "ETH-USD": 30, "SOL-USD": 15, "LINK-USD": 10, "AVAX-USD": 5}
raw = {coin: st.sidebar.slider(coin.replace("-USD", ""), 0, 100, start)
       for coin, start in defaults.items()}
if sum(raw.values()) == 0:
    st.warning("Set at least one weight above zero.")
    st.stop()
weights = pd.Series(raw) / sum(raw.values())
st.sidebar.write("**Actual weights used:**")
st.sidebar.write(" · ".join(f"{c.replace('-USD', '')} {w:.0%}" for c, w in weights.items()))

port = risk_summary((returns[weights.index] * weights).sum(axis=1))
btc = risk_summary(returns["BTC-USD"])

# Headline: answer the question first.
vol_gap = port["Yearly volatility"] - btc["Yearly volatility"]
if abs(vol_gap) < 0.005:
    st.subheader("This mix is about as volatile as Bitcoin alone.")
elif vol_gap < 0:
    st.subheader(f"This mix is less risky than Bitcoin alone: {-vol_gap:.1%} points lower yearly volatility.")
else:
    st.subheader(f"This mix is more risky than Bitcoin alone: {vol_gap:.1%} points higher yearly volatility.")

# Metrics, each compared to Bitcoin. "inverse" shows lower risk in green.
c1, c2, c3, c4 = st.columns(4)
c1.metric("Yearly volatility", f"{port['Yearly volatility']:.1%}",
          f"{vol_gap:+.1%} vs Bitcoin", delta_color="inverse")
c2.metric("Max drawdown", f"{port['Max drawdown']:.1%}",
          f"{port['Max drawdown'] - btc['Max drawdown']:+.1%} vs Bitcoin")
c3.metric("95% daily VaR", f"{port['95% daily VaR']:.1%}",
          f"{port['95% daily VaR'] - btc['95% daily VaR']:+.1%} vs Bitcoin")
c4.metric("Total return", f"{port['Total return']:.0%}",
          f"{port['Total return'] - btc['Total return']:+.0%} vs Bitcoin")
st.caption(
    "Max drawdown and VaR are negative numbers, so a positive difference (green) means "
    "smaller losses than Bitcoin. VaR: on 95% of days, the daily loss was smaller than this."
)

left, right = st.columns(2)
with left:
    st.markdown("**Growth of $10,000**")
    st.line_chart(pd.DataFrame({"Portfolio": port["value"], "Bitcoin only": btc["value"]}),
                  color=[PORT_COLOR, BTC_COLOR], y_label="Value ($)")
with right:
    st.markdown("**Drop from previous peak**")
    st.line_chart(pd.DataFrame({"Portfolio": port["drawdown"] * 100,
                                "Bitcoin only": btc["drawdown"] * 100}),
                  color=[PORT_COLOR, BTC_COLOR], y_label="Drawdown (%)")

with st.expander("Side-by-side numbers"):
    metrics = ["Total return", "Yearly volatility", "Max drawdown", "95% daily VaR"]
    table = pd.DataFrame({"Portfolio": [port[m] for m in metrics],
                          "Bitcoin only": [btc[m] for m in metrics]}, index=metrics)
    st.dataframe(table.style.format("{:.1%}"))

st.caption(
    "Limits: assumes the portfolio is rebalanced to target weights every day, ignores "
    "trading fees, and starts in Jan 2023 near a market bottom. Past risk doesn't predict future risk."
)
