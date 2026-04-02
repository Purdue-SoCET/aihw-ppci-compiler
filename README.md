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
vec vec_op_masked(char* op, vec v1, vec v2, int mask);
vec vec_op_masked(char* op, vec v1, float f1, int mask);


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
int make_mask(char* op, vec v1, vec v2, int mask);
int make_mask(char* op, vec v1, float f1, int mask);

/**
 * @brief Load model weights
 *
 * This function emits the lw_vi instruction.
 *
 * @param v Vector operand containing load configuration
 * @return No return value
 */
void load_weights(vec v);

/**
 * @brief Trigger scratchpad load operation
 *
 * This function emits the scpad_ld operation.
 *
 * @param rs1_rd1 Scratchpad Address
 * @param rs2 DRAM Address
 * @param rs3 Metadata to be packed: 31:30 - Scratchpad ID, 
                                     29:25 - num rows, 
                                     24:20 - num cols, 
                                     19:0 - num cols in full matrix.
 * @return No return value
 */
void scpad_load(int x, int y, int z);


/**
 * @brief Trigger scratchpad store operation
 *
 * This function emits the scpad_st operation.
 *
 * @param rs1_rd1 Scratchpad Address
 * @param rs2 DRAM Address
 * @param rs3 Metadata to be packed: 31:30 - Scratchpad ID, 
                                     29:25 - num rows, 
                                     24:20 - num cols, 
                                     19:0 - num cols in full matrix.
 * @return No return value
 */
void scpad_store(int x, int y, int z);

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
vec gemm(vec v1, vec v2, int mask);

/**
 * @brief Load a vector from scratchpad
 *
 * This function emits a vector load instruction and returns the loaded vector.
 *
 * @param addr Base address register value
 * @param num_rows Number of rows field
 * @param num_cols Number of columns field
 * @param sid Scratchpad ID
 * @return Loaded vector value
 */
vec vector_load(int addr, int num_rows, int num_cols, int sid);

/**
 * @brief Store a vector to scratchpad
 *
 * This function emits a vector store instruction.
 *
 * @param v Vector to store
 * @param addr Base address register value
 * @param num_rows Number of rows field
 * @param num_cols Number of columns field
 * @param sid Scratchpad ID
 */
void vector_store(vec v, int addr, int num_rows, int num_cols, int sid);

/**
 * @brief Compute scalar square root on bf16 float
 *
 * This function emits the scalar sqrt_bf instruction.
 *
 * @param x Float input value
 * @return Float square root result
 */
float sqrt(float x);
```

## Current limitations

Below is a list of what is currently not supported by the compiler, but is planned to be added in future releases.

* Global variables
* Function inlining
* ~~Void return functions broken~~ FIXED in release: v0.9.1
* Passing non-scalar values to functions by value, such as `vec` datatype values
    * **Workaround**: pass vectors by address, not by value
* Linking files with multiple functions in 1 file (works with -S flag)
* ~~Some operations, such as SDMA and vreg_ld can only be called via inline ASM. Intrinsics will be added in the future.~~ FIXED in release: v0.9.1
* Packetization is currently handled by the emulator's build file. Please run the -S output assembly through that to run the code on the emulator

## Contributing

If you find any bugs, incorrect outputs, or would like to request any new feature, edit or intrinsic, please ping the Compilers channel and then open an Issue with a description of the problem in this GitHub repository.