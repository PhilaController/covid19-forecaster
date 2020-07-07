import calendar
from abc import ABC, abstractmethod
from collections import defaultdict

import openpyxl
import pandas as pd
from matplotlib import pyplot as plt
from phila_style import get_digital_standards
from phila_style.matplotlib import get_theme

from .. import DATA_DIR
from ..baseline import load_baseline_forecast
from ..utils import add_date_column, get_quarter


class ScenarioForecast(ABC):
    """
    An abstract base class to represent a scenario-based forecasts
    for tax revenue.

    This forecasts tax revenue declines through the end of the
    calendar year 2021.

    Parameters
    ----------
    fresh : bool, optional
        use a fresh copy of the baseline forecast
    """

    # The names of the scenarios
    SCENARIOS = ["moderate", "severe"]

    # Start date for forecasting
    START = "4/1/2020"

    # End date for forecasting
    END = "12/31/2021"

    def __init__(self, fresh=False):

        # Load the baseline forecast
        self.baseline = load_baseline_forecast(self.tax_name, fresh=fresh)

        # Get the scenario results
        self.forecasts = {}
        for scenario in self.SCENARIOS:
            self.forecasts[scenario] = self.run_forecast(scenario)

    @property
    @abstractmethod
    def tax_name(self):
        """
        The name of the tax to forecast
        """
        pass

    @property
    def _baseline_forecast(self):
        """
        Return the dataframe holding the baseline forecast.
        """
        return self.baseline.forecast

    @abstractmethod
    def get_forecasted_decline(self, scenario, date, sector=None):
        """
        For a given scenario (and optionally sector), return the revenue
        decline from the baseline forecast for the specific date.

        Parameters
        ----------
        scenario : str
            the scenario to projct
        date : pandas.Timestamp
            the date object for the month to forecast
        sector : str, optional
            the sector to forecast
        """
        pass

    def run_forecast(self, scenario):
        """
        Run the forecast for the specified scenario.

        Parameters
        ----------
        scenario : str
            the name of the scenario to forecast
        """
        assert scenario in self.SCENARIOS

        # Start from the baseline forecast over the forecast period
        forecast = (
            self._baseline_forecast.set_index("date")
            .loc[self.START : self.END]
            .reset_index()
            .reset_index(drop=True)
            .copy()
        )

        # Iterate over each month and apply the reduction
        for i, row in forecast.iterrows():

            # Get the percentage decline from baseline
            decline = self.get_forecasted_decline(
                scenario, row["date"], row.get("naics_sector", None)
            )

            # Rescale each column
            for col in ["total", "lower", "upper"]:
                forecast.loc[i, col] = row[col] * (1 - decline)

        return forecast

    @classmethod
    def get_month_offset(cls, date):
        """
        A utility function to convert to calculate the monthly offset
        from the start of the forecast period to the input date.
        """
        # Month offset from forecast start
        return (
            date.to_period("M") - pd.to_datetime(cls.START).to_period("M")
        ).n

    def get_monthly_declines(self, scenario):
        """
        Calculate the monthly differences between the baseline
        forecast and the scenario forecast.
        """
        assert scenario in self.SCENARIOS

        forecast = self.forecasts[scenario]
        baseline = self.baseline.forecast

        return (
            (
                forecast.groupby("date")["total"].sum()
                - baseline.groupby("date")["total"].sum()
            )
            .dropna()
            .sort_index()
        )

    def get_fiscal_year_declines(self, scenario):
        """
        Calculate the fiscal year differences between the baseline
        forecast and the scenario forecast.
        """
        declines = self.get_monthly_declines(scenario)

        def get_fiscal_year(date):
            year = date.year
            return year if date.month < 7 else year + 1

        declines = declines.reset_index().assign(
            date=lambda df: df.date.apply(get_fiscal_year)
        )
        return declines.groupby("date")["total"].sum().sort_index()

    def get_quarterly_declines(self, scenario):
        """
        Calculate the quarter-by-quarter differences between the baseline
        forecast and the scenario forecast.
        """
        declines = self.get_monthly_declines(scenario)

        declines = declines.reset_index().assign(
            date=lambda df: df.date.apply(get_quarter)
        )
        return declines.groupby("date")["total"].sum().sort_index()

    def get_combined_scenarios(self):
        """
        Return a dataframe with the baseline forecast as well as
        the forecast for each scenario in a single data frame.
        """

        # Combine
        data = [
            self.baseline.forecast.assign(Scenario="baseline"),
            self.baseline.historical.assign(Scenario="actual"),
        ] + [self.forecasts[k].assign(Scenario=k) for k in self.SCENARIOS]

        # Trim to the forecast range
        data = pd.concat(data).query(
            f"date >= '{self.START}' and date <= '{self.END}'"
        )

        # Handle sector-by-sector data
        if "naics_sector" in data:
            data = data.rename(columns={"naics_sector": "Sector"})
            index = ["Scenario", "Sector"]
            sectors = sorted(data["Sector"].unique())
        else:
            index = "Scenario"

        # Pivot the data so each month has a column
        out = data.pivot_table(columns="date", values="total", index=index)

        # Add a Sector Total
        if "Sector" in out.index.names:
            for scenario in out.index.get_level_values("Scenario").unique():
                total = out.loc[scenario].sum(axis=0)
                out.loc[(scenario, "Total"), total.index] = total.values

            out = out.sort_index().reindex(sectors + ["Total"], level=1)

        return out

    def get_assumptions_matrix(self, by_quarter=False):
        """
        Return a data frame holding the monthly declines from the
        baseline forecast for each month in the forecast period.
        """

        # Combined forecasts
        df = self.get_combined_scenarios()

        if not by_quarter:
            # Get the decline
            for scenario in self.SCENARIOS:
                decline = 1 - df.loc[[scenario]] / df.loc["baseline"]
                df.loc[scenario, decline.columns] = decline.values

            # Remove the baseline forecast
            out = df.drop(labels=["baseline"])
        else:

            # Map month dates to quarters
            quarters = defaultdict(list)
            for col in df.columns:
                quarters[get_quarter(col)].append(col)

            out = []
            for scenario in self.SCENARIOS:
                for quarter_tag in sorted(quarters):
                    columns = quarters[quarter_tag]
                    decline = (
                        1
                        - df.loc[[scenario], columns].sum(axis=1)
                        / df.loc[["baseline"], columns].sum(axis=1).values
                    )
                    out.append(
                        decline.reset_index(name="Decline").assign(
                            Quarter=quarter_tag
                        )
                    )

            out = pd.concat(out)
            out = out.pivot_table(
                index=df.index.names, values="Decline", columns="Quarter"
            )

        # Return in the original order
        return out.reindex(df.drop(labels=["baseline"], axis=0).index)

    def plot(self):
        """
        Plot the baseline and scenario forecasts, as well as the
        historical data points.
        """
        # Load the palettes
        palette = get_digital_standards()

        with plt.style.context(get_theme()):

            fig, ax = plt.subplots(
                figsize=(6, 4), gridspec_kw=dict(left=0.15, bottom=0.1)
            )

            # Plot the prediction
            labels = ["baseline"] + self.SCENARIOS
            data = [self.baseline.forecast] + [
                self.forecasts[k] for k in labels[1:]
            ]
            colors = ["medium-gray", "ben-franklin-blue", "bell-yellow"]

            for label, df, color in zip(labels, data, colors):

                if label != "baseline":
                    start = df["date"].min()

                    df = pd.concat(
                        [
                            self.baseline.forecast.query(
                                f"month == {start.month-1} and year == {start.year}"
                            ),
                            df,
                        ],
                        axis=0,
                    )

                P = df.groupby("date")[["total", "lower", "upper"]].sum()
                P.plot(
                    lw=1,
                    ax=ax,
                    y="total",
                    color=palette[color],
                    zorder=10,
                    legend=False,
                    label=label,
                )

            # Plot the historical scatter
            H = self.baseline.historical.groupby("date")["total"].sum()
            H.reset_index().plot(
                kind="scatter",
                x="date",
                y="total",
                ax=ax,
                color=palette["love-park-red"],
                zorder=11,
            )

            # Format
            ax.set_yticklabels([f"${x/1e6:.1f}M" for x in ax.get_yticks()])
            ax.set_xlabel("")
            ax.set_ylabel("")
            ax.legend(loc=0, fontsize=10)

            return fig, ax

    def save_to_template(self, sheet_name, data_start_row):
        """
        Save the forecast to a template Excel file.

        Parameters
        ----------
        sheet_name : str
            the name of the Excel sheet to save to
        data_start_row : int
            the row number to write the data to
        """
        # Combined scenarios
        data = self.get_combined_scenarios()
        index_order = ["baseline"] + self.SCENARIOS + ["actual"]
        if hasattr(data.index, "levels"):
            data = data.reindex(index_order, level=0)
        else:
            data = data.loc[index_order]

        filename = (
            DATA_DIR / "templates" / "Budget Impact Analysis Template.xlsx"
        )
        with pd.ExcelWriter(filename, engine="openpyxl") as writer:

            # Copy over the sheets
            book = openpyxl.load_workbook(filename)
            writer.book = book
            writer.sheets = dict((ws.title, ws) for ws in book.worksheets)

            # Write the data
            data.to_excel(
                writer,
                sheet_name=sheet_name,
                startrow=data_start_row,
                header=None,
                merge_cells=False,
            )


class ShiftedScenarioForecast(ScenarioForecast):
    """
    An abstract base class to represent a forecast where the April
    revenue spike is shifted to July.

    This will be used for BIRT and NPT forecasts.
    """

    def __init__(self, fresh=False):

        # Load the baseline forecast
        self.baseline = load_baseline_forecast(self.tax_name, fresh=fresh)

        # Shift April to July
        self.shifted_forecast = self.shift_april_to_july()

        # Get the scenario results
        self.forecasts = {}
        for scenario in self.SCENARIOS:
            self.forecasts[scenario] = self.run_forecast(scenario)

    @property
    def _baseline_forecast(self):
        """
        Return the dataframe holding the (shifted) baseline forecast.
        """
        return self.shifted_forecast

    def shift_april_to_july(self):
        """
        Shift the baseline forecast in time so that April corresponds to
        July, and so on.
        """

        # Shift
        f = self.baseline.forecast.copy()
        is_2020 = f.year == 2020

        f.loc[is_2020, "month"] = f.loc[is_2020, "month"].replace(
            {10: 4, 11: 5, 12: 6, 4: 7, 5: 8, 6: 9, 7: 10, 8: 11, 9: 12}
        )
        return add_date_column(
            f.assign(
                month_name=lambda df: df.month.apply(
                    lambda i: calendar.month_abbr[i].lower()
                ),
                fiscal_month=lambda df: ((df.month - 7) % 12 + 1),
            )
        ).assign(quarter=lambda df: df.date.apply(get_quarter))
