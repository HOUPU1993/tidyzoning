import geopandas as gpd
import tidyzoning
from tidyzoning import unify_tidybuilding

def read_bldg(bldg_data_file=None, ozfs_data_file=None, bldg_data_string=None):
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
    build_df = unify_tidybuilding(bldg_data_file, ozfs_data_file, bldg_data_string)
    return build_df