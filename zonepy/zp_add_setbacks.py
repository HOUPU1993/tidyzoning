import warnings
import pandas as pd
import geopandas as gpd
from shapely.geometry import MultiLineString

def zp_add_setbacks(parcel_gdf: gpd.GeoDataFrame,
                    district_row: pd.Series,
                    zoning_req):
    """
    Python equivalent of zr_add_setbacks()

    :param parcel_gdf: GeoDataFrame, each row has 'side' and geometry
    :param district_row: pd.Series or GeoSeries, contains geometry
    :param zoning_req: pd.DataFrame or str
    :return: parcel_gdf (adds 'setback' column, and may add 'on_boundary' column)
    """

    # 1. No zoning_req case
    if isinstance(zoning_req, str):
        parcel_gdf = parcel_gdf.copy()
        parcel_gdf['setback'] = None
        return parcel_gdf

    # 2. Mapping from side to constraint_name
    name_key = {
        'front':           'setback_front',
        'interior side':   'setback_side_int',
        'exterior side':   'setback_side_ext',
        'rear':            'setback_rear'
    }

    # 3. Basic setback assignment
    parcel_gdf = parcel_gdf.copy()
    setbacks = []
    missing_side = False

    for _, row in parcel_gdf.iterrows():
        side = row['side']
        if side not in name_key:
            setbacks.append(None)
            missing_side = True
            continue

        # Find the corresponding constraint
        key = name_key[side]
        match = zoning_req[zoning_req['constraint_name'] == key]
        if not match.empty:
            # Take its min_value
            setbacks.append(match.iloc[0]['min_value'])
        else:
            setbacks.append(None)

    if missing_side:
        warnings.warn("No side label. Setbacks not considered.")
    parcel_gdf['setback'] = setbacks

    # 4. Check for extra rules
    extra = []
    if 'setback_side_sum' in zoning_req['constraint_name'].values:
        extra.append('setback_side_sum')
        side_sum = zoning_req.loc[
            zoning_req['constraint_name']=='setback_side_sum',
            'min_value'
        ].iloc[0]
    if 'setback_front_sum' in zoning_req['constraint_name'].values:
        extra.append('setback_front_sum')
        front_sum = zoning_req.loc[
            zoning_req['constraint_name']=='setback_front_sum',
            'min_value'
        ].iloc[0]
    if 'setback_dist_boundary' in zoning_req['constraint_name'].values:
        extra.append('setback_dist_boundary')
        dist_boundary = zoning_req.loc[
            zoning_req['constraint_name']=='setback_dist_boundary',
            'min_value'
        ].iloc[0]

        # 5. Calculate on_boundary column based on district boundary
        geom = district_row.geometry.iloc[0]
        boundary = geom.boundary  # LineString or MultiLineString
        buffer5 = boundary.buffer(5)
        parcel_gdf['on_boundary'] = parcel_gdf.geometry.within(buffer5)

    # 6. If no extra rules, return directly
    if not extra:
        return parcel_gdf

    # 7. Apply setback_dist_boundary
    if 'setback_dist_boundary' in extra:
        def apply_dist(sb):
            if sb is None:
                return None
            # Single value vs multiple values: assume sb is numeric if not list/tuple
            old = sb
            new = max(old, dist_boundary) if not isinstance(old, (list, tuple)) else max(dist_boundary, *old)
            # If first and last value in multi-value are equal, take scalar
            if isinstance(new, (list, tuple)) and new[0]==new[-1]:
                return new[0]
            return new

        mask = parcel_gdf['on_boundary']
        parcel_gdf.loc[mask, 'setback'] = parcel_gdf.loc[mask, 'setback'].apply(apply_dist)

    # 8. Apply setback_side_sum
    if 'setback_side_sum' in extra:
        sides = parcel_gdf['side']
        int_idxs = parcel_gdf.index[sides=='interior side']
        ext_idxs = parcel_gdf.index[sides=='exterior side']

        # Determine which two side edges
        if len(ext_idxs)>0 and len(int_idxs)>0:
            idx1, idx2 = ext_idxs[0], int_idxs[0]
        elif len(int_idxs)>=2:
            idx1, idx2 = int_idxs[0], int_idxs[1]
        elif len(ext_idxs)>=2:
            idx1, idx2 = ext_idxs[0], ext_idxs[1]
        else:
            warnings.warn("setback_side_sum cannot be calculated due to lack of parcel edges")
            idx1 = idx2 = None

        if idx1 is not None:
            v1 = parcel_gdf.at[idx1,'setback'] or 0
            v2 = parcel_gdf.at[idx2,'setback'] or 0
            diff = side_sum - (v1 + v2)
            inc = diff if diff>0 else 0
            parcel_gdf.at[idx2,'setback'] = v2 + inc

    # 9. Apply setback_front_sum
    if 'setback_front_sum' in extra:
        front_idxs = parcel_gdf.index[parcel_gdf['side']=='front']
        rear_idxs  = parcel_gdf.index[parcel_gdf['side']=='rear']
        if front_idxs.size>0 and rear_idxs.size>0:
            fidx, ridx = front_idxs[0], rear_idxs[0]
            fv = parcel_gdf.at[fidx,'setback'] or 0
            rv = parcel_gdf.at[ridx,'setback'] or 0
            diff = front_sum - (fv + rv)
            inc = diff if diff>0 else 0
            parcel_gdf.at[ridx,'setback'] = rv + inc
        else:
            warnings.warn("setback_front_sum cannot be calculated due to missing front or rear edge")

    return parcel_gdf