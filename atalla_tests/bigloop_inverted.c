// Branch cleanup test: loop body is under MAX_INVERTED_BRANCH_DISTANCE (128),
// so the header's blt_s + jal pair should become one bge_s to the loop exit.
int main(){
    int a = 1;
    for(int i = 0; i < 10; i++){
        a = a * 2 + i;
        a = a * 3 + i;
        a = a * 4 + i;
        a = a * 5 + i;
        a = a * 6 + i;
        a = a * 7 + i;
        a = a * 8 + i;
        a = a * 2 + i;
        a = a * 3 + i;
        a = a * 4 + i;
        a = a * 5 + i;
        a = a * 6 + i;
        a = a * 7 + i;
        a = a * 8 + i;
        a = a * 2 + i;
        a = a * 3 + i;
        a = a * 4 + i;
        a = a * 5 + i;
        a = a * 6 + i;
        a = a * 7 + i;
        a = a * 8 + i;
        a = a * 2 + i;
        a = a * 3 + i;
        a = a * 4 + i;
        a = a * 5 + i;
        a = a * 6 + i;
        a = a * 7 + i;
        a = a * 8 + i;
        a = a * 2 + i;
        a = a * 3 + i;
        a = a * 4 + i;
        a = a * 5 + i;
        a = a * 6 + i;
        a = a * 7 + i;
        a = a * 8 + i;
        a = a * 2 + i;
        a = a * 3 + i;
        a = a * 4 + i;
        a = a * 5 + i;
        a = a * 6 + i;
        a = a * 7 + i;
        a = a * 8 + i;
        a = a * 2 + i;
        a = a * 3 + i;
        a = a * 4 + i;
        a = a * 5 + i;
        a = a * 6 + i;
        a = a * 7 + i;
        a = a * 8 + i;
        a = a * 2 + i;
        a = a * 3 + i;
        a = a * 4 + i;
        a = a * 5 + i;
        a = a * 6 + i;
        a = a * 7 + i;
        a = a * 8 + i;
        a = a * 2 + i;
        a = a * 3 + i;
        a = a * 4 + i;
        a = a * 5 + i;
    }
    return a;
}
