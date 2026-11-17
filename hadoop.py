import subprocess

CONTAINER = "hadoop-namenode"   # all Hadoop commands are run inside this container

HDFS_INPUT = "/lichess/games"     # main dataset
HDFS_OUTPUT = "/lichess/output"   # MapReduce results


def run(command):
    """Runs a shell command inside the Hadoop container. Returns its stdout."""
    completed = subprocess.run(["docker", "exec", CONTAINER, "bash", "-c", command],
                               capture_output=True, text=True)
    if completed.returncode != 0:
        output = completed.stdout + completed.stderr
        print(output[-5000:])   # Hadoop logs are long; the end is the useful part
        raise SystemExit(f"Hadoop command failed: {command}")
    return completed.stdout


def exists(path):
    """True if the path exists in HDFS."""
    completed = subprocess.run(["docker", "exec", CONTAINER, "hdfs", "dfs", "-test", "-e", path])
    return completed.returncode == 0