// #include <stdio.h>


int main() {
   unsigned int input1 = 10;
   unsigned int input2 = 20;
   unsigned int output;
   asm(
        "add.s %0, %1, %2"
        : "=r"(output)
        : "r"(input1), "r"(input2)
        :
    );
}
