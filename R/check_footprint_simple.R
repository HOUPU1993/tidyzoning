#' Check if simple footprint fits in buildable area
#'
#' `check_footprint_simple()` takes a rectangular building footprint and checks to see if it will fit in the provided buildable area. The buildable area can be any shape.
#'
#' @param buildable_area A shape depicting the buildable area of a parcel. This is produced by the [get_buildable_area()] function.
#' @param bldg_width_x The width (in feet) of the building footprint
#' @param bldg_length_y The length (in feet) of the building footprint
#'
#' @return
#' Returns TRUE of FALSE stating whether or not the building footprint would fit in the buildable area.
#' @export
#'
check_footprint_simple <- function(buildable_area, bldg_width_x, bldg_length_y){
  # change crs so it is working in feet
  # (we may want to change this someday. Don't know if this is the correct crs)
  buildable_area <- st_transform(buildable_area, 2277)

  area_tb <- bldg_width_x * bldg_length_y # area of the tidybuilding footprint
  area_ba <- as.numeric(st_area(buildable_area)) # area of the buildable area

  # make sure the building isn't bigger than the parcel
  if (area_tb > area_ba){
    return(FALSE)
  }

  rot_degrees <- seq(10,90,10)
  # do the process and then rotate the buildable_area if it doesn't work
  for (i in 1:(length(rot_degrees) + 1)){

    # rasterize the buildable_area
    raster_template <- rast(ext(st_as_sf(buildable_area)), resolution = 1)
    build_area_raster <- rasterize(st_as_sf(buildable_area), raster_template,
                                   touches = TRUE) |>
      as.data.frame(xy = TRUE)

    # loop through each pixel until it is inside
    for (j in 1:nrow(build_area_raster)){

      x <- build_area_raster[[j,"x"]]
      y <- build_area_raster[[j,"y"]]
      bldg_footprint <- data.frame(x = rep(x:(x + bldg_width_x - 1), bldg_length_y),
                                   y = rep(y:(y - bldg_length_y + 1), each = bldg_width_x))

      matching_coords <- merge(bldg_footprint, build_area_raster, by = c("x", "y"))

      # change output to TRUE once it is inside the buildable area
      if (nrow(matching_coords) == nrow(bldg_footprint)){
        return(TRUE)
      }
    }

    # rotate and start again if it hasn't ended yet
    buildable_area <- rotate_shape(buildable_area, rot_degrees[i])
  }
  return(FALSE) # if it hasn't returned true by now
}
#
# system.time(check_footprint_simple(buildable_area, 50, 70))
#
# system.time(check_footprint(tidybuilding,buildable_area))
#
#
# #
# # big_df <- data.frame(x = c(1,2,3,4,5,6,7),
# #                      y = c(1,2,3,4,5,6,7))
# # small_df <- data.frame(x = c(1,2,3,5),
# #                        y = c(1,2,3,5))
# #
# # matching_coords <- merge(small_df, big_df, by = c("x", "y"))
# #
# # nrow(matching_coords) == nrow(small_df)
# #
# #
# ggplot(build_area_raster) +
#   geom_tile(aes(x = x, y = y), fill = "grey") +
#   geom_tile(data = bldg_footprint,aes(x = x, y = y), fill = "black") +
#   geom_tile(data = build_area_raster[j,], aes(x=x, y=y), fill = "red")
#
