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

## Current limitations

Below is a list of what is currently not supported by the compiler, but is planned to be added in future releases.

* Global variables
* Function inlining
* Passing non-scalar values to functions by value, such as `vec` datatype values
* Linking files with multiple functions in 1 file (works with -S flag)
* Some operations, such as SDMA and vreg_ld can only be called via inline ASM. Intrinsics will be added in the future.
* Packetization is currently handled by the emulator's build file. Please run the -S output assembly through that to run the code on the emulator

## Contributing

If you find any bugs, incorrect outputs, or would like to request any new feature, please open an Issue with a description of the problem in this GitHub repository.