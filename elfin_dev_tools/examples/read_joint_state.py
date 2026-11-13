"""Read and print the latest Elfin joint state using the Python client.

Run from the repository root with:

    uv run python elfin_dev_tools/examples/read_joint_state.py
"""

from elfin_dev_tools import ElfinApiError, ElfinClient


def main() -> int:
    try:
        with ElfinClient() as client:
            state = client.joint_state()
    except ElfinApiError as exc:
        print("Could not read Elfin joint state: {}".format(exc))
        return 1

    age = state.get("age_sec")
    age_text = "unknown" if age is None else "{:.3f}s".format(float(age))
    print("Joint state (age {})".format(age_text))

    names = state.get("names") or []
    positions_deg = state.get("positions_deg") or []
    if not names:
        print("No joints in the API response.")
        return 0

    for index, name in enumerate(names):
        if index < len(positions_deg):
            print("{}: {:.2f} degrees".format(name, float(positions_deg[index])))
        else:
            print("{}: position unavailable".format(name))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
