# AtallaC Reference Kernels

Fixed-size, human-readable AtallaC implementations of each kernel type.
These serve as ground truth for the compiler pipeline:

```
.c  →  ppci atalla_cc  →  .s  →  build_compiler  →  .in  →  functional_sim
```

## Kernels

| File | Op | Config |
|---|---|---|
| `relu.c` | ReLU (element-wise) | 4×32 tile |
| `gemm_tiled_baseline.c` | Tiled GEMM C += A×W | rolled loops, no K prefetch |
| `gemm_tiled_pipelined.c` | Tiled GEMM | K-tile W prefetch, rolled inner loops |
| `gemm_tiled_pipelined_unrolled.c` | Tiled GEMM | prefetch + TILE=4 manual unroll |
| `softmax.c` | Softmax (rmax/exp/rsum/rcp) | 1×32 vector |
| `maxpool.c` | MaxPool2D (vertical max only) | 8×8→4×8, pool=2, stride=2 |
| `conv_baseline.c` | Conv-as-GEMM (im2col) | rolled loops |
| `conv_pipelined.c` | Conv-as-GEMM | prefetch next (a,c) row |
| `conv_pipelined_unrolled.c` | Conv-as-GEMM | prefetch + M/K_out unroll |
| `layernorm.c` | LayerNorm (mean/var/normalize) | 4×32 tile, eps+inv_n2 in data mem |

## Notes

- All kernels use `ADDR_TABLE = 0x3C` (60) for parameter passing via DRAM.
- `sdma_ctl` values are hardcoded for the fixed tile sizes.
- Maxpool horizontal stride-select is done in post-processing (ppci lacks `shift.vi`/`vmov.vts`).
- LayerNorm and Softmax use `stbf_s`/`rcp_bf`/`bfts_s` and `SQRT` which are currently unsupported by ppci.
- The parameterised versions used by the pipeline are in `atalla-models/atalla-graph/kernels/*.py`.
- See `ENCODER_RECONCILIATION.md` for details on the `.s`→`.in` encoding path comparison.
- Run `validate_and_benchmark.py --preset gemm-variants` or `--preset conv-variants` to compare perf across the three variants.
