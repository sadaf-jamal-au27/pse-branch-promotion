"""Sample service for the PSE pilot.

The build workflow lints and compiles this package when a pull request targets
main. UAT and production do not compile it again.
"""


def service_name() -> str:
    return "pse-billing"


def health() -> dict:
    return {"service": service_name(), "status": "ok"}
