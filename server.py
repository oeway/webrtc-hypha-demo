import argparse
import asyncio
import logging
import fractions

import numpy as np
from av import VideoFrame
from imjoy_rpc.hypha import login, connect_to_server, register_rtc_service

from aiortc import MediaStreamTrack


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
        # frame = await self.track.recv()
        img = np.random.randint(0, 155, (150, 300, 3)).astype('uint8')
        new_frame = VideoFrame.from_ndarray(img, format="bgr24")
        new_frame.pts = self.count # frame.pts
        self.count+=1
        new_frame.time_base = fractions.Fraction(1, 1000)
        return new_frame

    
async def start_service(service_id, workspace=None, token=None):
    client_id = service_id + "-client"
    token = await login({"server_url": "https://ai.imjoy.io",})
    print(f"Starting service...")
    server = await connect_to_server(
        {
            "client_id": client_id,
            "server_url": "https://ai.imjoy.io",
            "workspace": workspace,
            "token": token,
        }
    )
    
    # print("Workspace: ", workspace, "Token:", await server.generate_token({"expires_in": 3600*24*100}))
    
    async def on_init(peer_connection):
        @peer_connection.on("track")
        def on_track(track):
            print(f"Track {track.kind} received")
            peer_connection.addTrack(
                VideoTransformTrack()
            )
            @track.on("ended")
            async def on_ended():
                print(f"Track {track.kind} ended")
    
    def move(direction, context=None):
        print("move: ", direction)
    
    def snap(context=None):
        print("snap an image")
        
    await server.register_service(
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
    
    # coturn = await server.get_service("coturn")
    # ice_servers = await coturn.get_rtc_ice_servers()
    # print("ICE servers:", ice_servers)
    # obtain it from https://ai.imjoy.io/public/services/coturn/get_rtc_ice_servers
    # ice_servers = [{"username":"1688956731:gvo9P4j7vs3Hhr6WqTUnen","credential":"yS9Vjds2jQg0qfq7xtlbwWspZQE=","urls":["turn:ai.imjoy.io:3478","stun:ai.imjoy.io:3478"]}]

    await register_rtc_service(
        server,
        service_id=service_id,
        config={
            "visibility": "public",
            # "ice_servers": ice_servers,
            "on_init": on_init,
        },
    )
    
    # svc = await get_rtc_service(server, service_id)
    # mc = await svc.get_service("microscope-control")
    # await mc.move("left")

    print(
        f"Service (client_id={client_id}, service_id={service_id}) started successfully, available at https://ai.imjoy.io/{server.config.workspace}/services"
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

    loop = asyncio.get_event_loop()
    loop.create_task(start_service(
        args.service_id,
        workspace=None,
        token=None,
    ))
    loop.run_forever()

    
