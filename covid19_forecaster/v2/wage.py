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
        "moderate": {
            "Educational & Health Services": [
                154970444.96123838,
                157622494.56706154,
                161975403.1331638,
                165820100.7594851,
                165048093.83472803,
                167325015.60829383,
            ],
            "Financial activities": [
                54729981.87214689,
                44025534.78100467,
                38712483.91936568,
                38756868.9664547,
                55926026.571434565,
                45341395.25829004,
            ],
            "Government": [
                68846684.7421078,
                57572786.91063191,
                71545432.61909501,
                57809069.44097503,
                69021144.03590372,
                61130179.24696087,
            ],
            "Information": [
                20383656.572224174,
                18490285.898634806,
                15849798.24338203,
                16173868.721063677,
                20896656.55317339,
                19540685.89455849,
            ],
            "Leisure & Hospitality": [
                23862092.14414267,
                23175268.002779767,
                25002966.562813465,
                26891299.557140686,
                27354006.65604629,
                25222004.9939523,
            ],
            "Manufacturing": [
                32355828.788715538,
                27659108.54775845,
                25766969.492640596,
                26788110.26321993,
                33274622.695953865,
                28232831.854739238,
            ],
            "Mining, Logging, & Construction": [
                17943599.485380694,
                17954330.70714891,
                19159292.283839714,
                19395153.22931562,
                19490887.619620476,
                19141656.696181625,
            ],
            "Other services": [
                38322070.08228314,
                37698288.6097371,
                38389461.79990671,
                39540874.60202495,
                41628795.05352193,
                41106068.46809614,
            ],
            "Professional & Business Services": [
                63556992.41932101,
                52372807.206093356,
                52480791.381821446,
                55839231.58589218,
                65848416.70838951,
                55035438.28561248,
            ],
            "Trade, Transportation, & Utilities": [
                60434017.73872964,
                57554459.416699864,
                56299746.81140789,
                57582534.899701424,
                62185980.190625824,
                59853729.9419314,
            ],
        },
        "severe": {
            "Educational & Health Services": [
                157664120.0645195,
                159639405.06217718,
                161509295.4906227,
                163439866.9331729,
                165330348.14824745,
                166949093.2586505,
            ],
            "Financial activities": [
                34322774.939862184,
                34590522.431650035,
                34896412.28997451,
                35257960.83936672,
                35627038.613565244,
                35956091.779611036,
            ],
            "Government": [
                52192529.85417928,
                52236500.963257834,
                52475195.5766738,
                52893535.218607545,
                53359709.65290331,
                53807840.23912313,
            ],
            "Information": [
                15395345.316663733,
                16671845.620754197,
                17530110.14908471,
                18110820.49319155,
                18579051.315827716,
                18892987.227357298,
            ],
            "Leisure & Hospitality": [
                21344209.6253595,
                23589898.604485765,
                25076568.189488444,
                26053926.894864596,
                26827660.132280134,
                27331363.63687627,
            ],
            "Manufacturing": [
                26447016.69071744,
                26529135.839474108,
                26687398.451036893,
                26921036.970709376,
                27172919.345718138,
                27408603.516427435,
            ],
            "Mining, Logging, & Construction": [
                17888555.186835,
                18103370.84737613,
                18309729.558636986,
                18525406.0423664,
                18737465.63091201,
                18919790.552416973,
            ],
            "Other services": [
                36916743.605359614,
                39172058.23912272,
                40727767.88665372,
                41828680.833756864,
                42740590.68297385,
                43377499.0431916,
            ],
            "Professional & Business Services": [
                53447237.102621906,
                54230825.40002326,
                54935776.923626006,
                55631481.879916705,
                56302177.35322158,
                56867317.630667195,
            ],
            "Trade, Transportation, & Utilities": [
                55945826.17959422,
                56212029.21991737,
                56604486.86930261,
                57132198.72992681,
                57689237.321961746,
                58201105.754957885,
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

        # Update seasonality
        if scenario == "severe":

            # Get the seasonality
            baseline = self.baseline.forecasted_revenue_.copy()
            seasonality = baseline["yearly"] / baseline["trend"]

            # Apply seasonality
            self.forecast_ *= 1 + seasonality.loc[self.forecast_.index]

        return self.forecast_
