#' Compare building bedrooms per unit and allowed bedrooms
#'
#' `check_bedrooms()` takes a tidybuilding and a tidydistrict to see if the district's zoning code allows the tidybuilding based on number of bedrooms.
#'
#' @inheritParams add_setbacks
#'
#' @return
#' Returns TRUE or FALSE stating whether or not the building would be allowed in the district based on the bedrooms in each unit.
#' @export
#'
check_bedrooms <- function(tidybuilding, tidydistrict){
  structure_constraints <- fromJSON(tidydistrict$structure_constraints)

  bed_list <- c(units_0bed = 0,
                units_1bed = 1,
                units_2bed = 2,
                units_3bed = 3,
                units_4bed = 4)

  if (length(names(tidybuilding)[names(tidybuilding) %in% names(bed_list)])){
    min_beds <- min(bed_list[names(tidybuilding)], na.rm = T)
    max_beds <- max(bed_list[names(tidybuilding)], na.rm = T)
  } else{
    return(TRUE)
  }

  zoning_req <- get_zoning_req(tidybuilding, tidydistrict)

  if (class(zoning_req) == "character"){
    return(TRUE)
    warning("No zoning requirements recorded for this district")
  }

  if ("bedrooms" %in% zoning_req$constraint_name){
    min_bedrooms <- zoning_req[zoning_req$constraint_name == "bedrooms", "min_value"]
    max_bedrooms <- zoning_req[zoning_req$constraint_name == "bedrooms", "max_value"]

    if (is.na(min_bedrooms)){
      min_bedrooms <- 0
    }

    if (is.na(max_bedrooms)){
      max_bedrooms <- 100
    }

    return(min_beds >= min_bedrooms & max_beds <= max_bedrooms)

  } else{
    return(TRUE)
  }

}
