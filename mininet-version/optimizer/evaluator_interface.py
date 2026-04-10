import time
from config import LOSS_FILE


def wait_for_loss(previous_loss, timeout=60):
    start = time.time()

    while time.time() - start < timeout:
        try:
            with open(LOSS_FILE) as f:
                lines = f.readlines()
                if lines:
                    last = float(lines[-1].strip().split(",")[1])

                    if previous_loss is None or last != previous_loss:
                        return last
        except:
            pass

        time.sleep(2)

    return None