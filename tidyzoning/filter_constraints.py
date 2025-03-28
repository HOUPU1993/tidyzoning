def filter_constraints(df, column, target_key):
    """Recursively check if the specified column contains the target_key and filter the matching rows.
    how to use: 
    filter_constraints(tidyzoning,"lot_constraints","lot_size")"""
    
    def contains_key(value, target_key):
        if isinstance(value, dict):
            return any(target_key in str(k).lower() or contains_key(v, target_key) for k, v in value.items())
        elif isinstance(value, list):
            return any(contains_key(item, target_key) for item in value)
        elif isinstance(value, str):
            return target_key in value.lower()
        return False
    
    return df[df[column].apply(lambda x: contains_key(x, target_key))]