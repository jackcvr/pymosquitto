import matplotlib.pyplot as plt

# TODO: generate automatically after benchmark
TIME = {
    "PyMosquitto": 05.87,
    "Paho": 09.66,
}
PYTHON_MEMORY = 10.420
MEMORY = {
    "PyMosquitto": 17.668 - PYTHON_MEMORY,
    "Paho": 23.480 - PYTHON_MEMORY,
}

plt.figure(figsize=(4, 2))

plt.subplot(121)
plt.title("Time/sec")
plt.bar(TIME.keys(), TIME.values())

plt.subplot(122)
plt.title("Memory/MB")
plt.bar(MEMORY.keys(), MEMORY.values())

plt.tight_layout()
plt.savefig("results.png", dpi=150)
plt.close()
