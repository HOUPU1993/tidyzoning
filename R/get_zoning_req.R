#' Get district zoning requirements
#'
#' Because many zoning requirements depend on the proposed building or the parcel of that zoning district, `the get_zoning_req()` function takes a tidybuilding, a tidyparcel, and a tidydistrict and outputs a data frame listing the set zoning requirements that those three objects would create.
#' If every value is NA, it could indicate that the building land use is not allowed in the zoning district.
#'
#' @inheritParams add_setbacks
#'
#' @return
#' Returns a data frame with the value each zoning requirement for that specific building, parcel, and zoning district.
#' NA values indicate the requirement isn't recorded in that district.
#' If every value is NA, it could indicate that the building land use is not allowed in the zoning district.
#' @export
#'
get_zoning_req <- function(tidybuilding, tidydistrict, tidyparcel = NULL){
  # make tidydistrit a nested list instead of sf object
  tidydistrict <- list(lot_constraints = fromJSON(tidydistrict$lot_constraints),
                       structure_constraints = fromJSON(tidydistrict$structure_constraints),
                       other_constraints = fromJSON(tidydistrict$other_constraints))

  # What are the constraints that are recorded?
  # These three dfs will be appended and combined in the end

  zoning_constraints <- list()
  for (i in 1:length(tidydistrict)){
    if (length(tidydistrict[[i]]) > 0){
      constraints <- data.frame(constraint_name = names(tidydistrict[[i]]),
                                min_value = NA,
                                max_value = NA,
                                units = NA)
      constraint_name <- names(tidydistrict)[[i]]
      zoning_constraints[[constraint_name]] <- constraints
    }
  }

  if (nrow(bind_rows(zoning_constraints)) == 0){
    return("No zoning requirements recorded for this district")
  }

  # Name the building type
  bldg_type <- find_bldg_type(tidybuilding)

  if (is.null(tidyparcel)){
    lot_width <- NA
    lot_depth <- NA
    lot_area <- NA
  } else{
    # establish the parcel variables that might be used in the equations
    front_of_parcel <- tidyparcel |>
      filter(side == "front")
    side_of_parcel <- tidyparcel |>
      filter(side == "Interior side")
    parcel_without_centroid <- tidyparcel |>
      filter(!is.na(side)) |>
      filter(side != "centroid")

    lot_width <- st_length(front_of_parcel) * 3.28084 # converting to ft
    units(lot_width) <- "ft"
    lot_depth <- st_length(side_of_parcel) * 3.28084 # converting to ft
    units(lot_depth) <- "ft"
    lot_area <- st_polygonize(st_union(parcel_without_centroid)) |> st_area() * 10.7639 # converting to ft
    units(lot_area) <- "ft^2"
  }

  # establish the building variables that might be used in the equations
  bed_list <- c(units_0bed = 0,
                units_1bed = 1,
                units_2bed = 2,
                units_3bed = 3,
                units_4bed = 4)

  bedrooms <- max(bed_list[names(tidybuilding)], na.rm = T)
  units_0bed <- ifelse(length(tidybuilding$units_0bed) > 0, tidybuilding$units_0bed, 0)
  units_1bed <- ifelse(length(tidybuilding$units_1bed) > 0, tidybuilding$units_1bed, 0)
  units_2bed <- ifelse(length(tidybuilding$units_2bed) > 0, tidybuilding$units_2bed, 0)
  units_3bed <- ifelse(length(tidybuilding$units_3bed) > 0, tidybuilding$units_3bed, 0)
  units_4bed <- ifelse(length(tidybuilding$units_4bed) > 0, tidybuilding$units_4bed, 0)
  total_units <- units_0bed + units_1bed + units_2bed + units_3bed + units_4bed
  fl_area <- ifelse(length(tidybuilding$floor_area) > 0, tidybuilding$floor_area, NA)
  parking_open <- ifelse(length(tidybuilding$parking_open) > 0, tidybuilding$parking_open, NA)
  parking_enclosed <- ifelse(length(tidybuilding$parking_enclosed) > 0, tidybuilding$parking_enclosed, NA)
  parking <- ifelse(length(tidybuilding$parking) > 0, tidybuilding$parking, NA)
  height <- ifelse(length(tidybuilding$height) > 0, tidybuilding$height, NA)
  floors <- ifelse(length(tidybuilding$floors) > 0, tidybuilding$floors, NA)
  min_unit_size <- ifelse(length(tidybuilding$min_unit_size) > 0, tidybuilding$min_unit_size, NA)
  max_unit_size <- ifelse(length(tidybuilding$max_unit_size) > 0, tidybuilding$max_unit_size, NA)
  far <- fl_area / lot_area

  # loop through each zoning regulation in the district
  warnings <- 0 # if tidyparcel == NULL, this will keep track of potential incorrect calculations
  for (k in 1:length(zoning_constraints)){
    constraints <- zoning_constraints[[k]]

    # listing constraints
    for (i in 1:nrow(constraints)){
      name <- names(zoning_constraints)[[k]]
      for (j in 1:length(tidydistrict[[name]][[i]])){
        use_name <- tidydistrict[[name]][[i]][[j]]$use_name
        if (bldg_type %in% use_name){
          use_index <- j
          break
        }else {
          use_index <- NA
        }
      }
      if (is.na(use_index)){
        break
      }
      constraint_info <- tidydistrict[[name]][[i]][[use_index]]

      # Looking at possible min values
      if (length(constraint_info$min_val[[1]]) == 1){ # this is just a one-line expression for the constraint
        constraint_min_val <- parse(text = constraint_info$min_val[[1]]) |>
          eval()

      } else if (length(constraint_info$min_val) == 0){
        constraint_min_val <- NA

      } else{ # this indicates a rule of some kind
        # loop through each rule
        for (j in 1:length(constraint_info$min_val)){
          rule_items <- names(constraint_info$min_val[[j]])
          if ("logical_operator" %in% rule_items ){
            if (constraint_info$min_val[[j]]$logical_operator == "AND"){
              logical_operator <- "&"
            } else{
              logical_operator <- "|"
            }
            if ("select" %in% rule_items){ # there is logical_op and there is a select
              conditions_value <- parse(text = paste(constraint_info$min_val[[j]]$conditions,
                                                     collapse = logical_operator)) |>
                eval()

              expressions <- c()
              for (i in 1:length(constraint_info$min_val[[j]]$expressions)){
                expressions <- c(expressions, eval(parse(text = constraint_info$min_val[[j]]$expressions[i])))
              }
              if (conditions_value == TRUE){
                if (constraint_info$min_val[[j]]$select == "min"){
                  constraint_min_val <- min(expressions)
                  break
                } else{
                  constraint_min_val <- max(expressions)
                  break
                }
              }
            } else{ # there is logical_op and just one expression at end
              constraint_min_val <- parse(text = constraint_info$min_val[[j]]$expression) |>
                eval()
              break
            }
          } else{
            if ("select" %in% rule_items){ # not logical_op, but there is a select
              if ("conditions" %in% rule_items){ # There is still a condition before selecting
                # there is logical_op and there is a select
                conditions_value <- parse(text = constraint_info$min_val[[j]]$conditions) |>
                  eval()

                expressions <- c()
                for (i in 1:length(constraint_info$min_val[[j]]$expressions)){
                  expressions <- c(expressions, eval(parse(text = constraint_info$min_val[[j]]$expressions[i])))
                }

                if (conditions_value == TRUE){
                  if (constraint_info$min_val[[j]]$select == "min"){
                    constraint_min_val <- min(expressions)
                    break
                  } else{
                    constraint_min_val <- max(expressions)
                    break
                  }
                }
              } else{ # it is just a select with the expressions
                expressions <- c()
                for (i in 1:length(constraint_info$min_val[[j]]$expressions)){
                  expressions <- c(expressions, eval(parse(text = constraint_info$min_val[[j]]$expressions[i])))
                }
                if (constraint_info$min_val[[j]]$select == "min"){
                  constraint_min_val <- min(expressions)
                  break
                } else{
                  constraint_min_val <- max(expressions)
                  break
                }
              }
            } else{ # no logical_op and no select
              conditions_value <- parse(text = constraint_info$min_val[[j]]$conditions) |>
                eval()
              if (conditions_value == TRUE){
                constraint_min_val <- parse(text = constraint_info$min_val[[j]]$expression) |>
                  eval()
                break
              }
            }
          }

        }
      }

      # Looking at possible max values
      if (length(constraint_info$max_val[[1]]) == 1){ # this is just a one-line expression for the constraint
        constraint_max_val <- parse(text = constraint_info$max_val[[1]]) |>
          eval()
      } else if (length(constraint_info$max_val) == 0){
        constraint_max_val <- NA
      } else{ # this indicates a rule of some kind
        # loop through each rule
        for (j in 1:length(constraint_info$max_val)){
          rule_items <- names(constraint_info$max_val[[j]])
          if ("logical_operator" %in% rule_items ){
            if (constraint_info$max_val[[j]]$logical_operator == "AND"){
              logical_operator <- "&"
            } else{
              logical_operator <- "|"
            }
            if ("select" %in% rule_items){ # there is logical_op and there is a select
              conditions_value <- parse(text = paste(constraint_info$max_val[[j]]$conditions,
                                                     collapse = logical_operator)) |>
                eval()

              expressions <- c()
              for (i in 1:length(constraint_info$max_val[[j]]$expressions)){
                expressions <- c(expressions, eval(parse(text = constraint_info$max_val[[j]]$expressions[i])))
              }
              if (conditions_value == TRUE){
                if (constraint_info$max_val[[j]]$select == "min"){
                  constraint_max_val <- min(expressions)
                  break
                } else{
                  constraint_max_val <- max(expressions)
                  break
                }
              }
            } else{ # there is logical_op and just one expression at end
              constraint_max_val <- parse(text = constraint_info$max_val[[j]]$expression) |>
                eval()
              break
            }
          } else{
            if ("select" %in% rule_items){ # not logical_op, but there is a select
              if ("conditions" %in% rule_items){ # There is still a condition before selecting
                # there is logical_op and there is a select
                conditions_value <- parse(text = constraint_info$max_val[[j]]$conditions) |>
                  eval()

                expressions <- c()
                for (i in 1:length(constraint_info$max_val[[j]]$expressions)){
                  expressions <- c(expressions, eval(parse(text = constraint_info$max_val[[j]]$expressions[i])))
                }

                if (conditions_value == TRUE){
                  if (constraint_info$max_val[[j]]$select == "min"){
                    constraint_max_val <- min(expressions)
                    break
                  } else{
                    constraint_max_val <- max(expressions)
                    break
                  }
                }
              } else{ # it is just a select with the expressions
                expressions <- c()
                for (i in 1:length(constraint_info$max_val[[j]]$expressions)){
                  expressions <- c(expressions, eval(parse(text = constraint_info$max_val[[j]]$expressions[i])))
                }
                if (constraint_info$max_val[[j]]$select == "min"){
                  constraint_max_val <- min(expressions)
                  break
                } else{
                  constraint_max_val <- max(expressions)
                  break
                }
              }
            } else{ # no logical_op and no select
              conditions_value <- parse(text = constraint_info$max_val[[j]]$conditions) |>
                eval()
              if (conditions_value == TRUE){
                constraint_max_val <- parse(text = constraint_info$max_val[[j]]$expression) |>
                  eval()
                break
              }
            }
          }

        }
      }

      zoning_constraints[[k]][i,"min_value"] <- constraint_min_val
      zoning_constraints[[k]][i,"max_value"] <- constraint_max_val
      zoning_constraints[[k]][i, "units"] <- constraint_info$unit

      if (is.na(constraint_min_val) & is.na(constraint_max_val) & !is.na(constraint_info$unit)){
        warnings <- warnings + 1
      }

    }
  }


  if (warnings > 0){
    warning("Some values my be inaccurate because they rely on parcel dimmensions")
    return(bind_rows(zoning_constraints))
  } else{
    return(bind_rows(zoning_constraints))
  }

}
