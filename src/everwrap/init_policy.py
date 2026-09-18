"""Create a private, disabled policy without replacing existing settings."""

from pathlib import Path
from .private_files import restrict_file


def initialize(path: Path):
    try:
        stream = path.open("xb")
    except FileExistsError:
        return False
    try:
        with stream:
            restrict_file(path)
            stream.write(b'{"access_mode":"denylist","content_mode":"blocked"}\n')
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return True


if __name__ == "__main__":
    created = initialize(Path(__file__).resolve().parents[2] / ".everwrap-local.json")
    print("Private policy created; note access is disabled." if created else
          "Existing policy preserved.")
