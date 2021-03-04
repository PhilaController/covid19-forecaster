# covid19-forecaster

Analysis toolkit for forecasting the revenue impact of COVID-19 on the City of Philadelphia's finances.

Read the reports:

- ["Estimates of the Impact of COVID-19 on the City of Philadelphia’s Tax Revenues" (April 2020)](https://controller.phila.gov/philadelphia-audits/covid19-fiscal-impact/)


## Installation

The following commands should be run from the command line, e.g., the Terminal app on 
MacOS or Command Prompt on Windows.

### Step 1: Make sure you have pipenv installed

Via conda: 

```bash
conda install -c conda-forge pipenv
```

or via pip:

```
pip install pipenv
```

### Step 2: Clone the repository

```bash

# Clone the repository
git clone https://github.com/PhiladelphiaController/covid19-forecaster.git

# Change to the new folder
cd covid19-forecaster
```

### Step 3: Install the dependencies

We will use `pipenv` to install the necessary dependencies into their own virtual environment. 

From the `covid19-forecaster` folder, run:

```bash
pipenv install --dev
```

This will install all dependencies (as well as the development dependencies).

## Running the forecasts

From the command line, the forecasts can be run using the following command:

```bash
pipenv run python run_forecasts.py
```

This will update the 'COVID Budget Impact Analysis.xlsx' spreadsheet with the updated forecast results. 

### Working in an interactive environment

You can run the software in an interactive environment using [Jupyter lab](https://jupyterlab.readthedocs.io/en/stable/) by running:

```bash
pipenv install jupyter lab
```

This *should* launch a Jupyter window on your browser, at which point you can create a new notebook file (`.ipynb` file).

To run the software from the notebook, you can run (from within a Jupyter cell):

```python
# Import the function to run
from covid19_forecaster.taxes import *

# Run forecasts and save to a spreadsheet
filename = "COVID Budget Impact Analysis.xlsx"
run_forecasts(filename)
```

You can also examine the forecasts for individual taxes. For example, for the Wage Tax model:


```python
# Load the wage tax model
wage = WageTax()

# Plot historical data + scenario forecasts
wage.plot()
```



