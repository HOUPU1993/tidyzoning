import geopandas as gpd
from tidyzoning import unify_tidybuilding

def read_bldg(path):
    """
    Reads a building folder and generate one-demensional dataset based on mutiple csv file.

    Parameters:
    -----------
    path : str
        File path to the folder.
    unify_tidybuilding : the function to calculate metrics and unify the tidybuilding

    Returns:
    --------
    DataFrame
    """
    build_df = unify_tidybuilding(path)
    return build_df