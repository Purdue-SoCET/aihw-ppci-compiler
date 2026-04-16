#include "help.h"
int globa = 8;
int other = 2;

int akf9uiuiwen(int a, int b) {
    return (a > b);
}

int main() {
    int g = globa;
    globa++;
    g = other;
    other++;
    int a = 2;
    int b = 3;
    for (int i = 0; i < 5; i++) {
        akf9uiuiwen(a, b);
        if (a < b) {
            helper(a);
        } else if (b == a) {
            a--;
        }
    }
    return 0;
}
