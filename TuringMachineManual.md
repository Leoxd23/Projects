# Turing Machine

This project implements a simple Turing machine in C++ that decides whether an input string belongs to the language:

$$
L = \{ a^n b^n \mid n \geq 1 \}
$$

In other words, the machine accepts strings containing the same number of `a` symbols followed by the same number of `b` symbols, such as:

- `ab`
- `aabb`
- `aaabbb`

It rejects strings such as:

- `aba`
- `abb`
- `baab`

## How it works

The machine uses a tape initialized with the input string, with the rest of the tape filled with `_` blanks.

The head starts at position 0 and the machine moves through different states:

- `q0`: finds the first `a` and replaces it with `X`
- `q1`: moves right until it finds a `b`
- `q2`: replaces that `b` with `Y` and moves left
- `q3`: moves left to find the next unmarked `a`
- `q4`: checks the remaining tape and accepts if only blanks remain

The symbol `X` marks an `a` that has already been matched, and `Y` marks a `b` that has already been matched.

## Accepted examples

- `ab`
- `aabb`
- `aaabbb`

## Rejected examples

- `a`
- `aba`
- `abb`
- `baab`

## Compilation

On Windows with the Visual Studio C++ compiler:

```powershell
cl /EHsc /nologo Source.cpp
```

Then run:

```powershell
.\Source.exe
```

## Notes

This is a standard single-file C++ implementation of a deterministic Turing machine that recognizes the language of equal numbers of `a` and `b` in order.
