#' Quickly visualize sf objects
#'
#' @description
#' A quick way to visualize up to four different shapes using ggplot
#'
#' @param shape1 An sf object
#' @param shape2 An sf object
#' @param shape3 An sf object
#' @param shape4 An sf object
#'
#' @return
#' Returns a simple plot with the different shapes, each a different color
#' @export
#'
show_shapes <- function(shape1, shape2 = NA, shape3 = NA, shape4 = NA){
  shape_list <- list(shape1,shape2,shape3,shape4)
  num_na <- shape_list[is.na(shape_list)] |> length()

  if (num_na == 3){
    ggplot(shape1) +
      geom_sf(fill = "red",alpha = .5, color = "red4") +
      theme_minimal()
  } else if (num_na == 2){
    ggplot(shape1) +
      geom_sf(fill = "red",alpha = .5, color = "red4") +
      geom_sf(data = shape2, fill = "blue",alpha = .5, color = "blue4") +
      theme_minimal()
  } else if (num_na == 1){
    ggplot(shape1) +
      geom_sf(fill = "red",alpha = .5, color = "red4") +
      geom_sf(data = shape2, fill = "blue",alpha = .5, color = "blue4") +
      geom_sf(data = shape3, fill = "green",alpha = .5, color = "green4") +
      theme_minimal()
    } else if (num_na == 0){
    ggplot(shape1) +
      geom_sf(fill = "red",alpha = .5, color = "red4") +
      geom_sf(data = shape2, fill = "blue",alpha = .5, color = "blue4") +
      geom_sf(data = shape3, fill = "green",alpha = .5, color = "green4") +
      geom_sf(data = shape4, fill = "yellow",alpha = .5, color = "yellow4") +
      theme_minimal()
  }
}
