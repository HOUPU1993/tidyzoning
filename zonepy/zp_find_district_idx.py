import geopandas as gpd  
import pandas as pd     

# def zp_find_district_idx(tidyparcel, tidyzoning):
    # """
    # Optimized version: Find the indices of the districts in `tidyzoning` that contain the centroids of the `tidyparcel`.

    # Parameters:
    # tidyparcel (GeoDataFrame): A GeoDataFrame representing the parcel.
    #                            Must include rows with 'centroid' in the 'side' column.
    # tidyzoning (GeoDataFrame): A GeoDataFrame representing zoning districts with geometries.

    # Returns:
    #                 Prop_ID and Pacel_id are from Tidyparcel
    #                 tidyzoning_index are from Tidyzoning
    #                 (Prop_ID, parcel_id, tidyzoning_index) if a match is found, or (Prop_ID, parcel_id, None) if no match is found.
    # How to use:
    # find_district_idx_results = find_district_idx(tidyparcel, tidyzoning)
    # """
    # # Filter rows with centroids
    # centroid_rows = tidyparcel[tidyparcel['side'] == 'centroid']
    # if centroid_rows.empty:
    #     print("No centroids found in tidyparcel.")
    #     return []

    # # Perform spatial join to find matches
    # joined = gpd.sjoin(centroid_rows, tidyzoning, how='left', predicate='within')

    # # Create the DataFrame directly with required columns
    # results_df = pd.DataFrame({
    #     "parcel_id": joined["parcel_id"],
    #     "zoning_id": joined["index_right"]
    # })

    # return results_df
    
import geopandas as gpd
import pandas as pd

def zp_find_district_idx(tidyparcel: gpd.GeoDataFrame,
                         tidyzoning: gpd.GeoDataFrame) -> pd.DataFrame:
    """
    Find each parcel's zoning_id(s) by its centroid.
    - 如果一个 parcel 的 centroid 落在多个 zoning 区块内，
      则 zoning_id 返回一个列表 [id1, id2, ...]。
    - 如果只落在一个区块内，返回那个标量 id。
    - 如果没有落在任何区块，返回 None。

    Parameters
    ----------
    tidyparcel : GeoDataFrame
        必须含列 'parcel_id', 'side', 'geometry'，且有 side=='centroid' 的行。
    tidyzoning : GeoDataFrame
        zoning district 图层，其 index 就是 zoning_id。

    Returns
    -------
    DataFrame with columns:
      parcel_id, zoning_id
    """
    # 1. 取出所有 centroid 行
    centroids = tidyparcel[tidyparcel['side'] == 'centroid']
    if centroids.empty:
        return pd.DataFrame(columns=['parcel_id', 'zoning_id'])

    # 2. 空间连接，得到每个 centroid 属于哪些 zoning 区（index_right）
    joined = gpd.sjoin(
        centroids[['parcel_id', 'geometry']],
        tidyzoning[['geometry']],
        how='left',
        predicate='within'
    )

    # 把 NaN 变 None
    joined['index_right'] = joined['index_right'].where(
        joined['index_right'].notna(), None
    )

    # 3. 分组聚合
    def agg_ids(ids):
        # 先过滤掉 None
        clean = [int(i) for i in ids if i is not None]
        if len(clean) == 0:
            return None
        if len(clean) == 1:
            return clean[0]
        # 多于一个，返回列表
        return clean

    agg = (
        joined
        .groupby('parcel_id', sort=False)['index_right']
        .agg(agg_ids)
        .reset_index()
        .rename(columns={'index_right': 'zoning_id'})
    )

    # 4. 保证每个 centroid 至少出现一行（对 0、1 个匹配外的情形已处理）
    #    这里不用再补全，因为 agg_ids 已经对 0 个的返回 None
    return agg
