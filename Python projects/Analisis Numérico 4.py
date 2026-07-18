"""
robust_roots.py
Buscador robusto de raíces (mejor esfuerzo).
- Usa SymPy para detectar y resolver polinomios analíticamente.
- Para funciones generales, escanea un intervalo [a,b], detecta bracketing
  por cambio de signo o por valores |f| pequeños, aplica bisección y
  pule con Newton/secant cuando sea seguro.
- Devuelve raíces reales (y opcionalmente complejas para polinomios).
Limitaciones: no puede garantizar encontrar *todas* las raíces en R para
funciones pathológicas, ni raíces fuera del intervalo buscado.
"""

import numpy as np
import sympy as sp
import math

x = sp.symbols('x')

# -------------------------
# Utilidades numéricas
# -------------------------
def safe_eval_func(f_expr):
    """Devuelve una función numpy-evaluable f(x) y su derivada f'(x) si es posible."""
    f = sp.lambdify(x, f_expr, 'numpy')
    try:
        fprime_expr = sp.diff(f_expr, x)
        fprime = sp.lambdify(x, fprime_expr, 'numpy')
    except Exception:
        fprime = None
    return f, fprime

def is_poly_and_solvable(f_expr):
    """Detecta polinomio con Sympy; devuelve Poly o None."""
    try:
        poly = sp.Poly(f_expr, x)
        if poly.is_univariate:
            return poly
    except Exception:
        return None
    return None

# -------------------------
# Métodos numéricos robustos
# -------------------------
def bisection_root(f, a, b, tol=1e-8, max_iter=200):
    """Bisección clásica con manejo de excepciones; requiere f(a)*f(b) <= 0"""
    fa = f(a); fb = f(b)
    if np.isnan(fa) or np.isnan(fb):
        raise ValueError("Evaluación NaN en extremos")
    if fa == 0:
        return a
    if fb == 0:
        return b
    if fa * fb > 0:
        raise ValueError("No hay cambio de signo")
    left, right = a, b
    for i in range(max_iter):
        c = (left + right) / 2.0
        try:
            fc = f(c)
        except Exception:
            # tratar evaluaciones problemáticas: subdividir y volver a intentar
            left, right = left, (left+right)/2
            continue
        if abs(fc) < tol or (right-left)/2 < tol:
            return c
        if fa * fc <= 0:
            right = c
            fb = fc
        else:
            left = c
            fa = fc
    return (left+right)/2.0

def newton_polish(f, fprime, x0, tol=1e-12, max_iter=50):
    """Pulidor Newton con protección contra derivada cerca de cero."""
    xi = x0
    for i in range(max_iter):
        try:
            fxi = f(xi)
            fpxi = fprime(xi) if fprime is not None else None
        except Exception:
            return None
        if fpxi is None or abs(fpxi) < 1e-14:
            return None  # no es seguro aplicar Newton
        xi_next = xi - fxi / fpxi
        if not (np.isfinite(xi_next)):
            return None
        if abs(xi_next - xi) < tol:
            return xi_next
        xi = xi_next
    return None

def secant_polish(f, x0, x1, tol=1e-12, max_iter=50):
    """Pulidor secante (no requiere derivada)."""
    xi_1 = x0; xi = x1
    for i in range(max_iter):
        try:
            f_xi = f(xi); f_xi1 = f(xi_1)
        except Exception:
            return None
        denom = (f_xi - f_xi1)
        if denom == 0:
            return None
        xi_next = xi - f_xi * (xi - xi_1) / denom
        if not np.isfinite(xi_next):
            return None
        if abs(xi_next - xi) < tol:
            return xi_next
        xi_1, xi = xi, xi_next
    return None

# -------------------------
# Estrategia principal
# -------------------------
def find_roots(f_str,
               interval=(-100.0, 100.0),
               grid_points=2000,
               zero_tol=1e-8,
               dedup_tol=1e-7):
    """
    f_str: string con la función en formato SymPy (ej. "exp(-x)-x" o "x**3-2*x+1")
    interval: (a,b) intervalo de búsqueda en R
    grid_points: número de puntos para muestreo inicial
    zero_tol: umbral para considerar f(x) ~ 0
    dedup_tol: distancia para considerar raíces iguales
    Devuelve: diccionario con raíces reales y (si aplica) raíces de polinomio.
    """
    a, b = float(interval[0]), float(interval[1])
    if a >= b:
        raise ValueError("Intervalo inválido")
    try:
        f_expr = sp.sympify(f_str)
    except Exception as e:
        raise ValueError(f"Expresión no válida para SymPy: {e}")

    # 1) Si es polinomio: usar nroots (rápido y devuelve multiplicidades)
    poly = is_poly_and_solvable(f_expr)
    poly_roots = None
    if poly is not None and poly.degree() >= 0:
        try:
            nroots = poly.nroots(n=15)
            poly_roots = [complex(r) for r in nroots]
            real_roots = []
            for r in poly_roots:
                if abs(r.imag) < 1e-10:
                    if a - 1e-12 <= r.real <= b + 1e-12:
                        real_roots.append(float(r.real))
            roots = _dedupe_roots(real_roots, dedup_tol)
            return {"real_roots": roots, "poly_roots": poly_roots}
        except Exception:
            pass

    # 2) Para funciones generales: búsqueda numérica en [a,b]
    f, fprime = safe_eval_func(f_expr)

    xs = np.linspace(a, b, grid_points)
    vals = np.empty_like(xs, dtype=float)
    for i, xi in enumerate(xs):
        try:
            yi = f(xi)
            if isinstance(yi, np.ndarray):
                yi = float(yi)
            vals[i] = float(yi)
        except Exception:
            vals[i] = np.nan

    roots_found = []

    # 2.a detectar evaluaciones exactamente cero o muy cercanas
    for xi, yi in zip(xs, vals):
        if not np.isfinite(yi):
            continue
        if abs(yi) <= zero_tol:
            roots_found.append(float(xi))

    # 2.b detectar cambios de signo en subintervalos válidos
    for i in range(len(xs)-1):
        x1, x2 = xs[i], xs[i+1]
        y1, y2 = vals[i], vals[i+1]
        if not (np.isfinite(y1) and np.isfinite(y2)):
            continue
        if y1 * y2 < 0:
            try:
                root = bisection_root(f, x1, x2, tol=zero_tol)
                if root is not None:
                    roots_found.append(root)
            except Exception:
                mid = (x1 + x2)/2
                try:
                    root = bisection_root(f, x1, mid, tol=zero_tol)
                    if root is not None:
                        roots_found.append(root)
                except Exception:
                    pass

    # 2.c detectar "valleys" donde |f| tiene mínimo pequeño sin cambio de signo
    abs_vals = np.abs(vals)
    finite_idx = np.where(np.isfinite(abs_vals))[0]
    for idx in finite_idx:
        if abs_vals[idx] > 1e-2:
            continue
        left = abs_vals[idx-1] if idx-1 >= 0 else np.inf
        right = abs_vals[idx+1] if idx+1 < len(abs_vals) else np.inf
        if abs_vals[idx] <= left and abs_vals[idx] <= right:
            xi = xs[idx]
            polished = None
            if fprime is not None:
                polished = newton_polish(f, fprime, xi)
            if polished is None:
                x_left = xs[idx-1] if idx-1 >= 0 else xi - (xs[1]-xs[0])
                x_right = xs[idx+1] if idx+1 < len(xs) else xi + (xs[1]-xs[0])
                polished = secant_polish(f, x_left, x_right)
            if polished is not None and np.isfinite(polished):
                if a - 1e-12 <= polished <= b + 1e-12:
                    try:
                        if abs(f(polished)) <= max(zero_tol, 1e-6):
                            roots_found.append(float(polished))
                    except Exception:
                        pass

    # deduplicar y ordenar
    roots_unique = _dedupe_roots(roots_found, dedup_tol)

    roots_info = []
    for r in roots_unique:
        multiplicity_est = None
        try:
            fp = fprime(r) if fprime is not None else None
            if fp is None:
                multiplicity_est = 'unknown'
            else:
                if abs(fp) < 1e-6:
                    multiplicity_est = "likely multiple (f' near 0)"
                else:
                    multiplicity_est = "simple (f' nonzero)"
        except Exception:
            multiplicity_est = 'unknown'
        roots_info.append((r, multiplicity_est))

    return {"real_roots": [r for r,_ in roots_info], "roots_info": roots_info, "poly_roots": poly_roots}


def _dedupe_roots(roots_list, tol=1e-7):
    if not roots_list:
        return []
    roots = sorted([float(r) for r in roots_list if np.isfinite(r)])
    out = [roots[0]]
    for r in roots[1:]:
        if abs(r - out[-1]) > tol:
            out.append(r)
    return out

# -------------------------
# Ejemplo de uso
# -------------------------
if __name__ == "__main__":
    ejemplos = [
        ("exp(-x)-x", (-2, 5)),
        ("x**2", (-1, 1)),
        ("sin(x) - 0.5", (-10, 10)),
        ("x**3 - 2*x + 1", (-5, 5)),
        ("(x-1)**2*(x+2)", (-5, 5)),
    ]
    for fstr, interval in ejemplos:
        print("\n>>> Buscando raíces de:", fstr, "en", interval)
        try:
            res = find_roots(fstr, interval=interval, grid_points=2000)
            print("Real roots:", res.get("real_roots"))
            if res.get("poly_roots") is not None:
                print("Poly (all) roots:", res.get("poly_roots"))
            print("Roots info:", res.get("roots_info"))
        except Exception as e:
            print("Error durante búsqueda:", e)
