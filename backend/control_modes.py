from __future__ import annotations
import asyncio
import time
from typing import TYPE_CHECKING, Awaitable, Literal

from abc import ABC

if TYPE_CHECKING:
    import main

type ControlModes = Literal['manual', 'automatic', 'oscillation']

control_Mode: ControlMode | None
control_modes: dict[str, ControlMode] = {}


def exec_coroutine(coroutine: Awaitable):
    loop = asyncio.get_event_loop()
    if loop.is_running():
        return loop.create_task(coroutine)
    asyncio.run(coroutine)


def register_mode[T: ControlMode](name: ControlModes):
    def decorate(cls: T) -> T:
        cls.__str__ = lambda self: name
        control_modes[name] = cls
        return cls

    return decorate


class ControlMode(ABC):
    def __init__(self, controls: main.Controls):
        self.controls = controls
        self._running = False

    @property
    def running(self):
        return self._running

    @running.setter
    def running(self, value: bool):
        self._running = value
        exec_coroutine(
            self.controls.ws_manager.broadcast({'controlModeRunning': self._running})
        )

    async def on_light_sensor_enter(self):
        pass

    async def on_light_sensor_leave(self):
        pass

    async def on_mode_start(self):
        """Used for modes that have to be started explicitly"""
        self.running = True

    async def on_mode_stop(self):
        """Used to cleanup modes on reset or explicit stop"""
        self.running = False

    async def on_websocket_connect(self):
        self.running = self.running  # send controlModeRunning


@register_mode('manual')
class ManualMode(ControlMode):  # doesn't do anything, manual is hardcoded in main.py
    def __init__(self, controls: main.Controls):
        super().__init__(controls)


@register_mode('automatic')
class AutomaticMode(ControlMode):
    def __init__(self, controls: main.Controls):
        super().__init__(controls)
        self.last_enter_epoch_ms: int = 0
        self.start_epoch_ms: int = 0
        self.ldr_timings = []

    async def on_mode_start(self):
        await super().on_mode_start()
        self.ldr_timings = []
        self.start_epoch_ms = time.time() * 1000
        await self.controls.turn()

    async def on_mode_stop(self):
        await super().on_mode_stop()
        self.ldr_timings = []
        await self.send_ldr_timings()

    async def on_light_sensor_enter(self):
        if not self.running:
            return
        self.last_enter_epoch_ms = time.time() * 1000

    async def on_light_sensor_leave(self):
        if not self.running:
            return
        await self.controls.turn()

        self.ldr_timings.append(
            {'enter': self.last_enter_epoch_ms, 'leave': time.time() * 1000}
        )
        if len(self.ldr_timings) >= self.controls.drift_tube_count:
            self.running = False
            await self.controls.reset()

        await self.send_ldr_timings()

    async def send_ldr_timings(self):
        await self.controls.ws_manager.broadcast(
            {
                'ldrData': {'start': self.start_epoch_ms, 'timings': self.ldr_timings},
            }
        )

    async def on_websocket_connect(self):
        await super().on_websocket_connect()
        await self.send_ldr_timings()


def is_even(num) -> bool:
    return num % 2 == 0


@register_mode('oscillation')
class OscillationMode(ControlMode):
    def __init__(self, controls: main.Controls):
        super().__init__(controls)
        self._next_tube = 1

    async def on_mode_start(self):
        await super().on_mode_start()
        self.start_epoch_ms = time.time() * 1000
        self._next_tube = 1
        await self.controls.turn()

    async def on_mode_stop(self):
        await super().on_mode_stop()
        self._next_tube = 1

    @property
    def next_tube(self):
        return self._next_tube

    @next_tube.setter
    def next_tube(self, value: int):
        self._next_tube = value
        if value > 16:
            self._next_tube = 1

    @property
    def total_tube_passes(self):
        return self.last_drift_tube * 2

    async def trigger(self):
        # skips at the middle parts at each half period, to start decelerating
        # ->  1   2   3   x   5   6   7   8
        #    16  15  14  13  x  11  10   9 <-
        if (
            self.next_tube != self.total_tube_passes // 4
            and self.next_tube != (self.total_tube_passes // 4) * 3
        ):
            await self.controls.turn()

    @property
    def last_drift_tube(self):
        """the most possible even number of drift tubes"""
        return (self.controls.drift_tube_count // 2) * 2

    async def on_light_sensor_enter(self):
        if self.next_tube > self.total_tube_passes // 2:
            await self.trigger()

    async def on_light_sensor_leave(self):
        # make sure to skip 0, as we sensor_enter will set the current to 0 which is smaller than half of passes, triggering leave as well
        if self.next_tube <= self.total_tube_passes // 2:
            await self.trigger()

        self.next_tube += 1
