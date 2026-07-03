# generated from ament/cmake/core/templates/nameConfig.cmake.in

# prevent multiple inclusion
if(_lanelog_curator_CONFIG_INCLUDED)
  # ensure to keep the found flag the same
  if(NOT DEFINED lanelog_curator_FOUND)
    # explicitly set it to FALSE, otherwise CMake will set it to TRUE
    set(lanelog_curator_FOUND FALSE)
  elseif(NOT lanelog_curator_FOUND)
    # use separate condition to avoid uninitialized variable warning
    set(lanelog_curator_FOUND FALSE)
  endif()
  return()
endif()
set(_lanelog_curator_CONFIG_INCLUDED TRUE)

# output package information
if(NOT lanelog_curator_FIND_QUIETLY)
  message(STATUS "Found lanelog_curator: 0.0.1 (${lanelog_curator_DIR})")
endif()

# warn when using a deprecated package
if(NOT "" STREQUAL "")
  set(_msg "Package 'lanelog_curator' is deprecated")
  # append custom deprecation text if available
  if(NOT "" STREQUAL "TRUE")
    set(_msg "${_msg} ()")
  endif()
  # optionally quiet the deprecation message
  if(NOT lanelog_curator_DEPRECATED_QUIET)
    message(DEPRECATION "${_msg}")
  endif()
endif()

# flag package as ament-based to distinguish it after being find_package()-ed
set(lanelog_curator_FOUND_AMENT_PACKAGE TRUE)

# include all config extra files
set(_extras "")
foreach(_extra ${_extras})
  include("${lanelog_curator_DIR}/${_extra}")
endforeach()
