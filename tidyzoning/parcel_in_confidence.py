import geopandas as gpd
import pandas as pd
import numpy as np

def parcel_in_confidence(tidyparcel):
    """
    Filters tidyparcel based on a list of 'confident' parcel_label types.

    Parameters:
    tidyparcel (GeoDataFrame): A tidy parcel dataset with a 'parcel_label' column.

    Returns:
    GeoDataFrame: Filtered GeoDataFrame containing only confident parcels.
    """
    confident_labels = [
        'regular inside parcel',
        'regular corner parcel',
        'special parcel_standard',
        'curve parcel_standard',
        'cul_de_sac parcel_standard',
        'no_match_address_standard',
        'no_address_parcel_standard'
    ]

    return tidyparcel[tidyparcel['parcel_label'].isin(confident_labels)].copy()
