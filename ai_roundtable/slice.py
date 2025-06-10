import typing


T = typing.TypeVar("T")


def find(
    items: typing.Iterable[T],
    pred: typing.Callable[[T], bool],
) -> T | None:
    """Find an element which satisfies pred."""
    return next(
        (x for x in items if pred(x)),
        None,
    )
