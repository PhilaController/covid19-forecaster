from .forecast import BaselineForecast
from .. import DATA_DIR
from ..utils import get_quarter


def load_baseline_forecast(tax_name, fresh=False):
    """
    Load a baseline forecast for the specified tax

    Parameters
    ----------
    tax_name : str
        the name of the tax to forecast
    fresh : bool, optional
        return a fresh copy of the forecast
    """
    path = DATA_DIR / "projections" / f"{tax_name}.pickle"
    if fresh or not path.is_file():
        f = BaselineForecast(tax_name)
        f.save(path)

    out = BaselineForecast.load(path)
    out.forecast = out.forecast.assign(
        quarter=lambda df: df.date.apply(get_quarter)
    )

    return out
