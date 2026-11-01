import json

from Web_Arayuzu.Main import SyncEventHub


class FakeConnection:
    def __init__(self, should_fail=False):
        self.frames = []
        self.should_fail = should_fail

    def sendall(self, frame):
        if self.should_fail:
            raise OSError("connection closed")
        self.frames.append(frame)


def test_publish_counts_delivered_sessions_and_keeps_tenants_isolated():
    hub = SyncEventHub()
    selected_session = FakeConnection()
    excluded_source = FakeConnection()
    failed_session = FakeConnection(should_fail=True)
    other_tenant_session = FakeConnection()
    hub.register("tenant-a", selected_session, "desktop-a")
    hub.register("tenant-a", excluded_source, "source-device")
    hub.register("tenant-a", failed_session, "desktop-failed")
    hub.register("tenant-b", other_tenant_session, "desktop-b")

    payload = {"type": "license_updated", "license": {"allowed": True}}
    delivered = hub.publish("tenant-a", payload, source_device_id="source-device")

    assert delivered == 1
    assert json.loads(selected_session.frames[0][2:]) == payload
    assert excluded_source.frames == []
    assert failed_session.frames == []
    assert other_tenant_session.frames == []

    assert hub.publish("tenant-a", payload) == 2
    assert len(selected_session.frames) == 2
    assert len(excluded_source.frames) == 1
    assert len(other_tenant_session.frames) == 0
