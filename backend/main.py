from __future__ import annotations
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Optional
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .control_modes import ControlMode, ManualMode, control_modes, ControlModes
from .fastapi_utils import BaseSchema, WebsocketManager
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from gpiozero import DigitalInputDevice
import warnings

from .voltage_control import VoltageControl

DRIFT_TUBE_COUNT = 9
LIGHT_SENSOR_PINS = (20, 21)

ws_manager = WebsocketManager()

# otherwise causes issues with importing in tests, as the environment doesn't have gpio
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
    voltage.turn_to('idle')
    light_sensors = []  # keeps light_sensors in memory so gpiozero doesn't clean them up

    for light_sensor_pin in LIGHT_SENSOR_PINS:
        light_sensor = DigitalInputDevice(
            light_sensor_pin, bounce_time=0.02, pull_up=False
        )
        light_sensor.when_activated = lambda: asyncio.run(
            control_mode.on_light_sensor_enter()
        )
        light_sensor.when_deactivated = lambda: asyncio.run(
            control_mode.on_light_sensor_leave()
        )
        light_sensors.append(light_sensor)

    yield  # Clean up
    voltage.close()


app = FastAPI(lifespan=lifespan)
api = FastAPI()

frontend_files_path = Path(__file__).parent / '../nuxt/.output/public'


@app.get('/', response_class=FileResponse)
async def index(request: Request):
    return frontend_files_path / 'index.html'


app.mount('/api', api)
if frontend_files_path.exists():
    app.mount('/', StaticFiles(directory=frontend_files_path), name='static')
else:
    warnings.warn(
        'Static files not found, please run "bun generate" to build nuxt frontend, see README.md'
    )


@api.websocket('/ws')
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


@api.post('/control/turn')
async def post_turn():
    return await Controls.turn()


@api.post('/control/reset')
async def post_reset():
    await control_mode.on_mode_stop()
    return await Controls.reset()


class ModeConfiguration(BaseSchema):
    control_mode: Optional[ControlModes] | None = None
    operation: Optional[Literal['start', 'stop']] | None = None


@api.post('/configuration')
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
