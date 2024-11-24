import asyncio
import json
from contextlib import asynccontextmanager
from typing import Any, Literal

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from fastapi.websockets import WebSocketState
from gpiozero import Button, DigitalInputDevice
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from .voltage_control import VoltageControl


class BaseSchema(BaseModel):
    """Converts camelcase to snake_case and vice-versa"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class ConnectionManager:
    def __init__(self):
        self.active_connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        print("disconnect", self.active_connections)
        self.active_connections.remove(websocket)
        print(self.active_connections)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: Any):
        for connection in self.active_connections:
            if connection.client_state != WebSocketState.CONNECTED:
                self.active_connections.remove(connection)
                continue
            print(connection.client_state)
            await connection.send_text(json.dumps(jsonable_encoder(message)))


voltage = VoltageControl(pwm_channel=0)

type ControlModes = Literal["manual"] | Literal["automatic"]
control_mode: ControlModes = "manual"

manager = ConnectionManager()


async def turn():
    voltage.turn()
    await manager.broadcast({"firstVoltage": voltage.status_num})


async def reset():
    voltage.turn_to("idle")
    await manager.broadcast({"firstVoltage": 0})


async def light_sensor_trigger():
    if control_mode == "manual":
        return
    await turn()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global button
    button = Button(2, bounce_time=0.05)
    voltage.turn_to("idle")

    button.when_pressed = lambda: asyncio.run(turn())

    light_sensor = DigitalInputDevice(16, bounce_time=0.03)
    light_sensor.when_activated = lambda: asyncio.run(light_sensor_trigger())
    light_sensor.when_deactivated = lambda: print("ball left")

    yield  # Clean up
    voltage.turn_to("idle")


app = FastAPI(lifespan=lifespan)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    await manager.broadcast(
        {"firstVoltage": voltage.status_num, "controlMode": control_mode}
    )
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Message text was: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.post("/api/control/turn")
async def post_turn():
    return await turn()


@app.post("/api/control/reset")
async def post_reset():
    return await reset()


class Configuration(BaseSchema):
    control_mode: ControlModes


@app.post("/api/configuration")
async def post_mode(config: Configuration):
    global control_mode
    print(config)
    control_mode = config.control_mode
    await manager.broadcast({"controlMode": control_mode})
