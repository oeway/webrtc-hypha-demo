import argparse
import fractions
import logging
import numpy as np
import time
from av import VideoFrame
from aiortc import MediaStreamTrack
from hypha_rpc.sync import login, connect_to_server, register_rtc_service, get_rtc_service

logger = logging.getLogger("pc")

class VideoTransformTrack(MediaStreamTrack):
    """
    A video stream track that transforms frames from an another track.
    """

    kind = "video"

    def __init__(self):
        super().__init__()  # don't forget this!
        self.count = 0

    async def recv(self):
        img = np.random.randint(0, 155, (150, 300, 3)).astype('uint8')
        new_frame = VideoFrame.from_ndarray(img, format="bgr24")
        new_frame.pts = self.count 
        self.count+=1
        new_frame.time_base = fractions.Fraction(1, 1000)
        return new_frame

    
def start_service(service_id, workspace=None):
    client_id = service_id + "-client"
    token = login({"server_url": "https://hypha.aicell.io",})
    print(f"Starting service...")
    server = connect_to_server(
        {
            "client_id": client_id,
            "server_url": "https://hypha.aicell.io",
            "workspace": workspace,
            "token": token,
        }
    )
    
    def on_init(peer_connection):
        @peer_connection.on("track")
        def on_track(track):
            print(f"Track {track.kind} received")
            peer_connection.addTrack(
                VideoTransformTrack()
            )

            @track.on("ended")
            def on_ended():
                print(f"Track {track.kind} ended")
    
    def move(value, axis, is_absolute, is_blocking, context=None):
        print("move: ", value, axis, is_absolute, is_blocking)
    
    def snap(context=None):
        print("snap an image")
        
    server.register_service(
        {
            "id": "microscope-control",
            "config":{
                "visibility": "public",
                "run_in_executor": True,
                "require_context": True,   
            },
            "type": "echo",
            "move": move,
            "snap": snap
        }
    )
    
    # ice_servers = [{"username":"1688956731:gvo9P4j7vs3Hhr6WqTUnen","credential":"yS9Vjds2jQg0qfq7xtlbwWspZQE=","urls":["turn:hypha.aicell.io:3478","stun:hypha.aicell.io:3478"]}]

    register_rtc_service(
        server,
        service_id=service_id,
        config={
            "visibility": "public",
            # "ice_servers": ice_servers,
            "on_init": on_init,
        },
    )
    
    # svc = get_rtc_service(server, service_id)
    # mc = svc.get_service("microscope-control")
    # mc.move("left")
    
    print(
        f"Service (client_id={client_id}, service_id={service_id}) started successfully, available at https://hypha.aicell.io/{server.config.workspace}/services"
    )
    print(f"You can access the webrtc stream at https://oeway.github.io/webrtc-hypha-demo/?service_id={service_id}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="WebRTC demo for video streaming"
    )
    parser.add_argument("--service-id", type=str, default="aiortc-demo", help="The service id")
    parser.add_argument("--verbose", "-v", action="count")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    start_service(
        args.service_id,
        workspace=None,
    )
    while True:
        time.sleep(1)
