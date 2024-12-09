#' Compare building lot coverage to zoning requirements
#'
#' `check_lot_coverage()` takes a tidybuilding, tidydistrict, and tidyparcel to see if the district's zoning code allows the tidybuilding based on lot coverage.
#'
#' @inheritParams add_setbacks
#'
#' @return
#' Returns TRUE or FALSE stating whether or not the building would be allowed in the district based on lot coverage.
#' @export
#'
check_lot_coverage <- function(tidybuilding, tidydistrict, tidyparcel){
  structure_constraints <- fromJSON(tidydistrict$structure_constraints)

  if (length(tidybuilding$geometry) == 1){
    footprint <- st_area(tidybuilding)
  } else if (length(tidybuilding$total_floors) == 1 & length(tidybuilding$floor_area) == 1){
    floors <- tidybuilding$total_floors[[1]]
    fl_area <- tidybuilding$floor_area[[1]]
    footprint <- set_units(fl_area / floors, "ft2")
    footprint <- set_units(footprint, "m2")
  } else{
    return(TRUE)
    warning("No floor area found in tidybuilding")
  }

  lot_coverage <- footprint * 100 / st_area(tidyparcel)

  zoning_req <- get_zoning_req(tidybuilding, tidydistrict, tidyparcel)
  if (class(zoning_req) == "character"){
    return(TRUE)
    warning("No zoning requirements recorded for this district")
  }

  if ("lot_coverage" %in% zoning_req$constraint_name){
    min_lot_coverage <- zoning_req[zoning_req$constraint_name == "lot_coverage", "min_value"]
    max_lot_coverage <- zoning_req[zoning_req$constraint_name == "lot_coverage", "max_value"]

    if (is.na(min_lot_coverage)){
      min_lot_coverage <- 0
    }

    if (is.na(max_lot_coverage)){
      max_lot_coverage <- 100
    }

    return(lot_coverage >= min_lot_coverage & lot_coverage <= max_lot_coverage)

  } else{
    return(TRUE)
  }

}
