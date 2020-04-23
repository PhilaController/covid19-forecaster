from covid19_forecaster.taxes import run_forecasts
from pathlib import Path

current_directory = Path(__file__).parent

if __name__ == "__main__":

    # Run all of the forecasts and save to file
    run_forecasts(current_directory / "COVID Budget Impact Analysis.xlsx")
