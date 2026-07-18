import threading
import time
import matplotlib.pyplot as plt
import numpy as np

# Función que cada hilo ejecutará: sumar una parte de la lista
def partial_sum(lista, start, end, results, index):
    results[index] = sum(lista[start:end])

# Algoritmo paralelo con threading
def parallel_sum(lista, num_threads):
    n = len(lista)
    step = n // num_threads
    threads = []
    results = [0] * num_threads
    
    # Crear hilos
    for i in range(num_threads):
        start = i * step
        end = n if i == num_threads - 1 else (i + 1) * step
        thread = threading.Thread(target=partial_sum, args=(lista, start, end, results, i))
        threads.append(thread)
        thread.start()
    
    # Esperar a que todos los hilos terminen
    for thread in threads:
        thread.join()
    
    return sum(results)

# --- Prueba con diferentes tamaños y número de hilos ---
sizes = [10**5, 5*10**5, 10**6, 5*10**6]  # tamaños de listas
threads_list = [1, 2, 4, 8]  # número de hilos
times = {p: [] for p in threads_list}

for n in sizes:
    lista = list(np.random.randint(1, 100, size=n))  # lista aleatoria
    for p in threads_list:
        start_time = time.time()
        parallel_sum(lista, p)
        end_time = time.time()
        times[p].append(end_time - start_time)

# --- Graficar resultados ---
plt.figure(figsize=(10,6))
for p in threads_list:
    plt.plot(sizes, times[p], marker="o", label=f"{p} hilos")

plt.xlabel("Tamaño de la lista (n)")
plt.ylabel("Tiempo de ejecución (s)")
plt.title("Suma paralela con threading")
plt.legend()
plt.grid(True)
plt.show()
