"""
A module to store revenues and growth rates used in the
FY21-FY25 Five Year Plan, as proposed on March 5, 2020
"""
import pandas as pd

BIRT_REVENUES = pd.DataFrame(
    {
        "fiscal_year": [2020, 2021, 2022, 2023, 2024, 2025],
        "total": [
            540945000,
            574965000,
            595843000,
            612812000,
            617622000,
            622550000,
        ],
    }
).set_index("fiscal_year")["total"]

# Projected revenues from FY20 Q2 QCMR
FY20_REVENUES = {
    "wage": 2195818000,  # This is City + PICA Wage+Earnings
    "sales": 236228000,
    "birt": 540945e3,
    "rtt": 338299e3,
    "parking": 101487000,
    "amusement": 25490000,
    "npt": 36791000,
    "soda": 76086000,
}

# Growth rates listed in FY21-FY25
FYP_GROWTH_RATES = {
    "wage": [4.5, 4.0, 3.9, 3.75, 4.0],
    "sales": [3.13, 3.25, 3.17, 3.33, 3.56],
    "birt": [4.50, 4.25, 4.00, 3.70, 3.8],
    "rtt": [1.00, 4.25, 4.16, 3.70, -4.59],
    "parking": [2.8, 2.88, 2.81, 2.95, 3.16],
    "soda": [-1, -1, -1, -1, -1],
}

for tax in FYP_GROWTH_RATES:
    FYP_GROWTH_RATES[tax] = (
        pd.DataFrame(
            {
                "fiscal_year": [2021, 2022, 2023, 2024, 2025],
                "growth_rate": FYP_GROWTH_RATES[tax],
            }
        ).set_index("fiscal_year")["growth_rate"]
        / 100
    )
