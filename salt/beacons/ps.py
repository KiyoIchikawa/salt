"""
Send events based on process status.

The config below sets up beacons to check that
processes are running or stopped. If there are multiple
instances of a process running, you may specify which
user's process to watch (good example would be
IIS App Pools).

.. code-block:: yaml
beacons:
  ps:
    processes:
      - powershell.exe:
         status: running
      - w3svc.exe:
         status: running
         username: "DOMAIN\\username1"
      - mysql:
         status: stopped
"""
import logging

try:
    import salt.utils.psutil_compat as psutil

    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


log = logging.getLogger(__name__)  # pylint: disable=invalid-name

__virtualname__ = "ps"


def __virtual__():
    if not HAS_PSUTIL:
        err_msg = "psutil library is missing."
        log.error("Unable to load %s beacon: %s", __virtualname__, err_msg)
        return False, err_msg
    return __virtualname__


def validate(config):
    """
    Validate the beacon configuration
    """
    # Configuration for ps beacon should be a list of dicts
    if not isinstance(config, dict):
        return (
            False,
            "Configuration for ps beacon must be a dictionary with key 'processes' that contains a list.",
        )
    else:
        if "processes" not in config:
            return False, "Configuration for ps beacon requires processes."
        else:
            if not isinstance(config["processes"], list):
                return False, "Processes for ps beacon must be a dictionary."

    return True, "Valid beacon configuration"


def beacon(config):
    ret = []
    procs = []

    for x in psutil.process_iter():
        try:
            procs.append(x)
        except psutil.NoSuchProcess:
            continue

    for process in config.get("processes", {}):
        process_name = next(iter(process.keys()))
        found = [x for x in procs if x.name() == process_name]

        if (len(found) > 0 and process[process_name]["status"] == "stopped") or (
            len(found) < 1 and process[process_name]["status"] == "running"
        ):
            continue

        current_result = {process_name: {}}
        username = (
            process[process_name]["username"]
            if "username" in [k for k in process[process_name].keys()]
            else ""
        )

        if username:
            found = [
                x
                for x in procs
                if x.name() == process_name and x.username() == username
            ]

        current_result[process_name]["status"] = (
            "running" if len(found) > 0 else "stopped"
        )

        current_result[process_name]["instances"] = (
            []
            if len(found) == 0
            else sorted(map(contextPullProps, found), key=lambda x: x[0])
        )

        ret.append(current_result)

    return sorted(ret, key=lambda x: list(x.keys()))


def contextPullProps(process):
    with process.oneshot():
        return (process.pid, process.username(), process.create_time())
