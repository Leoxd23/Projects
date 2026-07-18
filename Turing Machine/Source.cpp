#include <iostream>
#include <string>

using namespace std;

constexpr int MAX_LEN = 100;

class TuringMachine {
private:
    string tape;
    string output;
    int head = 0;
    int state = 0;

    void resetTape(const string& input) {
        tape.assign(MAX_LEN, '_');
        for (int i = 0; i < static_cast<int>(input.size()) && i < MAX_LEN; ++i) {
            tape[i] = input[i];
        }
        head = 0;
        state = 0;
    }

    void appendStep(const string& step) {
        output += step + '\n';
    }

    string buildStepLine() const {
        string step = "Estado: q" + to_string(state) + " | Cinta: ";
        for (char ch : tape) {
            step += ch;
            step += ' ';
        }
        step += "| Cabeza: " + to_string(head);
        return step;
    }

public:
    bool simulate(const string& input) {
        resetTape(input);
        output.clear();

        while (true) {
            appendStep(buildStepLine());

            if (head < 0 || head >= static_cast<int>(tape.size())) {
                return false;
            }

            switch (state) {
            case 0:
                if (tape[head] == 'a') {
                    tape[head] = 'X';
                    ++head;
                    state = 1;
                }
                else if (tape[head] == 'X' || tape[head] == 'Y' || tape[head] == 'b' || tape[head] == '_') {
                    state = 4;
                }
                else {
                    return false;
                }
                break;

            case 1:
                if (tape[head] == 'a' || tape[head] == 'X') {
                    ++head;
                }
                else if (tape[head] == 'b') {
                    state = 2;
                }
                else if (tape[head] == 'Y') {
                    ++head;
                }
                else {
                    return false;
                }
                break;

            case 2:
                if (tape[head] == 'b') {
                    tape[head] = 'Y';
                    state = 3;
                    --head;
                }
                else if (tape[head] == 'Y') {
                    ++head;
                }
                else {
                    return false;
                }
                break;

            case 3:
                if (tape[head] == 'a' || tape[head] == 'X' || tape[head] == 'b' || tape[head] == 'Y') {
                    --head;
                }
                else if (tape[head] == '_') {
                    ++head;
                    state = 0;
                }
                else {
                    return false;
                }
                break;

            case 4:
                if (tape[head] == 'b' || tape[head] == 'Y') {
                    ++head;
                }
                else if (tape[head] == '_') {
                    return true;
                }
                else {
                    return false;
                }
                break;

            default:
                return false;
            }
        }
    }

    string getOutput() const {
        return output;
    }
};

int main() {
    string input;
    cout << "Ingrese una cadena: ";
    cin >> input;

    TuringMachine machine;
    const bool accepted = machine.simulate(input);

    cout << machine.getOutput();
    cout << (accepted ? "Cadena ACEPTADA\n" : "Cadena RECHAZADA\n");

    return 0;
}
