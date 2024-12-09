#' Create a parcel's buildable area
#'
#' get_buildable_area() takes a tidyparcel object with setback information and produces a polygon representing the builablel area of the parcel.
#'
#' @param tidyparcel_with_setbacks A tidyparcel object that has setback infomration added. tidyparcel_with_setbacks is the output of the [add_setbacks()] function.
#'
#' @return
#' Returns a polygon representing the buildable area of the parcel.
#' @export
#'

get_buildable_area <- function(tidyparcel_with_setbacks){
  # make tidyparcel a polygon
  polygon <- st_polygonize(st_union(tidyparcel_with_setbacks))

  if (nrow(tidyparcel_with_setbacks[!is.na(tidyparcel_with_setbacks$setback),]) == 0){
    return(polygon)
  }

  # convert the setback units to meters
  if (is.na(unique(tidyparcel_with_setbacks$units)[[1]])){
    units(tidyparcel_with_setbacks$setback) <- unique(tidyparcel_with_setbacks$units)[[2]]
  } else{
    units(tidyparcel_with_setbacks$setback) <- unique(tidyparcel_with_setbacks$units)[[1]]
  }


  tidyparcel_with_setbacks <- tidyparcel_with_setbacks |>
    mutate(setback_m = set_units(setback,"m")) |>
    filter(!is.na(setback))

  # put a buffer on each side (need to convert to meters)
  buffered_sides <- tidyparcel_with_setbacks |>
    mutate(geometry = st_buffer(geometry,setback_m,1))

  # make the buffered sides all one polygon
  buffered_polygon <- st_union(buffered_sides)


  # make a new shape the parts not overlapping
  not_overlapping <- st_sym_difference(st_make_valid(buffered_polygon), st_make_valid(polygon))
  not_overlapping <- not_overlapping[st_area(not_overlapping) == max(st_area(not_overlapping))]

  # separate the polygons from the multipolygon
  not_overlapping <- st_cast(not_overlapping, "POLYGON")

  # select the non-overlapping shape that is the buildable area
  buildable_area <- not_overlapping[2]

  buildable_area

  # this stuff I tried to make it a simpler shape, but it sometimes didn't work.

  # # get only the nodes from buildable area that will creat a smooth, accurate line
  # parcel_geometries <- tidyparcel_with_setbacks[,"geometry"]
  # parcel_nodes <- st_cast(parcel_geometries, "POINT")
  # build_area_nodes <- st_cast(buildable_area, "POINT")
  # important_nodes <- st_nearest_feature(parcel_nodes, build_area_nodes)
  #
  # build_area_nodes[important_nodes] |>
  #   st_union() |>
  #   st_cast("MULTILINESTRING") |>
  #   st_cast("POLYGON")

}

