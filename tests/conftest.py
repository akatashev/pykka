import logging
import threading
import time
from collections import namedtuple

import pytest

from pykka import ActorRegistry, ThreadingActor, ThreadingFuture, ThreadingScheduler

from tests.log_handler import PykkaTestLogHandler


Runtime = namedtuple(
    "Runtime",
    ["name", "actor_class", "event_class", "future_class", "sleep_func", "scheduler_class"],
)


class NullCollector(pytest.collect.File):
    def collect(self):
        return []


RUNTIMES = {
    "threading": pytest.param(
        Runtime(
            name="threading",
            actor_class=ThreadingActor,
            event_class=threading.Event,
            future_class=ThreadingFuture,
            sleep_func=time.sleep,
            scheduler_class=ThreadingScheduler
        ),
        id="threading",
    )
}

try:
    import gevent
    import gevent.event
    from pykka.gevent import GeventActor, GeventFuture, GeventScheduler
except ImportError:
    RUNTIMES["gevent"] = pytest.param(
        None,
        id="gevent",
        marks=pytest.mark.skip(reason="skipping gevent tests"),
    )
else:
    RUNTIMES["gevent"] = pytest.param(
        Runtime(
            name="gevent",
            actor_class=GeventActor,
            event_class=gevent.event.Event,
            future_class=GeventFuture,
            sleep_func=gevent.sleep,
            scheduler_class=GeventScheduler
        ),
        id="gevent",
    )

try:
    import eventlet
    from pykka.eventlet import EventletActor, EventletEvent, EventletFuture, EventletScheduler
except ImportError:
    RUNTIMES["eventlet"] = pytest.param(
        None,
        id="eventlet",
        marks=pytest.mark.skip(reason="skipping eventlet tests"),
    )
else:
    RUNTIMES["eventlet"] = pytest.param(
        Runtime(
            name="eventlet",
            actor_class=EventletActor,
            event_class=EventletEvent,
            future_class=EventletFuture,
            sleep_func=eventlet.sleep,
            scheduler_class=EventletScheduler
        ),
        id="eventlet",
    )


@pytest.fixture(scope="session")
def eventlet_runtime():
    return RUNTIMES["eventlet"].values[0]


@pytest.fixture(scope="session")
def gevent_runtime():
    return RUNTIMES["gevent"].values[0]


@pytest.fixture(scope="session", params=RUNTIMES.values())
def runtime(request):
    return request.param


@pytest.fixture
def stop_all():
    yield
    ActorRegistry.stop_all()


@pytest.fixture
def log_handler():
    log_handler = PykkaTestLogHandler()

    root_logger = logging.getLogger()
    root_logger.addHandler(log_handler)
    # pytest sets the root logger level to WARNING. We reset it to NOTSET
    # so that all log messages reaches our log handler.
    root_logger.setLevel(logging.NOTSET)

    yield log_handler

    log_handler.close()


@pytest.fixture
def events(runtime):
    class Events:
        on_start_was_called = runtime.event_class()
        on_stop_was_called = runtime.event_class()
        on_failure_was_called = runtime.event_class()
        greetings_was_received = runtime.event_class()
        actor_registered_before_on_start_was_called = runtime.event_class()

    return Events()


@pytest.fixture(scope="module")
def early_failing_actor_class(runtime):
    class EarlyFailingActor(runtime.actor_class):
        def __init__(self, events):
            super().__init__()
            self.events = events

        def on_start(self):
            try:
                raise RuntimeError("on_start failure")
            finally:
                self.events.on_start_was_called.set()

    return EarlyFailingActor


@pytest.fixture(scope="module")
def late_failing_actor_class(runtime):
    class LateFailingActor(runtime.actor_class):
        def __init__(self, events):
            super().__init__()
            self.events = events

        def on_start(self):
            self.stop()

        def on_stop(self):
            try:
                raise RuntimeError("on_stop failure")
            finally:
                self.events.on_stop_was_called.set()

    return LateFailingActor


@pytest.fixture(scope="module")
def failing_on_failure_actor_class(runtime):
    class FailingOnFailureActor(runtime.actor_class):
        def __init__(self, events):
            super().__init__()
            self.events = events

        def on_receive(self, message):
            if message.get("command") == "raise exception":
                raise Exception("on_receive failure")
            else:
                super().on_receive(message)

        def on_failure(self, *args):
            try:
                raise RuntimeError("on_failure failure")
            finally:
                self.events.on_failure_was_called.set()

    return FailingOnFailureActor


@pytest.fixture
def future(runtime):
    return runtime.future_class()


@pytest.fixture
def futures(runtime):
    return [runtime.future_class() for _ in range(3)]
