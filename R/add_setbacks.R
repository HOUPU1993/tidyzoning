#' Add setback column to tidyparcel object
#'
#' `add_setbacks()` returns the tidyparcel object with new columns describing the setback and units of each side.
#'
#'
#' @param tidyparcel A tidyparcel object is an simple features object depicting each side of a parcel and its label (front, Interior side, Exterior side, rear).
#' @param tidydistrict The tidydistrict corresponding to the tidyparcel. A tidydistrict object is one row from a tidyzoning simple features object.
#' @param tidybuilding A tidybuilding object is a special features object representing a building.
#'
#' @return Returns the tidyparcel object with a "setbacks" and "units" column added to the end.
#' @export
#'


add_setbacks <- function(tidyparcel, tidydistrict, tidybuilding){
  tidyparcel <- tidyparcel[tidyparcel$side != "centroid",]
  tidyparcel <- tidyparcel[!is.na(tidyparcel$side),]
  zoning_req <- get_zoning_req(tidybuilding, tidyparcel, tidydistrict)

  if (class(zoning_req) == "character"){
    tidyparcel$setback <- NA
    tidyparcel$units <- NA
    return(tidyparcel)
  }

  name_key <- c(front = "setback_front",
                `Interior side` = "setback_side_int",
                `Exterior side` = "setback_side_ext",
                rear = "setback_rear")
  for (i in 1:nrow(tidyparcel)){
    side_type <- tidyparcel[[i,"side"]]
    filtered_constraints <- zoning_req |>
      filter(constraint_name == name_key[[side_type]])

    if (nrow(filtered_constraints) > 0){
      setback_value <- filtered_constraints[1,"min_value"]

      tidyparcel[i,"setback"] <- setback_value
      tidyparcel[i,"units"] <- filtered_constraints[1,"units"]
    } else {
      tidyparcel[i,"setback"] <- NA
      tidyparcel[i,"units"] <- NA
    }
  }

  tidyparcel
}

#
# parcel_ids <- unique(tidyparcel_for_testing$parcel_id)
# district_idx <- c()
# for (i in 1:length(parcel_ids)){
#   parcel <- tidyparcel_for_testing |>
#     filter(parcel_id == parcel_ids[[i]])
#   district_idx <- c(district_idx, find_district_idx(parcel, tidyzoning_for_testing))
#
# }
#
# tidyparcel <- tidyparcel_for_testing |>
#   filter(parcel_id == parcel_ids[[3]]) |>
#   filter(side != "centroid")
#
# tidydistrict <- tidyzoning_for_testing[district_idx[[2]],]
#
# tidybuilding <- tidybuilding_ex
#
# tidyparcel_for_testing |>
#   filter(parcel_id == parcel_ids[[2]]) |>
#   ggplot() +
#   geom_sf(aes(color = side))
#
#
# land_use_check <- c()
# for (i in 1:length(parcel_ids)){
#   district <- tidyzoning_for_testing[district_idx[[i]],]
#   land_use_check <- c(land_use_check, check_land_use(tidybuilding, district))
# }
#
# parcel_with_setbacks <- add_setbacks(tidyparcel, tidydistrict, tidybuilding)
#
# buildable_area <- get_buildable_area(parcel_with_setbacks)
#
# show_shapes(tidyparcel, buildable_area)
#
# check_footprint(tidybuilding,buildable_area)

