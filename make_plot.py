import csv
import sys
from datetime import datetime

import matplotlib.pyplot as plt

PYTHON_RSS = int(sys.argv[1]) if len(sys.argv) > 1 else 0

LOSERS = {"aiomqtt", "amqtt"}


def parse_time(t: str) -> float:
    if t.count(":") == 1:  # m:ss.xx
        dt = datetime.strptime(t, "%M:%S.%f")
        return dt.minute * 60 + dt.second + dt.microsecond / 1e6
    elif t.count(":") == 2:  # h:mm:ss.xx
        dt = datetime.strptime(t, "%H:%M:%S.%f")
        return dt.hour * 3600 + dt.minute * 60 + dt.second + dt.microsecond / 1e6
    else:
        return 0


def parse_csv(path: str) -> dict:
    result = {}
    with open(path, newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            module = row["Module"].strip()
            time = row["Time"].strip()
            rss = row["RSS"].strip()
            result[module] = {
                "Time": parse_time(time),
                "RSS": max(0, int(rss) - PYTHON_RSS),
            }
    return result


def plot_results(results: dict, outfile: str):
    times = {k: v["Time"] for k, v in results.items()}
    rss = {k: (v["RSS"] / 1024) for k, v in results.items()}

    plt.figure(figsize=(6, 3))
    for i, (results, title) in enumerate(
        [(times, "Time (s)"), (rss, "Memory (MB)")], 1
    ):
        results = dict(sorted(results.items(), key=lambda x: x[1]))
        modules = results.keys()
        vals = results.values()
        ax = plt.subplot(1, 2, i)
        ax.set_title(title)
        bars = ax.bar(modules, vals)
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
        for bar, val in zip(bars, vals):
            if val == 0:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    0,
                    "FAILED\n",
                    ha="center",
                    color="red",
                )

    plt.tight_layout()
    plt.savefig(outfile, dpi=150)
    plt.close()


data = parse_csv("benchmark.csv")
plot_results(data, "results.png")
for module in LOSERS:
    del data[module]
plot_results(data, "results_fast.png")
