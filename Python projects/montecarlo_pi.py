import random
import time
import matplotlib.pyplot as plt
import math

# Algoritmo Monte Carlo para aproximar pi
def montecarlo_pi(n):
    dentro = 0
    for _ in range(n):
        x, y = random.random(), random.random()
        if x*x + y*y <= 1:
            dentro += 1
    return 4 * dentro / n

# --- Experimentos ---
iteraciones = [10**3, 10**4, 10**5, 10**6]
tiempos = []
errores = []

for n in iteraciones:
    start = time.time()
    pi_aprox = montecarlo_pi(n)
    end = time.time()

    tiempo = end - start
    error = abs(math.pi - pi_aprox)

    tiempos.append(tiempo)
    errores.append(error)

    print(f"n={n:,} → π≈{pi_aprox:.6f}, error={error:.6f}, tiempo={tiempo:.4f}s")

# --- Gráficas ---
plt.figure(figsize=(12,5))

# Tiempo de ejecución O(n)
plt.subplot(1,2,1)
plt.plot(iteraciones, tiempos, marker="o")
plt.xlabel("Número de iteraciones (n)")
plt.ylabel("Tiempo de ejecución (s)")
plt.title("Tiempo vs Iteraciones (Monte Carlo π)")
plt.grid(True)

# Error de aproximación
plt.subplot(1,2,2)
plt.plot(iteraciones, errores, marker="o", color="red")
plt.xlabel("Número de iteraciones (n)")
plt.ylabel("Error |π - π_aprox|")
plt.title("Error vs Iteraciones (Monte Carlo π)")
plt.grid(True)

plt.tight_layout()
plt.show()
