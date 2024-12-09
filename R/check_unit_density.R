#' Compare building's unit density and allowed unit_density
#'
#' `check_unit_density()` takes a tidybuilding and a tidydistrict to see if the district's zoning code allows the tidybuilding based on unit density.
#'
#' @inheritParams add_setbacks
#'
#' @return
#' Returns TRUE or FALSE stating whether or not the building would be allowed in the district based on unit density.
#' @export
#'
check_unit_density <- function(tidybuilding, tidydistrict){
  structure_constraints <- fromJSON(tidydistrict$structure_constraints)

  tidybuilding_no_geometry <- tidybuilding |>
    st_set_geometry(NULL)

  unit_list <- c("units_0bed",
                "units_1bed",
                "units_2bed",
                "units_3bed",
                "units_4bed")

  unit_count <- tidybuilding_no_geometry[,names(tidybuilding_no_geometry) %in% unit_list] |> sum()

  acres <- st_area(tidybuilding) / 4046.86

  unit_density <- unit_count / acres #units per acre

  zoning_req <- get_zoning_req(tidybuilding, tidydistrict)
  if (class(zoning_req) == "character"){
    warning("No zoning requirements recorded for this district")
    return(TRUE)
  }

  if ("unit_density" %in% zoning_req$constraint_name){
    min_unit_density <- zoning_req[zoning_req$constraint_name == "unit_density", "min_value"]
    max_unit_density <- zoning_req[zoning_req$constraint_name == "unit_density", "max_value"]

    if (is.na(min_unit_density)){
      min_unit_density <- 0
    }

    if (is.na(max_unit_density)){
      max_unit_density <- 1000000
    }

    return(unit_density >= min_unit_density & unit_density <= max_unit_density)

  } else{
    return(TRUE)
  }

}
