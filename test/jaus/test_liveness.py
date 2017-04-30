import pytest

from format.jaus.core.liveness import (
    QueryHeartbeatPulse,
    ReportHeartbeatPulse,
)
from format.jaus.services import LivenessService
from format.jaus import Message

@pytest.fixture
def core_service_list():
    return [LivenessService]

@pytest.mark.asyncio(forbid_global_loop=True)
async def test_liveness(test_connection, component_id):
    await test_connection.send_message(
        QueryHeartbeatPulse()._write(),
        destination_id=component_id)

    result, src = await test_connection.listen(timeout=2)
    assert Message._read(result) == ReportHeartbeatPulse()
    assert src == component_id
