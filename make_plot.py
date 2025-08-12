import matplotlib.pyplot as plt

# TODO: generate automatically after benchmark
TIME = {
    "PyMosquitto": 4.82,
    "Paho": 11.19,
    "aMQTT": 62.55,
}
PYTHON_MEMORY = 8.632
MEMORY = {
    "PyMosquitto": 13.704 - PYTHON_MEMORY,
    "Paho": 19.804 - PYTHON_MEMORY,
    "aMQTT": 28.200 - PYTHON_MEMORY,
}

plt.figure(figsize=(6, 3))

plt.subplot(121)
plt.title("Time")
plt.bar(TIME.keys(), TIME.values())

plt.subplot(122)
plt.title("Memory")
plt.bar(MEMORY.keys(), MEMORY.values())

plt.tight_layout()
plt.savefig("results.png", dpi=150)
plt.close()
