from __future__ import annotations
import asyncio
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Literal, Optional

from .control_modes import ControlMode, ManualMode, control_modes, ControlModes
from .fastapi_utils import BaseSchema, WebsocketManager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from gpiozero import Button, DigitalInputDevice

from .voltage_control import VoltageControl

DRIFT_TUBE_COUNT = 9

ws_manager = WebsocketManager()

if not TYPE_CHECKING:
    voltage = VoltageControl(pwm_channel=0)  # -> gpio18


class Controls:
    drift_tube_count = DRIFT_TUBE_COUNT
    ws_manager = ws_manager

    @staticmethod
    async def turn():
        voltage.turn()
        await ws_manager.broadcast({'firstVoltage': voltage.status_num})

    @staticmethod
    async def reset():
        voltage.turn_to('idle')
        await ws_manager.broadcast({'firstVoltage': 0})


control_mode: ControlMode = ManualMode(Controls)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global button
    button = Button(2, bounce_time=0.05)
    voltage.turn_to('idle')

    button.when_pressed = lambda: asyncio.run(Controls.turn())

    light_sensor = DigitalInputDevice(5, bounce_time=0.03, pull_up=False)
    light_sensor.when_activated = lambda: asyncio.run(
        control_mode.on_light_sensor_enter()
    )
    light_sensor.when_deactivated = lambda: asyncio.run(
        control_mode.on_light_sensor_leave()
    )
    yield  # Clean up
    voltage.close()


app = FastAPI(lifespan=lifespan)


@app.websocket('/ws')
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    await ws_manager.broadcast(
        {'firstVoltage': voltage.status_num, 'controlMode': str(control_mode)}
    )
    await control_mode.on_websocket_connect()
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f'Message text was: {data}')
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


@app.post('/api/control/turn')
async def post_turn():
    return await Controls.turn()


@app.post('/api/control/reset')
async def post_reset():
    await control_mode.on_mode_stop()
    return await Controls.reset()

class ModeConfiguration(BaseSchema):
    control_mode: Optional[ControlModes] | None = None
    operation: Optional[Literal['start', 'stop']] | None = None


@app.post('/api/configuration')
async def post_mode(config: ModeConfiguration):
    global control_mode

    if config.control_mode and config.control_mode != str(control_mode):
        await control_mode.on_mode_stop()
        await Controls.reset()
        control_mode = control_modes[config.control_mode](Controls)

    if config.operation == 'start':
        await control_mode.on_mode_start()
    elif config.operation == 'stop':
        await control_mode.on_mode_stop()
        
    await ws_manager.broadcast({'controlMode': str(control_mode)})
