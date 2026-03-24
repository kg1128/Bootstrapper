# 💸 US Treasury Yield Curve Bootstrapping

This is a Streamlit application that fetches the latest US Treasury yield curve and mathematically bootstraps the quoted **Par Yields** to derive the theoretical **Spot Rates** (zero-coupon yield curve).

It illustrates that standard coupon bonds can be priced perfectly using zero-coupon discount factors, proving the mechanics of fixed income pricing.

## Features
- **Live Data source**: Fetches the daily par yield curve directly from the [US Department of the Treasury](https://home.treasury.gov/).
- **Manual Input mode**: Allows entering custom yield curves to test hypothetical interest rate environments.
- **Yield Curve Interpolation**: Uses **Cubic Splines** to populate rates for every 6-month period, ensuring smooth transitions across maturities.
- **Sequential Bootstrapping**: Iteratively derives the spot rate (Zero-Coupon curve) for each 6-month period up to 30 years.
- **Interactive Proof of Equivalence**: Demonstrates mathematically that discounting a target bond using its Par Yield equates perfectly to discounting each individual cash flow with the theoretical Zero-Coupon curve.

## Installation

1. Clone this repository or download the source code.
2. (Optional but recommended) Create a virtual environment.
3. Install the dependencies using pip:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the Streamlit application using the following command:
```bash
streamlit run app.py
```

The application will open in your default web browser (typically at `http://localhost:8502`).

## Requirements
- `streamlit`
- `pandas`
- `numpy`
- `plotly`
- `scipy`

## Methodology
- **Yield Equivalency**: The Treasury quotes constant maturity yields on a bond-equivalent basis (assuming semiannual compounding). All points on the curve (even those < 1 Year) are treated as semiannual coupon bonds to maintain yield consistency.
- **Bootstrapping Equation**:
  Starting from the shortest maturity and working forward, the Spot Rate $z_t$ is dynamically isolated:
  $$ 100 = \sum_{i=0.5}^{t} \frac{100 \times \frac{Y_t}{2}}{(1 + \frac{z_i}{2})^{2i}} + \frac{100}{(1 + \frac{z_t}{2})^{2t}} $$
