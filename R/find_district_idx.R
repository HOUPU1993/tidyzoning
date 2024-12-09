#' Find corresponding tidydistrict
#'
#' @description
#' `find_district_idx()` takes in a tidyzoning object and a tidyparcel object.
#' Returns the row number of the district to which the parcel belongs.
#'
#' @inheritParams add_setbacks
#' @param tidyzoning The tidyzoning object is a simple features object with a row for each zoning district and columns holding the geojson formatted zoning requirements of each district.
#'
#' @return The row number of the tidyzoning object that contains the disrict to which the parcel belongs.
#' Returns NA if there is no district found.
#' @export
#'
find_district_idx <- function(tidyparcel, tidyzoning){
  # lists TRUE/FALSE to indicate which tidyzoning geometries cover the parcel centroid
  contains <- st_contains(st_make_valid(tidyzoning), tail(tidyparcel,1), sparse = F)
  # gives the index of the district that covers the centroid
  idx <- as.numeric(row.names(tidyzoning[contains, ]))

  # returns NA if there isn't a unique district covering the parcel centroid
  if (length(idx) == 1){
    print(idx)
  } else {
    print(NA)
  }
}
