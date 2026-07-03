cmake_minimum_required(VERSION 3.10)
project(lanelog_curator)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(ament_cmake REQUIRED)
find_package(lanelet2_core REQUIRED)
find_package(lanelet2_io REQUIRED)
find_package(lanelet2_projection REQUIRED)

add_executable(lanelog_curator
  src/main.cpp
)

ament_target_dependencies(lanelog_curator
  lanelet2_core
  lanelet2_io
  lanelet2_projection
)

install(TARGETS
  lanelog_curator
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()