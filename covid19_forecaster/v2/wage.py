import numpy as np
import pandas as pd

from ..core import RevenueForecast
from ..forecasters import NoBaselineForecasterBySector
from . import (
    BASELINE_START,
    BASELINE_STOP,
    FORECAST_START,
    FORECAST_STOP,
    FREQ,
)

CROSSWALK = {
    "Leisure & Hospitality": [
        "Arts, Entertainment, and Other Recreation",
        "Hotels",
        "Restaurants",
        "Sport Teams",
    ],
    "Financial activities": [
        "Banking & Credit Unions",
        "Insurance",
        "Real Estate, Rental and Leasing",
        "Securities / Financial Investments",
    ],
    "Mining, Logging, & Construction": ["Construction"],
    "Educational & Health Services": [
        "Education",
        "Health and Social Services",
    ],
    "Government": ["Government"],
    "Manufacturing": ["Manufacturing"],
    "Other services": ["Other Sectors", "Unclassified Accounts"],
    "Professional & Business Services": ["Professional Services"],
    "Trade, Transportation, & Utilities": [
        "Public Utilities",
        "Retail Trade",
        "Transportation and Warehousing",
        "Wholesale Trade",
    ],
    "Information": [
        "Publishing, Broadcasting, and Other Information",
        "Telecommunication",
    ],
}


class WageTaxForecast(NoBaselineForecasterBySector, RevenueForecast):
    """Wage tax revenue forecast."""

    ASSUMPTIONS = {
        "severe": {
            "Educational & Health Services": [
                157297692.39599785,
                157855393.01924583,
                158414899.03503266,
                158976215.98469204,
                159539349.42598072,
                160104304.9331259,
            ],
            "Financial activities": [
                34308679.693078645,
                34410769.09214861,
                39669874.562836945,
                41504355.32418982,
                42484009.94361003,
                43466154.80055078,
            ],
            "Government": [
                52336927.67173249,
                52467769.99091183,
                52598939.41588911,
                52730436.76442883,
                52862262.8563399,
                52994418.51348075,
            ],
            "Information": [
                14810776.795984035,
                14880758.740111964,
                17173225.33698096,
                17990020.82023263,
                18438569.873754323,
                18888323.306867506,
            ],
            "Leisure & Hospitality": [
                21399297.673853062,
                22613743.157662373,
                23834127.123280272,
                25060471.672831528,
                26292798.981836013,
                27531131.299437568,
            ],
            "Manufacturing": [
                26524159.723438617,
                26626562.486784317,
                26729311.487948474,
                26832407.81810291,
                26935852.57171132,
                27039646.84653891,
            ],
            "Mining, Logging, & Construction": [
                17885006.617027108,
                17983281.90754994,
                18081936.793234024,
                18180972.557834607,
                18280390.48915324,
                18380191.87904998,
            ],
            "Other services": [
                36000100.28797411,
                36235361.40868511,
                36471573.834372856,
                36708740.85118024,
                36946865.755735196,
                37185951.85518261,
            ],
            "Professional & Business Services": [
                53254983.01476174,
                53437331.71965384,
                57620677.516297296,
                59147659.551873885,
                60678582.68656733,
                62213457.08223548,
            ],
            "Trade, Transportation, & Utilities": [
                56046461.305607505,
                56248767.97247248,
                56451735.88228862,
                56655367.076854005,
                56859663.604042955,
                57064627.517823614,
            ],
        },
        "moderate": {
            "Educational & Health Services": [
                158329651.46786198,
                159671904.18785027,
                161149770.4047019,
                162856358.80904347,
                164586944.81444213,
                166120266.3869037,
            ],
            "Financial activities": [
                34419521.225046165,
                34454798.48575193,
                39780047.68547774,
                41820023.236432895,
                43050178.96765235,
                44272814.70847764,
            ],
            "Government": [
                52525889.56343523,
                52570019.7477411,
                52810163.001162365,
                53231130.55300624,
                53700250.62366923,
                54151225.95541153,
            ],
            "Information": [
                14848252.34312045,
                14893412.36475511,
                17207008.03307773,
                18097073.9718935,
                18635171.87557968,
                19166493.22529244,
            ],
            "Leisure & Hospitality": [
                21763011.040680602,
                24567775.811800536,
                26404744.504373845,
                27587679.675510738,
                28511396.360333,
                29099064.078192092,
            ],
            "Manufacturing": [
                26614902.44249654,
                26697101.70430642,
                26856093.876189765,
                27091055.85703233,
                27344421.705785062,
                27581538.53985289,
            ],
            "Mining, Logging, & Construction": [
                17946193.630969115,
                18057897.066857796,
                18200194.934216667,
                18378996.234028623,
                18564568.848020397,
                18732549.711328786,
            ],
            "Other services": [
                36123261.47462621,
                36420211.35994002,
                36751598.38465713,
                37137598.67560859,
                37530004.6158894,
                37878499.31605926,
            ],
            "Professional & Business Services": [
                53437175.476748474,
                53557435.5416984,
                57854742.04922754,
                59677052.87127759,
                61556252.16771449,
                63417655.54925789,
            ],
            "Trade, Transportation, & Utilities": [
                56238203.790401526,
                56384793.16592909,
                56703850.96404992,
                57190525.17588292,
                57718802.51375767,
                58215940.32184015,
            ],
        },
    }

    def __init__(
        self, fresh=False,
    ):
        super().__init__(
            tax_name="wage",
            forecast_start=FORECAST_START,
            forecast_stop=FORECAST_STOP,
            freq=FREQ,
            baseline_start=BASELINE_START,
            baseline_stop=BASELINE_STOP,
            fresh=fresh,
            sector_crosswalk=CROSSWALK,
            agg_after_fitting=True,
            fit_kwargs={"seasonality_mode": "multiplicative"},
            flat_growth=True,
        )

    def run_forecast(self, scenario):
        """Run the forecast, adding seasonality in the severe case."""

        # Run the base
        self.forecast_ = super().run_forecast(scenario)

        # Get the seasonality
        baseline = self.baseline_forecast.forecasted_revenue_.copy()
        seasonality = baseline["yearly"] / baseline["trend"]

        # Calibrate trend line!
        trend_to_actuals = baseline["trend"].sum(
            axis=1
        ) / self.baseline_forecast.actual_revenue_.sum(axis=1)
        TREND_FACTOR = trend_to_actuals.loc["2019-10"].squeeze()

        # Apply seasonality
        start = self.forecast_start
        self.forecast_.loc[start:] *= (
            1 + seasonality.loc[start:]
        ) * TREND_FACTOR

        return self.forecast_
