import concurrent.futures
import requests
import httpx
import time

NUM_REQUESTS = 1000
NUM_THREADS = 50
URL = "https://rest.ably.io/time"

print("URL:          ", URL)
print("NUM_REQUESTS: ", NUM_REQUESTS)
print("NUM_THREADS:  ", NUM_THREADS)
print()

# requests
client = requests.Session()
durations = []
success, failure = 0, 0


def send():
    for _ in range(NUM_REQUESTS):
        start = time.monotonic()
        client.get(URL)
        end = time.monotonic()
        duration = end - start
        durations.append(duration)


all_start = time.monotonic()
with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
    for _ in range(NUM_THREADS):
        executor.submit(send)
all_end = time.monotonic()

durations = sorted(durations)
totalTimeTaken = sum(durations)
print("requests")
print("--------")
print("Total requests: ", len(durations))
print("Average: %.3f" % (sum(durations) / len(durations)))
print("Median:  %.3f" % (durations[int(len(durations) * 0.5)]))
print("95th:    %.3f" % (durations[int(len(durations) * 0.95)]))
print("99th:    %.3f" % (durations[int(len(durations) * 0.99)]))
print("total time taken %.3f" % totalTimeTaken)
print("total time taken concurrent %.3f" % (all_end - all_start))
print()

# httpx
client = httpx.Client()
durations = []


def send():
    for _ in range(NUM_REQUESTS):
        start = time.monotonic()
        client.get(URL)
        end = time.monotonic()
        duration = end - start
        durations.append(duration)


all_start = time.monotonic()
with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
    for _ in range(NUM_THREADS):
        executor.submit(send)
all_end = time.monotonic()

durations = sorted(durations)
totalTimeTaken = sum(durations)

print("httpx")
print("-----")
print("Total requests: ", len(durations))
print("Average: %.3f" % (sum(durations) / len(durations)))
print("Median:  %.3f" % (durations[int(len(durations) * 0.5)]))
print("95th:    %.3f" % (durations[int(len(durations) * 0.95)]))
print("99th:    %.3f" % (durations[int(len(durations) * 0.99)]))
print("total time taken %.3f" % totalTimeTaken)
print("total time taken concurrent %.3f" % (all_end - all_start))
print()
