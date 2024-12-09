#' Check if footprint fits in buildable area
#'
#' `check_footprint()` takes a building footprint from tidybuilding object and checks to see if it will fit in the provided buildable area. The buildable area can be any shape.
#'
#' @inheritParams add_setbacks
#' @inheritParams check_footprint_simple
#' @param num_rotations The number of rotations you wish to spin the building footprint. More rotations will be more accurate, but will cost significantly more time.
#' Ex: if `num_rotations = 4` then the building footprint will be turned 90 degrees each time until it finds where it fits.
#' Ex: if `num_rotations = 24` then the building footprint will be turned 15 degrees each time until it finds where it fits.
#'
#' @return
#' Returns TRUE of FALSE stating whether or not the building footprint would fit in the buildable area.
#' @export
#'
check_footprint <- function(tidybuilding, buildable_area, num_rotations = 24){
  # change crs so it is working in feet
  # (we may want to change this someday)
  if (is.na(st_crs(buildable_area)) & is.na(st_crs(tidybuilding))){
    tidybuilding <- tidybuilding
    buildable_area <- buildable_area
  } else if (is.na(st_crs(buildable_area))){
    tidybuilding <- st_transform(tidybuilding, 2277)
    buildable_area <- st_set_crs(buildable_area, 2277)
  } else if (is.na(st_crs(tidybuilding))){
    tidybuilding <- st_set_crs(tidybuilding, 2277)
    buildable_area <- st_transform(buildable_area, 2277)
  } else{
    tidybuilding <- st_transform(tidybuilding, 2277)
    buildable_area <- st_transform(buildable_area, 2277)
  }

  area_tb <- as.numeric(st_area(tidybuilding)) # area of the tidybuilding footprint
  area_ba <- as.numeric(st_area(buildable_area)) # area of the buildable area

  # make sure the building isn't bigger than the parcel
  if (area_tb > area_ba){
    return(FALSE)
  }

  # rasterize the buildable_area
  # (resolution 3 if it is a big parcel, but 1 if it is smaller)
  if (area_ba > 3000){
    res <- 3
  } else{
    res <- 1
  }

  raster_template <- rast(ext(st_as_sf(buildable_area)), resolution = res)
  build_area_raster <- rasterize(st_as_sf(buildable_area), raster_template,
                                 touches = TRUE) |>
    as.data.frame(xy = TRUE)

  rot_degrees <- seq(0,360,360 / num_rotations)
  # do the process and then rotate the footprint if it doesn't work
  for (j in 1:(length(rot_degrees) - 1)){
    tidybuilding <- rotate_shape(tidybuilding, rot_degrees[j])

    # get a point from tidybuilding outline
    building_points <- tidybuilding[,"geometry"] |>
      st_cast("LINESTRING") |>
      st_cast("POINT")

    one_bldg_point <- building_points[3,]

    # loop through each pixel until it is inside
    for (i in 1:nrow(build_area_raster)){
      footprint <- tidybuilding[,"geometry"]
      pixel_loc <- c(build_area_raster[[i,"x"]], build_area_raster[[i,"y"]])

      # find difference between point and pixel
      diff <- st_geometry(one_bldg_point) - pixel_loc

      # move the tidybuilding
      translated_geometry <- st_geometry(footprint) - diff
      st_geometry(footprint) <- translated_geometry

      # see if the buildable area covers the tidybuilding
      covers <- st_covers(buildable_area, st_set_crs(footprint,st_crs(buildable_area)), sparse = F)

      # change output to TRUE once it is inside the buildable area
      if (covers[[1]] == TRUE){
        return(TRUE)
      }
    }
  }
  return(FALSE)
}

# ggplot(build_area_raster) +
#   geom_tile(aes(x = x, y = y)) +
#   geom_sf(data = footprint, color = "red4", fill = "red", alpha = .5)
#



# #
# tidybuilding <- tidybuilding_ex
# tidydistrict <- tidyzoning_ex[15,]
# tidyparcel <- tidyparcel_ex[tidyparcel_ex$OBJECTID == 1,]
# #
# #
# #
# # mask <- !is.na(build_area_raster)
# #
# # use_r("check_footprint_simple")
# #
# # rep(1:5,2)
# #
# xmin <- min(build_area_raster$x)
# xmax <- max(build_area_raster$x)
# ymin <- min(build_area_raster$y)
# ymax <- max(build_area_raster$y)
#
# mask <- data.frame(x = rep(xmin:xmax, length(ymin:ymax)),
#                    y = rep(ymin:ymax, each = length(xmin:xmax)))
# #
# # ggplot(mask) +
# #   geom_tile(aes(x = x, y = y), color = "grey") +
# #   geom_tile(data = build_area_raster,aes(x = x, y = y), color = "black")
# #
# build_area_raster <- rasterize(st_as_sf(buildable_area), raster_template,
#                                touches = TRUE) |>
# #   as.data.frame()
# #
# # mask <- !is.na(build_area_raster) |> as.data.frame()
# #
# # nrow(mask)
# # nrow(as.data.frame(build_area_raster))
# #
# # ggplot(mask) +
# #   geom_tile(aes(x = x, y = y), color = "black")
# #
# # show_shapes(buildable_area)
#
#
# show_shapes(tidybuilding)
# show_shapes(tidyparcel)
#
# parcel_with_setbacks <- add_setbacks(tidyparcel,tidydistrict, tidybuilding)
# parcel_with_setbacks[2,"setback"] <- NA
# parcel_with_setbacks[2,"units"] <- NA
#
# buildable_area <- get_buildable_area(parcel_with_setbacks)
#
# show_shapes(parcel_with_setbacks)
# show_shapes(parcel_with_setbacks, buildable_area)
#
# check_footprint(tidybuilding, buildable_area)
#
# check_footprint_simple(buildable_area, 50, 70)
#
# #
# #
# #
# #
# # # This is the outside shape
# # shape_1 <- st_polygon(list(matrix(c(0,0,
# #                                     25,0,
# #                                     25,50,
# #                                     0,50,
# #                                     0,0), byrow = T, ncol = 2)))
# #
# # # A little smaller than shape_1 and rotatad 90 degrees
# # shape_2 <- st_polygon(list(matrix(c(0,0,
# #                                     49,0,
# #                                     49,24,
# #                                     0,24,
# #                                     0,0), byrow = T, ncol = 2)))
# #
# # shape_sf <- st_sf(geometry = st_sfc(shape_1, shape_2))
# #
# # shape1 <- shape_sf[1,"geometry"]
# # shape2 <- shape_sf[2,"geometry"]
# #
# # show_shapes(shape1,shape2)
# #
# # check_footprint(shape1,shape2)
# # check_footprint(shape2,shape1)
#
#
# mask(build_area_raster, raster_template)
#
#

