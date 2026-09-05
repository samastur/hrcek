"""Optional debugpy listener.

Imported by manage.py before Django is configured, so this module must
not import Django or anything that does.
"""

from __future__ import annotations


def maybe_start_debugger(*, enabled: bool, port: int, wait: bool) -> bool:
    """Start a debugpy listener on localhost. Returns whether it did.

    debugpy is imported lazily so that a production process never loads
    it, and so the disabled path costs nothing.
    """
    if not enabled:
        return False
    import debugpy  # noqa: PLC0415  (lazy by design; see docstring)

    debugpy.listen(("127.0.0.1", port))
    if wait:
        debugpy.wait_for_client()
    return True
