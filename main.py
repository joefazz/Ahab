import docker
import pprint
from datetime import datetime, timedelta

pp = pprint.PrettyPrinter(indent=2)
unused_containers = []

# Function which checks to see when the container was last active, compares it against the tts
# and then either stops it or removes it based on param
# tts = Time To Stale


# def calculate_cpu_percent(d):
#     cpu_count = len(d["cpu_stats"]["cpu_usage"]["percpu_usage"])
#     cpu_percent = 0.0
#     cpu_delta = float(d["cpu_stats"]["cpu_usage"]["total_usage"]) - \
#         float(d["precpu_stats"]["cpu_usage"]["total_usage"])
#     system_delta = float(d["cpu_stats"]["system_cpu_usage"]) - \
#         float(d["precpu_stats"]["system_cpu_usage"])
#     if system_delta > 0.0:
#         cpu_percent = cpu_delta / system_delta * 100.0 * cpu_count
#     return cpu_percent


def stale_manager(container, tts=1, should_remove=False):
    logs = container.logs(stream=False, timestamps=True, tail=1)
    # logs is in bytes form so needs to be decoded
    decoded_str = logs.decode("utf-8")
    # Sometimes the log is empty, if it is we need to keep track of it because it means the container is unused
    if decoded_str:
        # Strip the timestamp out of the log (also remove the timezone because I can't figure out how to include it)
        timestamp = decoded_str.split(' ')[0][:-4]

        now = datetime.strptime(
            datetime.utcnow().isoformat(), '%Y-%m-%dT%H:%M:%S.%f')

        then = datetime.strptime(
            timestamp, '%Y-%m-%dT%H:%M:%S.%f')

        # Edit this in order to modify the TTS (Time To Stale)
        x_minutes_ago = now - timedelta(minutes=tts)

        delta = now - then

        # Remove stale containers so the disk is freed
        if then < x_minutes_ago:
            print(
                "Removing: " + container.name) if should_remove else print("Stopping: " + container.name)
            container.remove() if should_remove else container.stop()

        print(delta)
    else:
        if container.status == "running" or container.status == "paused":
            if unused_containers.count(container.short_id) == 1:
                container.stop()
                print("Stop Container: " + container.name)
            else:
                unused_containers.append(container.short_id)

        elif container.status == "exited":
            print(unused_containers.count(container.short_id))
            if unused_containers.count(container.short_id) == 1:
                container.remove()
                print("Removing Container: " + container.name)
            else:
                unused_containers.append(container.short_id)


def track_containers(containers):
    for unused in unused_containers:
        unused_cont = client.containers.get(unused)
        print("Flushing unused container: " + unused_cont.name)
        stale_manager(unused_cont, 1, unused_cont.status == "exited")

    for container in containers:
        if unused_containers.count(container.short_id) == 1:
            continue
        # If the container is running need to make sure that it's not at high capacity load
        if container.status == "running":
            container.stats(stream=False)
            # pp.pprint(stats)
            if container.name == "Bifrost" or container.name == "mongo":
                print("Don't touch container: " + container.name)
            else:
                print("Live container: " + container.name)
                stale_manager(container, 5)

        elif container.status == "paused":
            print("Paused container: " + container.name)
            stale_manager(container, 10)

        # If the container isn't running, check to see the last time it was live
        elif container.status == "exited":
            stale_manager(container, 5, True)

    return 0


client = docker.from_env()

with open("unused_containers.txt", "r") as file:
    unused_containers = file.readlines()


all_containers = client.containers.list(all=True)

if len(all_containers) == 0:
    print("Nothing Running")
else:
    track_containers(all_containers)

with open("unused_containers.txt", "w+") as file:
    file.seek(0)

    file.truncate()

    file.writelines(unused_containers)
