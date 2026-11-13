"""Utility functions for arithmetic operations."""

from __future__ import annotations

__all__ = ["add"]


def add(a: int, b: int) -> int:
    """Return the sum of *a* and *b*.

    Parameters
    ----------
    a : int
        First operand.
    b : int
        Second operand.

    Returns
    -------
    int
        The sum of *a* and *b*.

    Examples
    --------
    >>> add(2, 3)
    5
    """
    return a + b


if __name__ == "__main__":
    import doctest

    doctest.testmod()
