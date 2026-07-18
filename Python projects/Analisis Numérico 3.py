import numpy as np
import sympy as sp

# =====================
# MÉTODOS PARA SISTEMAS
# =====================
def gauss_jordan(A, b):
    """ Resuelve un sistema Ax = b con Gauss-Jordan """
    n = len(b)
    M = np.hstack([A.astype(float), b.reshape(-1,1).astype(float)])

    for i in range(n):
        if M[i,i] == 0:
            for j in range(i+1, n):
                if M[j,i] != 0:
                    M[[i,j]] = M[[j,i]]
                    break
        M[i] = M[i] / M[i,i]
        for j in range(n):
            if j != i:
                M[j] = M[j] - M[j,i]*M[i]
    return M[:, -1]

# =========================
# MÉTODOS PARA NO LINEALES
# =========================
def newton_raphson(f_expr, x0, tol=1e-6, max_iter=100):
    x = sp.symbols('x')
    f = sp.lambdify(x, f_expr, 'numpy')
    fprime = sp.lambdify(x, sp.diff(f_expr, x), 'numpy')

    xi = x0
    for i in range(max_iter):
        fxi, fpxi = f(xi), fprime(xi)
        if fpxi == 0:
            return None
        xi_next = xi - fxi/fpxi
        if abs(xi_next - xi) < tol:
            return xi_next
        xi = xi_next
    return None

def biseccion(f_expr, a, b, tol=1e-6, max_iter=100):
    x = sp.symbols('x')
    f = sp.lambdify(x, f_expr, 'numpy')

    if f(a)*f(b) > 0:
        return None
    for _ in range(max_iter):
        c = (a+b)/2
        if abs(f(c)) < tol or (b-a)/2 < tol:
            return c
        if f(a)*f(c) < 0:
            b = c
        else:
            a = c
    return (a+b)/2

def regla_falsa(f_expr, a, b, tol=1e-6, max_iter=100):
    x = sp.symbols('x')
    f = sp.lambdify(x, f_expr, 'numpy')

    if f(a)*f(b) > 0:
        return None
    for _ in range(max_iter):
        c = (a*f(b) - b*f(a)) / (f(b) - f(a))
        if abs(f(c)) < tol:
            return c
        if f(a)*f(c) < 0:
            b = c
        else:
            a = c
    return c

def punto_fijo(g_expr, x0, tol=1e-6, max_iter=100):
    x = sp.symbols('x')
    g = sp.lambdify(x, g_expr, 'numpy')

    xi = x0
    for _ in range(max_iter):
        xi_next = g(xi)
        if abs(xi_next - xi) < tol:
            return xi_next
        xi = xi_next
    return None

# Buscar todas las raíces en un intervalo
def encontrar_todas_las_raices(f_expr, a=-10, b=10, pasos=200, metodo="biseccion"):
    raices = []
    xs = np.linspace(a, b, pasos)
    for i in range(len(xs)-1):
        x0, x1 = xs[i], xs[i+1]
        try:
            if metodo == "biseccion":
                r = biseccion(f_expr, x0, x1)
            elif metodo == "regla_falsa":
                r = regla_falsa(f_expr, x0, x1)
            else:
                continue
            if r is not None and not any(abs(r-rr) < 1e-4 for rr in raices):
                raices.append(r)
        except Exception:
            continue
    return raices

# =====================
# PROGRAMA PRINCIPAL
# =====================
def main():
    print("=== Resolver sistemas o ecuaciones no lineales ===")
    print("1) Sistema de ecuaciones lineales (Gauss-Jordan)")
    print("2) Ecuación no lineal")

    opcion = input("Elige una opción (1 o 2): ")

    if opcion == "1":
        n = int(input("Número de ecuaciones (y variables): "))
        A = np.zeros((n, n))
        b = np.zeros(n)

        print("Introduce los coeficientes de la matriz A:")
        for i in range(n):
            fila = input(f"Fila {i+1} (separar con espacios): ")
            A[i] = [float(x) for x in fila.split()]

        print("Introduce los valores del vector b:")
        b = np.array([float(x) for x in input("b (separar con espacios): ").split()])

        sol = gauss_jordan(A, b)
        print("\n✅ Solución del sistema:", sol)

    elif opcion == "2":
        x = sp.symbols('x')
        expr_str = input("Introduce la función f(x): ")
        f_expr = sp.sympify(expr_str)

        print("\nMétodos disponibles:")
        print("1) Newton-Raphson")
        print("2) Bisección")
        print("3) Regla Falsa")
        print("4) Punto fijo")
        print("5) Buscar todas las raíces (con Bisección)")
        metodo = input("Elige un método (1-5): ")

        if metodo == "1":
            x0 = float(input("Valor inicial x0: "))
            raiz = newton_raphson(f_expr, x0)
        elif metodo == "2":
            a = float(input("Extremo izquierdo a: "))
            b = float(input("Extremo derecho b: "))
            raiz = biseccion(f_expr, a, b)
        elif metodo == "3":
            a = float(input("Extremo izquierdo a: "))
            b = float(input("Extremo derecho b: "))
            raiz = regla_falsa(f_expr, a, b)
        elif metodo == "4":
            g_str = input("Introduce g(x) para el punto fijo (ej: sqrt(3)): ")
            g_expr = sp.sympify(g_str)
            x0 = float(input("Valor inicial x0: "))
            raiz = punto_fijo(g_expr, x0)
        elif metodo == "5":
            a = float(input("Intervalo izquierdo a: "))
            b = float(input("Intervalo derecho b: "))
            raices = encontrar_todas_las_raices(f_expr, a, b)
            print("\n✅ Raíces aproximadas en el intervalo:", raices)
            return
        else:
            print("Método no válido.")
            return

        print("\n✅ Raíz aproximada:", raiz)

    else:
        print("Opción no válida.")

if __name__ == "__main__":
    main()