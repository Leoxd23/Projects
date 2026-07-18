import time
import random
import matplotlib.pyplot as plt
from collections import deque, OrderedDict

# FIFO Cache
class FIFOCache:
    def __init__(self, capacidad):
        self.capacidad = capacidad
        self.cache = deque()
        self.data = set()
        self.fallos = 0

    def acceder(self, x):
        if x not in self.data:
            self.fallos += 1
            if len(self.cache) >= self.capacidad:
                eliminado = self.cache.popleft()
                self.data.remove(eliminado)
            self.cache.append(x)
            self.data.add(x)

# LRU Cache con OrderedDict (O(1))
class LRUCache:
    def __init__(self, capacidad):
        self.capacidad = capacidad
        self.cache = OrderedDict()
        self.fallos = 0

    def acceder(self, x):
        if x not in self.cache:
            self.fallos += 1
            if len(self.cache) >= self.capacidad:
                self.cache.popitem(last=False)  # elimina el menos reciente
        else:
            self.cache.move_to_end(x)  # actualizar como el más reciente
        self.cache[x] = True

# --- Experimento ---
def prueba_cache(n, capacidad):
    secuencia = [random.randint(0, n//2) for _ in range(n)]  # accesos aleatorios

    fifo = FIFOCache(capacidad)
    lru = LRUCache(capacidad)

    # FIFO
    start = time.time()
    for x in secuencia:
        fifo.acceder(x)
    t_fifo = time.time() - start

    # LRU
    start = time.time()
    for x in secuencia:
        lru.acceder(x)
    t_lru = time.time() - start

    return t_fifo, fifo.fallos, t_lru, lru.fallos

# --- Ejecución con diferentes tamaños ---
tamaños = [10**3, 5*10**3, 10**4, 5*10**4]
capacidad = 100
tiempos_fifo, tiempos_lru = [], []
fallos_fifo, fallos_lru = [], []

for n in tamaños:
    t_fifo, f_fifo, t_lru, f_lru = prueba_cache(n, capacidad)
    tiempos_fifo.append(t_fifo)
    tiempos_lru.append(t_lru)
    fallos_fifo.append(f_fifo)
    fallos_lru.append(f_lru)
    print(f"n={n:,} → FIFO: fallos={f_fifo}, tiempo={t_fifo:.5f}s | LRU: fallos={f_lru}, tiempo={t_lru:.5f}s")

# --- Gráficas ---
plt.figure(figsize=(12,5))

# Tiempos
plt.subplot(1,2,1)
plt.plot(tamaños, tiempos_fifo, marker="o", label="FIFO")
plt.plot(tamaños, tiempos_lru, marker="o", label="LRU")
plt.xlabel("Número de accesos (n)")
plt.ylabel("Tiempo (s)")
plt.title("Tiempo de ejecución FIFO vs LRU")
plt.legend()
plt.grid(True)

# Fallos
plt.subplot(1,2,2)
plt.plot(tamaños, fallos_fifo, marker="o", label="FIFO")
plt.plot(tamaños, fallos_lru, marker="o", label="LRU")
plt.xlabel("Número de accesos (n)")
plt.ylabel("Fallos de caché")
plt.title("Fallos de caché FIFO vs LRU")
plt.legend()
plt.grid(True)

plt.tight_layout()
plt.show()
