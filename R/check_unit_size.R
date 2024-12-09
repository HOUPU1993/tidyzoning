#' Compare unit sizes and allowed unit sizes
#'
#' `check_unit_size()` takes a tidybuilding and a tidydistrict to see if the district's zoning code allows the tidybuilding based on unit sizes.
#'
#' @inheritParams add_setbacks
#'
#' @return
#' Returns TRUE or FALSE stating whether or not the building would be allowed in the district based on the unit sizes.
#' @export
#'
check_unit_size <- function(tidybuilding, tidydistrict){
  structure_constraints <- fromJSON(tidydistrict$structure_constraints)


  if (length(tidybuilding$max_unit_size) == 1 & length(tidybuilding$min_unit_size) == 1){
    min_size <- tidybuilding$min_unit_size[[1]]
    max_size <- tidybuilding$max_unit_size[[1]]
  } else if (length(tidybuilding$max_unit_size) == 1){
    min_size <- tidybuilding$max_unit_size[[1]]
    max_size <- tidybuilding$max_unit_size[[1]]
  } else if (length(tidybuilding$min_unit_size) == 1){
    min_size <- tidybuilding$min_unit_size[[1]]
    max_size <- tidybuilding$min_unit_size[[1]]
  } else{
    return(TRUE)
  }

  zoning_req <- get_zoning_req(tidybuilding, tidydistrict)
  if (class(zoning_req) == "character"){
    return(TRUE)
    warning("No zoning requirements recorded for this district")
  }

  if ("unit_size" %in% zoning_req$constraint_name){
    min_unit_size <- zoning_req[zoning_req$constraint_name == "unit_size", "min_value"]
    max_unit_size <- zoning_req[zoning_req$constraint_name == "unit_size", "max_value"]

    if (is.na(min_unit_size)){
      min_unit_size <- 0
    }

    if (is.na(max_unit_size)){
      max_unit_size <- 1000000
    }

    if (!is.na(zoning_req[zoning_req$constraint_name == "unit_size", "units"])){
      min_size <- set_units(min_size, "ft2")
      max_size <- set_units(max_size, "ft2")
      unit_size_units <- zoning_req[zoning_req$constraint_name == "unit_size", "units"]

      if (unit_size_units == "square feet"){
        unit_size_units <- "ft2"
      } else if (unit_size_units == "square meters"){
        unit_size_units <- "m2"
      } else if (unit_size_units == "acres"){
        unit_size_units <- "acre"
      }

      units(min_unit_size) <- unit_size_units
      units(max_unit_size) <- unit_size_units
      min_unit_size <- set_units(min_unit_size, "ft2")
      max_unit_size <- set_units(max_unit_size, "ft2")
    }

    return(min_size >= min_unit_size & max_size <= max_unit_size)

  } else{
    return(TRUE)
  }

}

