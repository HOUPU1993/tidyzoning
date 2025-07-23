def zp_check_res_type(vars, district_data):
    """
    Is the building allowed base on use_type?
    
    Campares the building use type with the permitted use types in the zoning
    code and returns TRUE or FALSE
    """

    res_type = vars.iloc[0]["res_type"]
    allowed = district_data.iloc[0]["res_types_allowed"]
    return res_type in allowed