#' Compare building floor count and allowed floors
#'
#' `check_floors()` takes a tidybuilding and a tidydistrict to see if the district's zoning code allows the tidybuilding based on number of floors.
#'
#' @inheritParams add_setbacks
#'
#' @return
#' Returns TRUE or FALSE stating whether or not the building would be allowed in the district based on total floors.
#' @export
#'
check_floors <- function(tidybuilding, tidydistrict){
  structure_constraints <- fromJSON(tidydistrict$structure_constraints)

  if (length(tidybuilding$total_floors) == 1){
    floors <- tidybuilding$total_floors[[1]]
  } else if (length(tidybuilding$building_height) == 1){
    height <- tidybuilding$building_height[[1]]
    floors <- height / 12
    warning("Floors approximated based on 12 ft floors")
  } else{
    return(TRUE)
  }

  zoning_req <- get_zoning_req(tidybuilding, tidydistrict)

  if (class(zoning_req) == "character"){
    return(TRUE)
    warning("No zoning requirements recorded for this district")
  }

  if ("floors" %in% zoning_req$constraint_name){
    min_floors <- zoning_req[zoning_req$constraint_name == "stories", "min_value"]
    max_floors <- zoning_req[zoning_req$constraint_name == "stories", "max_value"]

    if (is.na(min_floors)){
      min_floors <- 0
    }

    if (is.na(max_floors)){
      max_floors <- 326 # double the floors of Burj Khalifa
    }

    return(floors >= min_floors & floors <= max_floors)

  } else{
    return(TRUE)
  }

}
