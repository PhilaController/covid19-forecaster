import argparse
import shutil
from pathlib import Path
from typing import List, Union

import click
import openpyxl
import pandas as pd
from loguru import logger
from matplotlib import pyplot as plt

from . import DATA_DIR, v1, v2
from .core import RevenueForecast, ScenarioComparison, ScenarioForecast
from .utils import get_fiscal_year


def groupby_fiscal_year(df):
    """Group the input data by the "fiscal_year" column"""

    # Re-index the input data by fiscal year
    X = df.copy()
    X.index = pd.Index(
        [get_fiscal_year(dt) for dt in X.index], name="fiscal_year"
    )

    # Group by and sum
    return X.groupby("fiscal_year").sum()


def get_scenarios_with_actuals(
    summary, by_fiscal_year=False, scenario_start_date="2021-01"
):
    """Get scenarios combined with actuals until the forecast."""

    # Actuals
    actuals = summary.xs("actual", level=1, axis=1).dropna()

    # Moderate
    moderate = (
        summary.loc[scenario_start_date:]
        .xs("moderate", level=1, axis=1)
        .dropna()
    )
    moderate = pd.concat([actuals, moderate], axis=0)

    # Severe
    severe = (
        summary.loc[scenario_start_date::]
        .xs("severe", level=1, axis=1)
        .dropna()
    )
    severe = pd.concat([actuals, severe], axis=0)

    # Group by fiscal year?
    if by_fiscal_year:
        moderate = groupby_fiscal_year(moderate).T
        severe = groupby_fiscal_year(severe).T

    return moderate, severe


def save_scenario_results(
    scenarios: ScenarioComparison, filename: Union[str, Path]
):
    """Save the scenario results to the specified path."""

    if isinstance(filename, str):
        filename = Path(filename)

    # Check parent directory
    if not filename.parent.exists():
        filename.parent.mkdir()

    # ---------------------------------------------------
    # Calculation #1: Get the normalized declines
    # ---------------------------------------------------
    declines = scenarios.get_normalized_summary()
    declines = declines.T.loc["2020":].T

    # ---------------------------------------------------
    # Calculation #2: Get the FY totals declines
    # ---------------------------------------------------
    r = scenarios.get_summary(start_date="07-01-2014").T
    moderate_fy_totals, severe_fy_totals = get_scenarios_with_actuals(
        r, by_fiscal_year=True
    )

    # Copy the template
    template_path = DATA_DIR / "templates" / "covid-budget-scenarios-v2.xlsx"
    shutil.copy(template_path, filename)

    # Open the workbook
    book = openpyxl.load_workbook(filename)

    # Verify sheets are deleted
    sheets = [
        "Normalized Declines (Raw)",
        "Optimistic (Raw)",
        "Pessimistic (Raw)",
    ]
    for sheet in sheets:
        if sheet in book.sheetnames:
            del book[sheet]
    book.save(filename)

    # Open and save the calculations
    with pd.ExcelWriter(filename, engine="openpyxl", mode="a") as writer:

        # Save the declines
        declines.to_excel(writer, sheet_name=sheets[0])

        # FY totals
        (moderate_fy_totals / 1e3)[[2020, 2021, 2022]].to_excel(
            writer, sheet_name=sheets[1]
        )
        (severe_fy_totals / 1e3)[[2020, 2021, 2022]].to_excel(
            writer, sheet_name=sheets[2]
        )


def _ensure_data_frame(X):

    out = X.copy()
    if isinstance(X, pd.Series):
        out = out.to_frame()
    return out


def save_model_outputs(scenarios: ScenarioComparison, path: Union[str, Path]):
    """Save the model outputs."""

    if isinstance(path, str):
        path = Path(path)

    # Check directory
    if not path.exists():
        path.mkdir()

    # Set up output directories
    actual_dir = path / "actuals"
    baseline_dir = path / "baseline"
    forecast_dir = path / "forecasts"

    for d in [actual_dir, baseline_dir, forecast_dir]:
        if not d.exists():
            d.mkdir()

    # Loop over each scenario
    for i, scenario in enumerate(scenarios.scenario_names):

        # Get this scenario
        this_scenario = scenarios[scenario]

        # Loop over each tax
        for tax_name in this_scenario.taxes:

            # Get this tax
            tax = this_scenario[tax_name]

            # Save Actuals and Baseline
            if i == 0:

                # The baseline forecast
                b = tax.baseline_forecast

                # Actuals
                b.actual_revenue_.to_csv(
                    actual_dir / f"{tax_name}-revenue.csv"
                )
                b.actual_tax_base_.to_csv(
                    actual_dir / f"{tax_name}-tax-base.csv"
                )

                # Baseline
                _ensure_data_frame(b.forecasted_revenue_["total"]).to_csv(
                    baseline_dir / f"{tax_name}-revenue.csv"
                )
                _ensure_data_frame(b.forecasted_tax_base_["total"]).to_csv(
                    baseline_dir / f"{tax_name}-tax-base.csv"
                )

            for scenario in ["moderate", "severe"]:

                # Run the forecast
                f = _ensure_data_frame(tax.run_forecast(scenario))
                f.to_csv(forecast_dir / f"{tax_name}-{scenario}-revenue.csv")

                # Save the figure too
                tax.plot()
                plt.savefig(
                    forecast_dir / f"{tax_name}-{scenario}-revenue.png"
                )
                plt.close()


def run_scenarios(
    taxes: List[RevenueForecast], fresh=False, scenarios=["moderate", "severe"]
):
    """Run the scenarios for the input taxes."""

    results = {}

    # Run all of the scenarios
    for scenario in scenarios:
        logger.info(f"Running scenario '{scenario}'")

        forecasts = []
        for cls in taxes:

            # Initialize and log
            tax = cls(fresh=fresh)
            logger.info(f"   Running forecast for '{tax.tax_name}'")

            # Run the forecast
            tax.run_forecast(scenario)

            # Save it
            forecasts.append(tax)

        # Save a scenario forecast object
        results[scenario] = ScenarioForecast(*forecasts)

    return ScenarioComparison(results)


def run_and_save_scenarios(
    taxes: List[RevenueForecast],
    path: Union[str, Path],
    fresh=False,
    clean=False,
    scenarios=["moderate", "severe"],
):
    """Run the scenarios and save the results."""

    # Run
    scenarios = run_scenarios(taxes, fresh=fresh, scenarios=scenarios)

    # Make sure we have a Path object
    if isinstance(path, str):
        path = Path(path)

    # Remove directory?
    out_dir = path.parent
    if out_dir.exists() and clean:
        shutil.rmtree(out_dir)

    # Make sure it exists
    if not out_dir.exists():
        out_dir.mkdir()

    # Save the scenarios
    save_scenario_results(scenarios, path)

    # Save the model inputs
    save_model_outputs(scenarios, out_dir)


@click.command()
@click.argument(
    "output_dir", type=Path,
)
@click.option(
    "--clean",
    is_flag=True,
    help="Whether to remove the output directory first.",
)
@click.option(
    "--fresh",
    is_flag=True,
    help="Whether to create fresh baselines when modeling.",
)
def main(output_dir, clean=False, fresh=False):
    """Run and save the March 2021 model forecast."""

    # Get the config for version #2
    taxes = v2.TAXES
    scenarios = v2.SCENARIOS

    # Run and save
    path = output_dir / f"covid-budget-impact-{version}.xlsx"
    run_and_save_scenarios(
        taxes, path, fresh=fresh, clean=clean, scenarios=scenarios
    )
