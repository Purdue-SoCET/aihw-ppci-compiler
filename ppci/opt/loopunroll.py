# Loop unrolling optimization

# High-level plan for loop unrolling implementation
# 1. Use the built-in control flow graph to get all the loops 
# 2. Connect the loop nodes returned to the IR code that was generated
# 3. Make a decision on which loops to actually unroll (VERY IMPORTANT)
#   3a. Brainstorming: need code size limits, cache size, registers available, to decide whether loop unroll is viable
# 4. Modify the IR code (either manually or using IR functions / api)