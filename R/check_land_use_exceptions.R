#' Compare building land use and allowed land uses
#'
#' `check_land_use_exceptions()`, like `check_land_use()`, will see if the district's zoning code allows the tidybuilding based on land use.
#' But this function also return TRUE if the land use is recorded in the tidyzoning as a potential exception.
#'
#' @inheritParams add_setbacks
#'
#' @return
#' Returns TRUE or FALSE stating whether or not the building would be allowed in the district based on land use.
#' It will also return TRUE if the tidyzoning records a potential exception would allow the land use.
#' Note: If there is no recorded land use requirement in zoning code, it returns FALSE
#' @export
#'
check_land_use_exceptions <- function(tidybuilding, tidydistrict){
  dist_info_list <- fromJSON(tidydistrict$dist_info)

  bldg_type <- find_bldg_type(tidybuilding)

  if (bldg_type == "other"){
    return(FALSE)
    warning("Unable to calculate building type. Results may not be accurate")
  }

  if (bldg_type %in% dist_info_list$uses_permitted$uses_value){
    return(TRUE)
  } else{
    return(bldg_type %in% dist_info_list$uses_permitted$excep_value)
  }

}
