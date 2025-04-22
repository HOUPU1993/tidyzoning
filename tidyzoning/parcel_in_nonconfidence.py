import geopandas as gpd
import pandas as pd
import numpy as np

def parcel_in_nonconfidence(tidyparcel):
    """
    Filters tidyparcel based on a list of 'confident' parcel_label types.

    Parameters:
    tidyparcel (GeoDataFrame): A tidy parcel dataset with a 'parcel_label' column.

    Returns:
    GeoDataFrame: Filtered GeoDataFrame containing only confident parcels.
    """
    non_confident_labels = [
        'jagged parcel',
        'duplicated address',
        'cul_de_sac parcel_other',
        'special parcel_other',
        'no_match_address_other',
        'curve parcel_other',
        'no_address_parcel_other'
    ]

    return tidyparcel[tidyparcel['parcel_label'].isin(non_confident_labels)].copy()