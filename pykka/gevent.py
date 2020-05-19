import sys

import gevent
import gevent.event
import gevent.queue
from gevent.greenlet import Greenlet

from pykka import Actor, Future, Scheduler, Timeout

__all__ = ["GeventActor", "GeventFuture", "GeventScheduler"]


class GeventFuture(Future):
    """
    :class:`GeventFuture` implements :class:`pykka.Future` for use with
    :class:`GeventActor`.

    It encapsulates a :class:`gevent.event.AsyncResult` object which may be
    used directly, though it will couple your code with gevent.
    """

    #: The encapsulated :class:`gevent.event.AsyncResult`
    async_result = None

    def __init__(self, async_result=None):
        super().__init__()
        if async_result is None:
            async_result = gevent.event.AsyncResult()
        self.async_result = async_result

    def get(self, timeout=None):
        try:
            return super().get(timeout=timeout)
        except NotImplementedError:
            pass

        try:
            return self.async_result.get(timeout=timeout)
        except gevent.Timeout as e:
            raise Timeout(e)

    def set(self, value=None):
        assert not self.async_result.ready(), "value has already been set"
        self.async_result.set(value)

    def set_exception(self, exc_info=None):
        assert exc_info is None or len(exc_info) == 3
        exc_info = exc_info or sys.exc_info()
        self.async_result.set_exception(exc_info[1], exc_info=exc_info)


class GeventActor(Actor):
    """
    :class:`GeventActor` implements :class:`pykka.Actor` using the `gevent
    <http://www.gevent.org/>`_ library. gevent is a coroutine-based Python
    networking library that uses greenlet to provide a high-level synchronous
    API on top of libevent event loop.

    This is a very fast implementation.
    """

    @staticmethod
    def _create_actor_inbox():
        return gevent.queue.Queue()

    @staticmethod
    def _create_future():
        return GeventFuture()

    def _start_actor_loop(self):
        gevent.Greenlet.spawn(self._actor_loop)


class GeventScheduler(Scheduler):
    """
    A basic Pykka Scheduler service based on Akka Scheduler behaviour.

    Its main purpose is to `tell` a message to an actor after a specified
    delay or to do it periodically. It isn't a long-term scheduler
    and is expected to be used for retransmitting messages or to schedule
    periodic startup of an actor-based data processing pipeline.

    Gevent scheduler is based on gevent.Greenlet.
    """

    @staticmethod
    def _get_timer(delay, func, *args) -> Greenlet:
        """
        Creates a Greenlet to schedule function execution.

        Args:
            delay: Delay before function execution.
            func: Function to execute.
            args: Function arguments.
        Returns: Greenlet object.
        """
        timer = gevent.spawn_later(delay, func, *args)
        return timer
