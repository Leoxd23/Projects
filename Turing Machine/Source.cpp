#include <stdio.h>
#include <string.h>

#define MAX_LEN 100

char tape[MAX_LEN];
char output[MAX_LEN * 10];
int head = 0;

void resetTape(const char* input) {
    memset(tape, '_', sizeof(tape));
    strncpy(tape, input, strlen(input));
    head = 0;
}

void appendStep(const char* step) {
    strcat(output, step);
    strcat(output, "\n");
}

int simulateTuringMachine(const char* input) {
    resetTape(input);
    output[0] = '\0';
    int i, state = 0;
    char step[200];

    while (1) {
        sprintf(step, "Estado: q%d | Cinta: ", state);
        for (i = 0; i < strlen(tape); ++i)
            sprintf(step + strlen(step), "%c ", tape[i]);
        sprintf(step + strlen(step), "| Cabeza: %d", head);
        appendStep(step);

        switch (state) {
        case 0:
            if (tape[head] == 'a') {
                tape[head] = 'X';
                head++;
                state = 1;
            }
            else if (tape[head] == 'X' || tape[head] == 'Y' || tape[head] == 'b' || tape[head] == '_') {
                state = 4;
            }
            else return 0;
            break;

        case 1:
            if (tape[head] == 'a' || tape[head] == 'X') head++;
            else if (tape[head] == 'b') state = 2;
            else if (tape[head] == 'Y') head++;
            else if (tape[head] == '_') return 0;
            else return 0;
            break;

        case 2:
            if (tape[head] == 'b') {
                tape[head] = 'Y';
                state = 3;
                head--;
            }
            else if (tape[head] == 'Y') head++;
            else return 0;
            break;

        case 3:
            if (tape[head] == 'a' || tape[head] == 'X' || tape[head] == 'b' || tape[head] == 'Y') head--;
            else if (tape[head] == '_') {
                head++;
                state = 0;
            }
            else return 0;
            break;

        case 4:
            if (tape[head] == 'b' || tape[head] == 'Y') head++;
            else if (tape[head] == '_') return 1;
            else return 0;
            break;

        default: return 0;
        }
    }
    return 0;
}

int main() {
    char input[100];
    printf("Ingrese una cadena: ");
    scanf("%s", input);

    int valid = simulateTuringMachine(input);
    strcat(output, valid ? "Cadena ACEPTADA\n" : "Cadena RECHAZADA\n");

    printf("%s", output);
    return 0;
}
