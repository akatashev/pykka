from typing import (
    Any,
    Callable,
    Generator,
    Generic,
    Iterable,
    Optional,
    TypeVar,
)

from pykka._types import OptExcInfo

_T = TypeVar("_T")
I = TypeVar("I")  # noqa # For when T is Iterable[I]

_M = TypeVar("_M")  # For Future.map()
_R = TypeVar("_R")  # For Future.reduce()

GetHookFunc = Callable[[Optional[float]], _T]

class Future(Generic[_T]):
    _get_hook: Optional[GetHookFunc]
    _get_hook_result: Optional[_T]
    def get(self, timeout: Optional[float] = ...) -> _T: ...
    def set(self, value: Optional[_T] = ...) -> None: ...
    def set_exception(self, exc_info: Optional[OptExcInfo] = ...) -> None: ...
    def set_get_hook(self, func: GetHookFunc) -> None: ...
    def filter(
        self: Future[Iterable[I]], func: Callable[[I], bool]  # noqa
    ) -> Future[Iterable[I]]: ...  # noqa
    def join(self, *futures: Future[Any]) -> Future[Iterable[Any]]: ...
    def map(self, func: Callable[[_T], _M]) -> Future[_M]: ...
    def reduce(
        self: Future[Iterable[I]],  # noqa
        func: Callable[[_R, I], _R],  # noqa
        *args: _R,
    ) -> Future[_R]: ...
    def __await__(self) -> Generator[None, None, _T]: ...

def get_all(
    futures: Iterable[Future[Any]], timeout: Optional[float] = ...
) -> Iterable[Any]: ...
