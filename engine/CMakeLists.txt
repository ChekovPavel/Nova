cmake_minimum_required(VERSION 3.16)
project(nova_engine VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

# Compiler flags
set(CMAKE_CXX_FLAGS_RELEASE "-O3 -march=native -DNDEBUG")
set(CMAKE_CXX_FLAGS_DEBUG   "-g -fsanitize=address,undefined")

# ---- Shared library -------------------------------------------------------
add_library(nova_engine SHARED
    nova_engine.cpp
    src/transformer.cpp
)

target_include_directories(nova_engine
    PUBLIC  ${CMAKE_CURRENT_SOURCE_DIR}/include
    PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/src
)

set_target_properties(nova_engine PROPERTIES
    OUTPUT_NAME          "nova_engine"
    PREFIX               ""               # strip "lib" prefix for ctypes
    POSITION_INDEPENDENT_CODE ON
)

# Optional: OpenMP for parallel matmul
find_package(OpenMP QUIET)
if(OpenMP_CXX_FOUND)
    target_link_libraries(nova_engine PRIVATE OpenMP::OpenMP_CXX)
    message(STATUS "OpenMP: enabled")
endif()

# ---- Install --------------------------------------------------------------
include(GNUInstallDirs)
install(TARGETS nova_engine
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
)
install(FILES include/nova_engine.h
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
)
