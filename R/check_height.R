#' Compare building height and allowed height
#'
#' `check_height()` takes a tidybuilding and a tidydistrict to see if the district's zoning code allows the tidybuilding based on height.
#'
#' @inheritParams add_setbacks
#'
#' @return
#' Returns TRUE or FALSE stating whether or not the building would be allowed in the district based on building height.
#' @export
#'
check_height <- function(tidybuilding, tidydistrict){
  structure_constraints <- fromJSON(tidydistrict$structure_constraints)

  if (length(tidybuilding$building_height) == 1){
    height <- tidybuilding$building_height[[1]]
  } else if (length(tidybuilding$total_floors) == 1){
    floors <- tidybuilding$total_floors[[1]]
    height <- floors * 12
    warning("Height approximated based on 12 ft floors")
  } else{
    return(TRUE)
    warning("No tidybuilding height recorded")
  }

  zoning_req <- get_zoning_req(tidybuilding, tidydistrict)
  if (class(zoning_req) == "character"){
    return(TRUE)
    warning("No zoning requirements recorded for this district")
  }

  if ("height" %in% zoning_req$constraint_name){
    min_height <- zoning_req[zoning_req$constraint_name == "height", "min_value"]
    max_height <- zoning_req[zoning_req$constraint_name == "height", "max_value"]

    if (is.na(min_height)){
      min_height <- 0
    }

    if (is.na(max_height)){
      max_height <- 1000000
    }

    # change height units to match the ones recorded in the code
    if (!is.na(zoning_req[zoning_req$constraint_name == "height", "units"])){
      height <- set_units(height, "ft")
      height_units <- zoning_req[zoning_req$constraint_name == "height", "units"]
      units(max_height) <- height_units
      units(min_height) <- height_units
      max_height <- set_units(max_height, "ft")
      min_height <- set_units(min_height, "ft")
    }

    return(height >= min_height & height <= max_height)

  } else{
    return(TRUE)
  }

}
