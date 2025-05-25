cmake_minimum_required(VERSION 3.15)
project(cum VERSION 1.0.29 LANGUAGES CXX)

add_library(cum INTERFACE)

target_include_directories(cum INTERFACE
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/src>
    $<INSTALL_INTERFACE:include>)

install(
    DIRECTORY src/cum
    DESTINATION include
    FILES_MATCHING PATTERN "*.hpp")

install(
    TARGETS cum
    EXPORT cum
    INCLUDES DESTINATION include
)

include(CMakePackageConfigHelpers)

write_basic_package_version_file(
    ${CMAKE_CURRENT_BINARY_DIR}/cumConfigVersion.cmake
    VERSION ${PROJECT_VERSION}
    COMPATIBILITY SameMajorVersion)

configure_package_config_file(
    ${CMAKE_CURRENT_SOURCE_DIR}/Config.cmake.in
    ${CMAKE_CURRENT_BINARY_DIR}/cumConfig.cmake
    INSTALL_DESTINATION lib/cmake/cum)

install(
    FILES
        ${CMAKE_CURRENT_BINARY_DIR}/cumConfig.cmake
        ${CMAKE_CURRENT_BINARY_DIR}/cumConfigVersion.cmake
    DESTINATION lib/cmake/cum)

install(
    EXPORT cum
    FILE cumTargets.cmake
    NAMESPACE cum::
    DESTINATION lib/cmake/cum)
