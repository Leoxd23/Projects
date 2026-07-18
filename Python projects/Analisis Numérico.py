import numpy as np
import sympy as sp

def gauss_elimination(A, b):
    """ Resuelve un sistema de ecuaciones lineales Ax = b con eliminación gaussiana """
    n = len(b)
    M = np.hstack([A.astype(float), b.reshape(-1,1).astype(float)])

    # Eliminación hacia adelante
    for i in range(n):
        # Pivoteo parcial
        max_row = np.argmax(abs(M[i:, i])) + i
        if M[max_row, i] == 0:
            raise ValueError("El sistema no tiene solución única")
        if max_row != i:
            M[[i, max_row]] = M[[max_row, i]]
        
        # Normalizar fila pivote
        M[i] = M[i] / M[i, i]

        # Eliminar hacia abajo
        for j in range(i+1, n):
            M[j] = M[j] - M[j, i] * M[i]

    # Sustitución hacia atrás
    x = np.zeros(n)
    for i in range(n-1, -1, -1):
        x[i] = M[i, -1] - np.dot(M[i, i+1:n], x[i+1:n])
    return x


def newton_raphson(f_expr, x0, tol=1e-8, max_iter=100, usar_correccion_multiplicidad=True):
    x = sp.symbols('x')
    f = sp.lambdify(x, f_expr, 'numpy')
    fprime_expr = sp.diff(f_expr, x)
    fprime = sp.lambdify(x, fprime_expr, 'numpy')
    f2 = sp.lambdify(x, sp.diff(fprime_expr, x), 'numpy') if usar_correccion_multiplicidad else None

    xi = float(x0)
    eps_der = 1e-14
    for i in range(1, max_iter+1):
        fxi = float(f(xi))
        if abs(fxi) < tol:  # ya estamos en la raíz
            print(f"Iteración {i}: x = {xi}, f(x) = {fxi}")
            return xi

        fpxi = float(fprime(xi))

        if abs(fpxi) < eps_der:  
            # Si f≈0 y f'≈0 → raíz múltiple
            if abs(fxi) < tol and usar_correccion_multiplicidad:
                f2xi = float(f2(xi))
                denom = fpxi**2 - fxi*f2xi
                if abs(denom) < eps_der:
                    raise ValueError("No se puede aplicar la corrección; intenta otro x0.")
                delta = (fxi*fpxi)/denom
            else:
                raise ValueError(f"Derivada nula en x={xi}, cambia el valor inicial x0.")
        else:
            # Newton estándar
            delta = fxi/fpxi

        xi_next = xi - delta
        print(f"Iteración {i}: x = {xi_next}, f(x) = {float(f(xi_next))}")
        if abs(xi_next - xi) < tol:
            return xi_next
        xi = xi_next

    raise ValueError("El método no convergió.")


# ===================== #
#     PROGRAMA MAIN     #
# ===================== #
def main():
    print("=== Resolver sistemas o ecuaciones ===")
    print("1) Sistema de ecuaciones lineales")
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

        sol = gauss_elimination(A, b)
        print("\n✅ Solución del sistema:", sol)

    elif opcion == "2":
        x = sp.symbols('x')
        expr_str = input("Introduce la función f(x): ")
        f_expr = sp.sympify(expr_str)

        x0 = float(input("Introduce el valor inicial x0: "))
        raiz = newton_raphson(f_expr, x0)
        print("\n✅ Raíz aproximada:", raiz)

    else:
        print("Opción no válida.")

if __name__ == "__main__":
    main()
