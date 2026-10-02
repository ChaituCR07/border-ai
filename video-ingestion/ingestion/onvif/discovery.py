from dataclasses import dataclass
from typing import List


@dataclass
class DiscoveredCamera:
    name: str
    host: str
    port: int
    rtsp_url: str


class OnvifDiscovery:
    """Placeholder. A real implementation would use WS-Discovery to find devices
    on the LAN and an ONVIF client (e.g. the `onvif-zeep` package) to read each
    device's stream profile and RTSP URI."""

    def discover(self, timeout: float = 5.0) -> List[DiscoveredCamera]:
        raise NotImplementedError("ONVIF discovery is planned for a later phase")
