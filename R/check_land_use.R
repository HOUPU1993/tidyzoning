#' Compare building land use and allowed land uses
#'
#' `check_land_use()` takes a tidybuilding and a tidydistrict to see if the district's zoning code allows the tidybuilding based on land use.
#'
#' @inheritParams add_setbacks
#'
#' @return
#' Returns TRUE or FALSE stating whether or not the building would be allowed in the district based on land use.
#' Note: If there is no recorded land use requirement in zoning code, it returns FALSE
#' @export
#'
check_land_use <- function(tidybuilding, tidydistrict){
  dist_info_list <- fromJSON(tidydistrict$dist_info)

  bldg_type <- find_bldg_type(tidybuilding)

  if (bldg_type == "other"){
    return(FALSE)
    warning("Unable to calculate building type. Results may not be accurate")
  }

  if (length(dist_info_list$uses_permitted$uses_value) == 0){
    return(FALSE)
    warning("Can't find permitted land uses. Assumed FALSE")
  } else{
    return(bldg_type %in% dist_info_list$uses_permitted$uses_value)
  }
}
