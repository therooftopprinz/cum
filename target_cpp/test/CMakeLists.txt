find_package(Python3 COMPONENTS Interpreter REQUIRED)

# When CMake is invoked on this directory, CMAKE_SOURCE_DIR is target_cpp/test;
# generators and sample2.cum live at repo root two levels up.
if(CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
  get_filename_component(CUM_ROOT "${CMAKE_CURRENT_LIST_DIR}/../.." ABSOLUTE)
else()
  set(CUM_ROOT "${CMAKE_SOURCE_DIR}")
endif()

set(SAMPLE2_CUM "${CUM_ROOT}/sample2.cum")
set(SAMPLE2_HPP "${CMAKE_CURRENT_SOURCE_DIR}/sample2.hpp")

add_custom_command(
  OUTPUT "${SAMPLE2_HPP}"
  COMMAND
    ${CMAKE_COMMAND} -E env "PYTHONPATH=${CUM_ROOT}/generator"
      bash -c
      "\"${Python3_EXECUTABLE}\" \"${CUM_ROOT}/generator/cum_to_ast.py\" \"${SAMPLE2_CUM}\" | \"${Python3_EXECUTABLE}\" \"${CUM_ROOT}/generator/ast_to_cpp.py\" > \"${SAMPLE2_HPP}\""
  DEPENDS
    "${SAMPLE2_CUM}"
    "${CUM_ROOT}/generator/cum_to_ast.py"
    "${CUM_ROOT}/generator/ast_to_cpp.py"
    "${CUM_ROOT}/generator/ast_normalize.py"
    "${CUM_ROOT}/generator/cpp_generator.py"
  COMMENT "Generating sample2.hpp from sample2.cum"
  VERBATIM
)

add_custom_target(sample2_hpp_generated DEPENDS "${SAMPLE2_HPP}")

add_executable(cum_test_sample2 sample2.cpp)
add_dependencies(cum_test_sample2 sample2_hpp_generated)
target_compile_features(cum_test_sample2 PRIVATE cxx_std_17)
target_include_directories(cum_test_sample2 PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})
if(TARGET cum)
  target_link_libraries(cum_test_sample2 PRIVATE cum)
else()
  target_include_directories(cum_test_sample2 PRIVATE "${CUM_ROOT}/target_cpp")
endif()
