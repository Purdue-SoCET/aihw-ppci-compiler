# Atalla C Compiler

This is a compiler intended for usage by the Atalla AI Accelerator. As its frontend, it targets an extended version of C called AtallaC, where stdlib calls are not supported, and certain new intrinsic functions exist. See `atalla_tests` subdirectory for example AtallaC code.

## Installation

There is a provided script called `atalla_cc`. This is the main entry point for the compiler.

To run `atalla_cc`, do the following:

1. Install dependencies: run `pip install -r requirements.txt`

2. Make script executable: run `chmod +x atalla_cc`

3. Verify usage by running `./atalla_cc -h`. This will show further usage instructions and available flags.


## Example Usage

Compile 1 file to assembly:

```
./atalla_cc -S atalla_tests/sample.c
```

Compile & Link multiple files, with output to sample.elf:

```
./atalla_cc atalla_tests/sample.c atalla_tests/instructtest.c -o sample.elf
```

## Intrinsic Usage

We provide the following intrisic functions to be used by the programmer to perform certian operations.

```c
/**
 * @brief Perform vector operation
 *
 * This function performs a vector-vector, vector-scalar, or vector-immediate operation. Note that this should only be used in combination with a specific mask. If you wish to use a binary operator on the entire vectors, simply use the binary operator like you would add together 2 integers.
 *
 * @param op Operator to be performed, must be one of the following:
 * - op = ["+","-", "|","<<","*","&",">>","/","^","GEMM","EXP","SQRT","~","RSUM","RMIN","RMAX",]
 * @param v1 Vector operand
 * @param v2 Vector operand
 * @param f1 Float operand (can be both a variable and a constant)
 * @param mask Mask
 * @return Vector that stores the output of the operation
 */
vec_op_masked(char* op, vec v1, vec v2, int mask);
vec_op_masked(char* op, vec v1, float f1, int mask);


/**
 * @brief Create a mask
 *
 * This function creates a mask from a vector-vector or vector-scalar comparison.
 *
 * @param op Operator to be performed, must be one of the following:
 * - op = [">", "<", "==", "!="]
 * @param v1 Vector operand
 * @param v2 Vector operand
 * @param f1 Float operand (can be both a variable and a constant)
 * @param mask Mask
 * @return Integer that stores the created mask
 */
make_mask(char* op, vec v1, vec v2, int mask);
make_mask(char* op, vec v1, float f1, int mask);

/**
 * @brief Perform GEMM on 2 vectors
 *
 * This function performs GEMM on 2 vectors.
 *
 * @param v1 Vector operand
 * @param v2 Vector operand
 * @param mask Mask
 * @return Vector that stores the result of the GEMM
 */
gemm(vec v1, vec v2, int mask)
```

## Current limitations

Below is a list of what is currently not supported by the compiler, but is planned to be added in future releases.

* Global variables
* Function inlining
* Void return functions broken
* Passing non-scalar values to functions by value, such as `vec` datatype values
* Linking files with multiple functions in 1 file (works with -S flag)
* Some operations, such as SDMA and vreg_ld can only be called via inline ASM. Intrinsics will be added in the future.
* Packetization is currently handled by the emulator's build file. Please run the -S output assembly through that to run the code on the emulator

## Contributing

If you find any bugs, incorrect outputs, or would like to request any new feature, edit or intrinsic, please ping the Compilers channel and then open an Issue with a description of the problem in this GitHub repository.