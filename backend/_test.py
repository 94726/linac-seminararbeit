from unittest.mock import AsyncMock, Mock
import pytest

print()

from .control_modes import (
    ControlMode,
    OscillationMode,
    control_modes,
    register_mode,
)


class AsyncCounter:
    def __init__(self, initial=0) -> None:
        self.count = initial

    async def increment(self):
        self.count += 1


def test_register_mode():
    @register_mode('__test')
    class TestMode(ControlMode):
        pass

    assert '__test' in control_modes


class TestOscillation:
    @pytest.mark.parametrize(
        'test_input,expected_drift_tubes,expected_stages',
        [(9, 8, 16), (15, 14, 28), (20, 20, 40)],
    )
    def test_correct_drift_tube_count(
        self, test_input, expected_drift_tubes, expected_stages
    ):
        mock_controls = Mock()
        mock_controls.drift_tube_count = test_input
        mode = OscillationMode(mock_controls)

        assert mode.last_drift_tube == expected_drift_tubes
        assert mode.total_tube_passes == expected_stages

    @pytest.mark.parametrize(
        'ldr_triggers,expected_turns',
        [
            (1, 1),
            (2, 2),
            (3, 3),
            (4, 3),
            (5, 4),
            (6, 5),
            (7, 6),
            (8, 7),
            (9, 8),
            (10, 9),
            (11, 10),
            (12, 10),
            (13, 11),
            (14, 12),
            (15, 13),
            (16, 14),
        ],
    )
    @pytest.mark.asyncio
    async def test_correct_turning(self, ldr_triggers, expected_turns):
        turn_counter = AsyncCounter()
        mock_controls = AsyncMock()
        mock_controls.turn = turn_counter.increment
        mock_controls.drift_tube_count = 9
        mode = OscillationMode(mock_controls)

        for i in range(ldr_triggers):
            await mode.on_light_sensor_enter()
            await mode.on_light_sensor_leave()

        assert turn_counter.count == expected_turns

    @pytest.mark.asyncio
    async def test_correctly_restarts(self):
        turn_counter = AsyncCounter()
        mock_controls = AsyncMock()
        mock_controls.turn = turn_counter.increment
        mock_controls.drift_tube_count = 9
        mode = OscillationMode(mock_controls)
        assert mode.next_tube == 1

        for i in range(16):
            await mode.on_light_sensor_enter()
            await mode.on_light_sensor_leave()

        assert mode.next_tube == 1
