import argparse
from pathlib import Path

from covid19_forecaster.taxes import run_forecasts

current_directory = Path(__file__).parent

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--fresh", action="store_true")
    args = parser.parse_args()

    # Run all of the forecasts and save to file
    run_forecasts(
        current_directory / "COVID Budget Impact Analysis.xlsx",
        fresh=args.fresh,
    )
