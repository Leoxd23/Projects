import numpy as np
import sympy as sp

def newton_raphson(f_expr, x0, tol=1e-6, max_iter=100):
    x = sp.symbols('x')
    f = sp.lambdify(x, f_expr, 'numpy')
    fprime = sp.lambdify(x, sp.diff(f_expr, x), 'numpy')
    xi = x0
    for _ in range(max_iter):
        try:
            fxi = f(xi)
            fpxi = fprime(xi)
            if fpxi == 0:
                return None
            xi_next = xi - fxi/fpxi
            if abs(fxi) < tol or abs(xi_next - xi) < tol:
                return xi_next
            xi = xi_next
        except:
            return None
    return None

def biseccion(f_expr, a, b, tol=1e-6, max_iter=100):
    x = sp.symbols('x')
    f = sp.lambdify(x, f_expr, 'numpy')
    if f(a)*f(b) > 0:
        return None
    for _ in range(max_iter):
        c = (a+b)/2
        fc = f(c)
        if abs(fc) < tol or (b-a)/2 < tol:
            return c
        if f(a)*fc < 0:
            b = c
        else:
            a = c
    return (a+b)/2

def resolver_ecuacion(expr_str, rango=(-10, 10), pasos=200):
    x = sp.symbols('x')
    f_expr = sp.sympify(expr_str)

    # Intento simbólico
    try:
        soluciones = sp.solve(sp.Eq(f_expr, 0), x)
        if soluciones:
            return sorted(set([complex(sol.evalf()) for sol in soluciones]))
    except:
        pass

    f = sp.lambdify(x, f_expr, 'numpy')
    a, b = rango
    xs = np.linspace(a, b, pasos)
    raices = []

    # Bisección
    for i in range(len(xs)-1):
        x1, x2 = xs[i], xs[i+1]
        try:
            if f(x1) * f(x2) <= 0:
                r = biseccion(f_expr, x1, x2)
                if r is not None:
                    raices.append(r)
        except:
            continue

    # Newton-Raphson
    for guess in np.linspace(a, b, 10):
        r = newton_raphson(f_expr, guess)
        if r is not None:
            raices.append(r)

    # Eliminar duplicados
    raices_unicas = []
    for r in raices:
        if not any(abs(r - ru) < 1e-5 for ru in raices_unicas):
            raices_unicas.append(r)

    return sorted(raices_unicas)

# ===================== #
#     PROGRAMA MAIN     #
# ===================== #
def main():
    print("=== Resolver ecuaciones ===")
    expr_str = input("Introduce la función f(x): ")
    a = float(input("Introduce el límite inferior del intervalo: "))
    b = float(input("Introduce el límite superior del intervalo: "))

    soluciones = resolver_ecuacion(expr_str, rango=(a, b))

    if soluciones:
        print("\n✅ Raíces encontradas en el intervalo:")
        for r in soluciones:
            print("   x ≈", r)
    else:
        print("\n❌ No se encontró ninguna raíz en el intervalo.")

if __name__ == "__main__":
    main()
