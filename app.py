import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy.interpolate import CubicSpline

# Configure page
st.set_page_config(page_title="Treasury Yield Bootstrapping", layout="wide", page_icon="📈")
st.title("💸 US Treasury Yield Curve Bootstrapping")

st.markdown("""
This application fetches the latest US Treasury **yield curve** and bootstraps the quoted *Par Yields* to derive the theoretical **Spot Rates** (zero-coupon yield curve), illustrating that standard coupon bonds can be priced perfectly using zero-coupon discount factors.
""")

with st.expander("📚 Sources & Methodology FAQs"):
    st.markdown("""
    - **Yield Curve Data Source:** [Daily Treasury Yield Curve Rates](https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_yield_curve&field_tdr_date_value=202603)
    - **Methodology FAQ:** [Treasury Interest Rates FAQ](https://home.treasury.gov/policy-issues/financing-the-government/interest-rate-statistics/interest-rates-frequently-asked-questions)
      - The Treasury quotes constant maturity yields on a **bond-equivalent basis** (assuming semiannual compounding), not an effective annual yield (APY).
      - *All* points on the yield curve, even short-term maturities (under 1 year), are mathematically treated as equivalent to semiannual coupon bonds to maintain yield consistency.
      - We interpolate the par yield curve using **Cubic Splines** to populate every 6-month period, then sequentially bootstrap out to 30 years.
    """)

with st.sidebar:
    st.header("⚙️ Configuration")
    
    st.subheader("Data Source")
    data_source = st.radio("Select Source", ["Treasury Website", "Manual Input"])
    
    period = "202603" # default
    if data_source == "Treasury Website":
        st.subheader("Data Selection")
        year = st.selectbox("Year", options=range(2026, 1989, -1), index=0)
        month = st.selectbox("Month", options=range(1, 13), index=2)
        period = f"{year}{month:02d}"

@st.cache_data(ttl=3600)
def load_treasury_data(period_str):
    url = f"https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_yield_curve&field_tdr_date_value={period_str}"
    # Using pandas read_html to scrape the data table directly
    tables = pd.read_html(url)
    df = tables[0]
    return df

st.header("1. Latest Par Yield Data")

maturities_dict = {
    '1 Mo': 1/12, '2 Mo': 2/12, '3 Mo': 3/12, '4 Mo': 4/12,
    '6 Mo': 0.5, '1 Yr': 1.0, '2 Yr': 2.0, '3 Yr': 3.0,
    '5 Yr': 5.0, '7 Yr': 7.0, '10 Yr': 10.0, '20 Yr': 20.0, '30 Yr': 30.0
}

terms = []
par_yields = []

if data_source == "Treasury Website":
    try:
        with st.spinner("Fetching data from Treasury.gov..."):
            df_raw = load_treasury_data(period)
            
        valid_dates = df_raw['Date'].tolist()
        selected_date = st.sidebar.selectbox("Quote Date", options=valid_dates, index=len(valid_dates)-1)
        
        st.sidebar.subheader("Illustration Settings")
        proof_maturity = st.sidebar.selectbox("Proof Bond Maturity (Years)", options=[2, 3, 5, 7, 10, 20, 30], index=6)
        
        latest_row = df_raw[df_raw['Date'] == selected_date].iloc[0].to_dict()
        date_val = latest_row.get('Date', 'Latest')
        st.write(f"**Data Date:** `{date_val}`")
        
        for k, t in maturities_dict.items():
            if k in latest_row and pd.notna(latest_row[k]):
                terms.append(t)
                par_yields.append(float(latest_row[k]) / 100.0) # convert % to decimal
                
        terms = np.array(terms)
        par_yields = np.array(par_yields)
        
        # Display table horizontally
        display_df = pd.DataFrame({"Maturity (Years)": terms, "Par Yield (%)": par_yields * 100}).T
        display_df.columns = [list(maturities_dict.keys())[i] for i in range(len(terms))]
        st.dataframe(display_df)
        
    except Exception as e:
        st.error(f"Failed to fetch Treasury data. Error: {e}")
        st.stop()
else:
    st.sidebar.subheader("Illustration Settings")
    proof_maturity = st.sidebar.selectbox("Proof Bond Maturity (Years)", options=[2, 3, 5, 7, 10, 20, 30], index=6)

    st.write("**Data Date:** `Custom Input`")
    st.write("Edit the values in the table below to define your custom par yield curve (in %):")
    
    default_yields = {
        '1 Mo': 5.30, '2 Mo': 5.35, '3 Mo': 5.40, '4 Mo': 5.42,
        '6 Mo': 5.35, '1 Yr': 5.00, '2 Yr': 4.60, '3 Yr': 4.40,
        '5 Yr': 4.20, '7 Yr': 4.25, '10 Yr': 4.30, '20 Yr': 4.50, '30 Yr': 4.45
    }
    
    df_manual = pd.DataFrame([default_yields])
    edited_df = st.data_editor(df_manual, hide_index=True)
    
    manual_row = edited_df.iloc[0].to_dict()
    for k, t in maturities_dict.items():
        if k in manual_row:
            terms.append(t)
            par_yields.append(float(manual_row[k]) / 100.0)
            
    terms = np.array(terms)
    par_yields = np.array(par_yields)
    
st.header("2. Bootstrapping the Yield Curve")

st.markdown("""
A par yield assumes an instrument trading exactly at its face value ($100). The price is exactly equal to the sum of discounted cash flows. By starting at the shortest maturity and working forward sequentially, we mathematically isolate the **Spot Rate** $z_t$ for each semiannual period.

$$ 100 = \sum_{i=0.5}^{t} \\frac{100 \\times \\frac{Y_t}{2}}{(1 + \\frac{z_i}{2})^{2i}} + \\frac{100}{(1 + \\frac{z_t}{2})^{2t}} $$
""")

# Interpolate using Cubic Spline
cs = CubicSpline(terms, par_yields)

# Create an array of periods from 0.5 to 30.0 (steps of 0.5)
periods = np.arange(0.5, 30.5, 0.5)
interp_par_yields = cs(periods)

# Sequential Bootstrapping to find spot rates
spot_rates = []
for t_idx, t in enumerate(periods):
    Y_t = interp_par_yields[t_idx]
    coupon = 100 * Y_t / 2
    
    pv_coupons = 0
    for i in range(t_idx):
        pv_coupons += coupon / ((1 + spot_rates[i]/2)**(2 * periods[i]))
        
    # Solve for z_t
    z_t = 2 * (((coupon + 100) / (100 - pv_coupons))**(1 / (2 * t)) - 1)
    spot_rates.append(z_t)

spot_rates = np.array(spot_rates)

col1, col2 = st.columns([2, 1])

with col1:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=periods, y=interp_par_yields*100, mode='lines', name='Interpolated Par Yield', line=dict(color='blue', dash='dash')))
    fig.add_trace(go.Scatter(x=periods, y=spot_rates*100, mode='lines', name='Bootstrapped Spot Yield', line=dict(color='red')))
    fig.add_trace(go.Scatter(x=terms, y=par_yields*100, mode='markers', name='Actual Quotes', marker=dict(color='black', size=8, symbol='x')))
    
    fig.update_layout(
        title="Par Yield Curve vs Spot Rate Curve",
        xaxis_title="Maturity (Years)",
        yaxis_title="Implied Yield (%)",
        template="plotly_white",
        legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99)
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.write("### Spot Rates Table")
    spot_df = pd.DataFrame({
        "Maturity (Yr)": periods,
        "Par Yield (%)": interp_par_yields * 100,
        "Spot Rate (%)": spot_rates * 100
    })
    st.dataframe(spot_df.style.format("{:.3f}"), height=400)


st.header(f"3. Proof of Equivalence: The {proof_maturity}-Year Bond")

st.markdown(f"""
The fundamental mechanics of fixed income state that discounting a bond's cash flows at its single implied yield (Par Yield) mathematically equals discounting each *individual* cash flow at the theoretical Zero-Coupon curve (Spot Rates). Let's take the **{proof_maturity}-Year** point as an example.
""")

target_idx = np.where(periods == proof_maturity)[0][0]
par_target = interp_par_yields[target_idx]
coupon_target = 100 * par_target / 2
num_periods = int(proof_maturity * 2)
proof_periods = periods[:num_periods]

st.info(f"**{proof_maturity}-Year Interpolated Par Yield:** {par_target*100:.4f}% | **Semiannual Coupon:** ${coupon_target:.4f}")

# Precompute the cash flows and PVs
proof_data = []
pv_a = 0
pv_b = 0

for i, t in enumerate(proof_periods):
    cf = coupon_target + (100 if i == len(proof_periods)-1 else 0)
    
    # Method A
    df_a = 1 / ((1 + par_target/2)**(2*t))
    pv_a_step = cf * df_a
    pv_a += pv_a_step
    
    # Method B
    z = spot_rates[i]
    df_b = 1 / ((1 + z/2)**(2*t))
    pv_b_step = cf * df_b
    pv_b += pv_b_step
    
    proof_data.append({
        "Time (Yr)": t,
        "Cash Flow ($)": cf,
        "Method A: Disc Factor": df_a,
        "Method A: PV ($)": pv_a_step,
        "Method B: Disc Factor (Spot)": df_b,
        "Method B: PV ($)": pv_b_step
    })

proof_df = pd.DataFrame(proof_data)

col_a, col_b = st.columns(2)

with col_a:
    st.subheader("Method A: Par Yield Discounting")
    st.latex(r"PV = \sum_{t=0.5}^{" + str(proof_maturity) + r"} \frac{C}{(1+Y/2)^{2t}} + \frac{100}{(1+Y/2)^{" + str(num_periods) + r"}}")
    st.success(f"**Calculated PV = \\${pv_a:.10f}**")
    st.markdown("Discounting entirely at the par yield simply brings the bond value back strictly to face value. This is mathematically trivial, by definition.")

with col_b:
    st.subheader("Method B: Bootstrapped Spot Rates")
    st.latex(r"PV = \sum_{t=0.5}^{" + str(proof_maturity) + r"} \frac{C}{(1+z_t/2)^{2t}} + \frac{100}{(1+z_{" + str(proof_maturity) + r"}/2)^{" + str(num_periods) + r"}}")
    st.success(f"**Calculated PV = \\${pv_b:.10f}**")
    st.markdown("Using our bootstrapped spot rates curve, each individual coupon perfectly matches the underlying pricing. The prices are absolutely identical!")

st.write("### Cash Flow Breakdown Table")
st.dataframe(proof_df.style.format({
    "Time (Yr)": "{:.1f}",
    "Cash Flow ($)": "{:.4f}",
    "Method A: Disc Factor": "{:.6f}",
    "Method A: PV ($)": "{:.6f}",
    "Method B: Disc Factor (Spot)": "{:.6f}",
    "Method B: PV ($)": "{:.6f}"
}), use_container_width=True, height=400)
    
if abs(pv_a - pv_b) < 1e-6:
    st.balloons()
