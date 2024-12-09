#' Find land use of a building
#'
#' `find_bldg_type()` takes in a tidybuilding and outputs the land use (1_family, 2_family, etc.).
#'
#' @inheritParams add_setbacks
#'
#' @return A string stating the building land use (1_family, 2_family, etc.).
#' This will match the way land use is written in the tidyzining object.
#' @export
#'
find_bldg_type <- function(tidybuilding){
  possible_columns <- c("units_0bed",
                        "units_1bed",
                        "units_2bed",
                        "units_3bed",
                        "units_4bed")

  tidybuilding <- tidybuilding[,names(tidybuilding) %in% possible_columns] |>
    st_drop_geometry()

  row_sum <- rowSums(tidybuilding)

  if (row_sum %in% c(1,2,3)){
    paste0(row_sum[[1]], "_family")
  } else if (row_sum > 3){
    paste("4_family")
  } else {
    paste("other")
  }
}
