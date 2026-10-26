// float do_stuff(float a, float b, float c, float d) {
int do_stuff(int a, int b, int c, int d) {
    int a1, a2, a3, a4, a5;
    // float a1, a2, a3, a4, a5;

    //only add
    // a1 = a + b;
    // a2 = c + d;
    // a3 = a1 + b;
    // a4 = a2 + b;

    //how the order actually is in assembly for the do_stuff block0:
    // a1 = a + b;
    // a3 = a1 + a;
    // a2 = c + d;
    // a4 = a2 + b;

    //to actually test it

    //hopefully: packet 1
    a1 = a + b;
    a2 = c * d;

    //hopefully: packet 2
    a3 = a1 + b;
    a4 = a2 * b;

    //didn't work because of the difference in latency, the solution it emmitted
    //was one of several options that all had the same total latency for the block
    //trying again with bf16 because offers instructions in differnt FU's of same latency
    // a1 = a + b; //latency 5
    // a2 = sqrt(c); //latency 5 not dependent on a1
    // a3 = a1 + b; //latency 5 dependent on a1
    // a4 = d / a2; //latency 5 dependent on a2

    //instead of the instruction selector re-ordering them
    //such that it is
    //a1 calc
    //a3 calc
    //a2 calc
    //a4 calc
    // and then packetizer makes 4 packets instead of 2

    a5 = a3 + a4;
    return a5;
}


int main() {
    // float a = 1.0;
    // float b = 2.0;
    // float c = 3.0;
    // float d = 4.0;
    // float e = do_stuff(a,b,c,d);
    int a = 1;
    int b = 2;
    int c = 3;
    int d = 4;
    int e = do_stuff(a,b,c,d);
    return 0;
}