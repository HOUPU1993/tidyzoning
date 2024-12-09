#' Compare building floor area ratio to zoning requirements
#'
#' `check_far()` takes a tidybuilding, tidydistrict, and tidyparcel to see if the district's zoning code allows the tidybuilding based on floor area ratio.
#'
#' @inheritParams add_setbacks
#'
#' @return
#' Returns TRUE or FALSE stating whether or not the building would be allowed in the district based on floor area ratio.
#' @export
#'
check_far <- function(tidybuilding, tidydistrict, tidyparcel){
  structure_constraints <- fromJSON(tidydistrict$structure_constraints)

  if (length(tidybuilding$floor_area) == 1){
    fl_area <- tidybuilding$floor_area[[1]]
  } else if (length(tidybuilding$total_floors) == 1){
    floors <- tidybuilding$total_floors[[1]]
    fl_area <- st_area(tidybuilding) * floors
  } else{
    return(FALSE)
    warning("No floor area found in tidybuilding")
  }

  # units are in square meters right now
  far <- set_units(fl_area, "m2") / st_area(tidyparcel)

  zoning_req <- get_zoning_req(tidybuilding, tidydistrict, tidyparcel)

  if (zoning_req == "No zoning requirements recorded for this district"){
    return(TRUE)
    warning("No zoning requirements recorded for this district")
  }

  if ("far" %in% zoning_req$constraint_name){
    min_far <- zoning_req[zoning_req$constraint_name == "far", "min_value"]
    max_far <- zoning_req[zoning_req$constraint_name == "far", "max_value"]

    if (is.na(min_far)){
      min_far <- 0
    }

    if (is.na(max_far)){
      max_far <- 1000000
    }

    return(far >= min_far & far <= max_far)

  } else{
    return(TRUE)
  }

}
