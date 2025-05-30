import argparse
import asyncio
import logging
import fractions
import aiohttp

import numpy as np
from av import VideoFrame
from hypha_rpc import login, connect_to_server, register_rtc_service
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from aiortc import MediaStreamTrack

logger = logging.getLogger("pc")

# FastAPI app instance
app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def root():
    with open("index.html", "r") as file:
        HTML_CONTENT = file.read()
    return HTML_CONTENT

@app.get("/api/v1/test")
async def test():
    return {"message": "Hello, WebRTC demo is working!"}

async def serve_fastapi(args, context=None):
    # context can be used for authorization, e.g., checking the user's permission
    # e.g., check user id against a list of allowed users
    scope = args["scope"]
    print(f'{context["user"]["id"]} - {scope["client"]} - {scope["method"]} - {scope["path"]}')
    await app(args["scope"], args["receive"], args["send"])

# Global state for microscope position
microscope_state = {
    "x": 240,  # Center X
    "y": 180,  # Center Y
    "target_x": 240,
    "target_y": 180,
    "velocity_x": 0.0,  # Current velocity in X direction
    "velocity_y": 0.0,  # Current velocity in Y direction
    "max_acceleration": 8.0,  # Maximum acceleration when starting movement
    "max_velocity": 15.0,     # Maximum velocity
    "damping": 0.85,          # Velocity damping for smooth deceleration
    "attraction_strength": 0.3,  # How strongly it's attracted to target
    "objects": [
        {"x": 100, "y": 100, "color": [255, 100, 100], "size": 30},
        {"x": 300, "y": 200, "color": [100, 255, 100], "size": 25},
        {"x": 200, "y": 250, "color": [100, 100, 255], "size": 35},
        {"x": 350, "y": 120, "color": [255, 255, 100], "size": 20},
        {"x": 150, "y": 300, "color": [255, 100, 255], "size": 28},
    ]
}

class VideoTransformTrack(MediaStreamTrack):
    """
    A video stream track that transforms frames from an another track.
    """

    kind = "video"

    def __init__(self):
        super().__init__()  # don't forget this!
        self.count = 0
        self.running = True
        self.start_time = None
        print("VideoTransformTrack initialized")

    def draw_circle(self, img, center_x, center_y, radius, color):
        """Draw a filled circle on the image"""
        height, width = img.shape[:2]
        y, x = np.ogrid[:height, :width]
        mask = (x - center_x)**2 + (y - center_y)**2 <= radius**2
        img[mask] = color

    def draw_crosshair(self, img, center_x, center_y, size=20, color=[255, 255, 255]):
        """Draw a crosshair at the specified position"""
        height, width = img.shape[:2]
        
        # Horizontal line
        if 0 <= center_y < height:
            start_x = max(0, center_x - size)
            end_x = min(width, center_x + size)
            img[center_y, start_x:end_x] = color
        
        # Vertical line
        if 0 <= center_x < width:
            start_y = max(0, center_y - size)
            end_y = min(height, center_y + size)
            img[start_y:end_y, center_x] = color

    async def recv(self):
        if not self.running:
            print("VideoTransformTrack: recv() called but track is not running")
            raise Exception("Track stopped")
            
        try:
            import time
            
            # Initialize start time on first frame
            if self.start_time is None:
                self.start_time = time.time()
            
            # Calculate proper timing
            current_time = time.time()
            elapsed = current_time - self.start_time
            expected_frame = int(elapsed * 30)  # 30 FPS
            
            # Skip frames if we're behind, or wait if we're ahead
            if self.count < expected_frame:
                self.count = expected_frame
            elif self.count > expected_frame:
                await asyncio.sleep((self.count - expected_frame) / 30.0)
            
            # Physics-based movement with acceleration and deceleration
            # Calculate distance to target
            dx = microscope_state["target_x"] - microscope_state["x"]
            dy = microscope_state["target_y"] - microscope_state["y"]
            distance = np.sqrt(dx*dx + dy*dy)
            
            if distance > 0.1:  # Only apply forces if not at target
                # Normalize direction vectors
                dir_x = dx / distance
                dir_y = dy / distance
                
                # Calculate acceleration based on distance to target
                # Stronger acceleration when far, weaker when close
                acceleration_magnitude = min(
                    microscope_state["max_acceleration"], 
                    distance * microscope_state["attraction_strength"]
                )
                
                # Apply acceleration in direction of target
                accel_x = dir_x * acceleration_magnitude
                accel_y = dir_y * acceleration_magnitude
                
                # Update velocity with acceleration
                microscope_state["velocity_x"] += accel_x * (1/30.0)  # Frame time
                microscope_state["velocity_y"] += accel_y * (1/30.0)
                
                # Apply damping to velocity for smooth deceleration
                microscope_state["velocity_x"] *= microscope_state["damping"]
                microscope_state["velocity_y"] *= microscope_state["damping"]
                
                # Limit maximum velocity
                vel_magnitude = np.sqrt(
                    microscope_state["velocity_x"]**2 + microscope_state["velocity_y"]**2
                )
                if vel_magnitude > microscope_state["max_velocity"]:
                    scale = microscope_state["max_velocity"] / vel_magnitude
                    microscope_state["velocity_x"] *= scale
                    microscope_state["velocity_y"] *= scale
                
                # Update position based on velocity
                microscope_state["x"] += microscope_state["velocity_x"]
                microscope_state["y"] += microscope_state["velocity_y"]
                
                # Ensure position stays within bounds
                microscope_state["x"] = max(0, min(480, microscope_state["x"]))
                microscope_state["y"] = max(0, min(360, microscope_state["y"]))
                
                # Stop very small movements to avoid jitter
                if distance < 2.0 and vel_magnitude < 0.5:
                    microscope_state["x"] = microscope_state["target_x"]
                    microscope_state["y"] = microscope_state["target_y"]
                    microscope_state["velocity_x"] = 0.0
                    microscope_state["velocity_y"] = 0.0
            else:
                # At target, zero out velocity
                microscope_state["velocity_x"] = 0.0
                microscope_state["velocity_y"] = 0.0
            
            # Generate a frame with microscope view simulation
            t = self.count / 30.0  # time in seconds
            
            # Create a 480x360 frame
            height, width = 360, 480
            
            # Create a gradient background that simulates microscope lighting
            y_grad, x_grad = np.ogrid[:height, :width]
            center_x, center_y = width // 2, height // 2
            
            # Distance from center for vignette effect
            distance = np.sqrt((x_grad - center_x)**2 + (y_grad - center_y)**2)
            max_distance = np.sqrt(center_x**2 + center_y**2)
            vignette = 1 - (distance / max_distance) * 0.3
            
            # Reduce noise for better compression and quality
            # Use deterministic pattern instead of random noise
            pattern_noise = 3 * np.sin(x_grad * 0.1 + t * 0.5) * np.cos(y_grad * 0.1 + t * 0.3)
            base_intensity = 45 + 15 * np.sin(t * 0.5)
            background = (base_intensity + pattern_noise) * vignette
            
            # Create high-quality RGB image with better precision
            img = np.zeros((height, width, 3), dtype=np.float32)
            img[:, :, 0] = background * 0.85  # Slight blue tint
            img[:, :, 1] = background * 0.92
            img[:, :, 2] = background
            
            # Calculate view offset based on microscope position
            view_offset_x = int(microscope_state["x"] - center_x)
            view_offset_y = int(microscope_state["y"] - center_y)
            
            # Draw objects that move relative to microscope position
            for obj in microscope_state["objects"]:
                # Calculate object position relative to current view
                obj_x = obj["x"] - view_offset_x
                obj_y = obj["y"] - view_offset_y
                
                # Add smoother floating motion with reduced temporal variation
                float_x = obj_x + 3 * np.sin(t * 1.5 + obj["x"] * 0.01)
                float_y = obj_y + 2 * np.cos(t * 1.2 + obj["y"] * 0.01)
                
                # Only draw if object is visible in current view
                if -obj["size"] <= float_x <= width + obj["size"] and -obj["size"] <= float_y <= height + obj["size"]:
                    # Add smoother pulsing effect
                    pulse = 1 + 0.15 * np.sin(t * 2 + obj["x"] * 0.02)
                    size = int(obj["size"] * pulse)
                    
                    # Draw object with smoother glow effect for better compression
                    for glow_size in range(size + 8, size - 1, -1):
                        alpha = 0.4 * (1 - (glow_size - size) / 8) ** 2  # Quadratic falloff
                        glow_color = [obj["color"][i] * alpha for i in range(3)]
                        self.draw_circle_float(img, float_x, float_y, glow_size, glow_color)
                    
                    # Draw main object with precise colors
                    self.draw_circle_float(img, float_x, float_y, size, obj["color"])
            
            # Draw microscope crosshair at center with anti-aliasing
            self.draw_crosshair_float(img, center_x, center_y, 15, [255, 255, 255])
            
            # Add measurement grid with reduced intensity for better compression
            grid_spacing = 50
            grid_color = [60, 60, 60]  # Darker grid lines
            for i in range(0, width, grid_spacing):
                if i % (grid_spacing * 2) == 0:  # Major grid lines
                    img[:, i:min(i+1, width)] = grid_color
            for i in range(0, height, grid_spacing):
                if i % (grid_spacing * 2) == 0:  # Major grid lines
                    img[i:min(i+1, height), :] = grid_color
            
            # Add position indicator with solid colors
            pos_text_area = img[10:35, 10:200]
            pos_text_area[:] = [0, 0, 0]  # Black background
            
            # Add coordinate display as colored bars with better precision
            x_bar_length = int((microscope_state["x"] / 480) * 180)
            y_bar_length = int((microscope_state["y"] / 360) * 180)
            
            if x_bar_length > 0:
                img[15:20, 15:15+x_bar_length] = [255, 100, 100]  # Red for X
            if y_bar_length > 0:
                img[25:30, 15:15+y_bar_length] = [100, 255, 100]  # Green for Y
            
            # Add frame counter with solid colors
            frame_indicator = self.count % 60
            indicator_width = int((frame_indicator / 60) * 100)
            img[height-15:height-10, width-110:width-110+indicator_width] = [100, 100, 255]
            
            # Convert to uint8 with proper clipping for better quality
            img_uint8 = np.clip(img, 0, 255).astype(np.uint8)
            
            new_frame = VideoFrame.from_ndarray(img_uint8, format="bgr24")
            
            # Use proper timing based on frame count
            new_frame.pts = self.count
            new_frame.time_base = fractions.Fraction(1, 30)  # 30 FPS
            
            if self.count % 90 == 0:  # Log every 3 seconds
                print(f"VideoTransformTrack: Frame {self.count}, Microscope pos: ({microscope_state['x']:.1f}, {microscope_state['y']:.1f})")
            
            self.count += 1
            
            return new_frame
        except Exception as e:
            print(f"VideoTransformTrack: Error in recv(): {e}")
            self.running = False
            raise

    def draw_circle_float(self, img, center_x, center_y, radius, color):
        """Draw a filled circle on the float image with anti-aliasing"""
        height, width = img.shape[:2]
        y, x = np.ogrid[:height, :width]
        
        # Calculate distance from center
        distance = np.sqrt((x - center_x)**2 + (y - center_y)**2)
        
        # Create anti-aliased mask
        mask = np.zeros((height, width), dtype=np.float32)
        inside = distance <= radius
        edge = (distance > radius) & (distance <= radius + 1)
        
        mask[inside] = 1.0
        mask[edge] = radius + 1 - distance[edge]  # Smooth edge
        
        # Apply color with alpha blending
        for i in range(3):
            img[:, :, i] = img[:, :, i] * (1 - mask) + color[i] * mask

    def draw_crosshair_float(self, img, center_x, center_y, size=20, color=[255, 255, 255]):
        """Draw a crosshair with anti-aliasing"""
        height, width = img.shape[:2]
        center_x, center_y = int(center_x), int(center_y)
        
        # Horizontal line
        if 0 <= center_y < height:
            start_x = max(0, center_x - size)
            end_x = min(width, center_x + size)
            img[center_y, start_x:end_x] = color
        
        # Vertical line
        if 0 <= center_x < width:
            start_y = max(0, center_y - size)
            end_y = min(height, center_y + size)
            img[start_y:end_y, center_x] = color

async def fetch_ice_servers():
    """Fetch ICE servers from the coturn service"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://ai.imjoy.io/public/services/coturn/get_rtc_ice_servers') as response:
                if response.status == 200:
                    ice_servers = await response.json()
                    print("Successfully fetched ICE servers:", ice_servers)
                    return ice_servers
                else:
                    print(f"Failed to fetch ICE servers, status: {response.status}")
                    return None
    except Exception as e:
        print(f"Error fetching ICE servers: {e}")
        return None

async def start_service(service_id, workspace=None, token=None):
    client_id = service_id + "-client"
    token = await login({"server_url": "https://hypha.aicell.io",})
    print(f"Starting service...")
    server = await connect_to_server(
        {
            "client_id": client_id,
            "server_url": "https://hypha.aicell.io",
            "workspace": workspace,
            "token": token,
        }
    )
    
    # Register the FastAPI web app service
    web_app_info = await server.register_service({
        "id": "webrtc-demo-app",
        "name": "WebRTC Demo App",
        "type": "asgi",
        "serve": serve_fastapi,
        "config": {"visibility": "public", "require_context": True}
    })
    
    print(f"Web app available at: https://hypha.aicell.io/{server.config.workspace}/apps/{web_app_info['id'].split(':')[1]}")
    
    async def on_init(peer_connection):
        print("WebRTC peer connection initialized on server side")
        
        @peer_connection.on("connectionstatechange")
        async def on_connectionstatechange():
            print(f"Connection state changed to: {peer_connection.connectionState}")
        
        @peer_connection.on("track")
        def on_track(track):
            print(f"Track {track.kind} received from client")
            video_track = VideoTransformTrack()
            
            # Add track - aiortc will handle the encoding parameters automatically
            peer_connection.addTrack(video_track)
            print(f"Added VideoTransformTrack to peer connection")
            
            @track.on("ended")
            async def on_ended():
                print(f"Client track {track.kind} ended")
                video_track.running = False

    # Fetch ICE servers
    ice_servers = await fetch_ice_servers()
    if not ice_servers:
        print("Using fallback ICE servers")
        ice_servers = [{"urls": ["stun:stun.l.google.com:19302"]}]

    await register_rtc_service(
        server,
        service_id=service_id,
        config={
            "visibility": "public",
            "ice_servers": ice_servers,
            "on_init": on_init,
        },
    )
    
    def move(value, axis, is_absolute=True, is_blocking=True, context=None):
        """Move the microscope position"""
        print(f"Move command: {value} on {axis} axis (absolute: {is_absolute})")
        
        # Store previous target to detect new commands
        prev_target_x = microscope_state["target_x"]
        prev_target_y = microscope_state["target_y"]
        
        if axis.upper() == 'X':
            if is_absolute:
                microscope_state["target_x"] = max(0, min(480, value))
            else:
                microscope_state["target_x"] = max(0, min(480, microscope_state["target_x"] + value))
        elif axis.upper() == 'Y':
            if is_absolute:
                microscope_state["target_y"] = max(0, min(360, value))
            else:
                microscope_state["target_y"] = max(0, min(360, microscope_state["target_y"] + value))
        
        # Check if target changed significantly to apply initial velocity boost
        target_changed_x = abs(microscope_state["target_x"] - prev_target_x) > 1
        target_changed_y = abs(microscope_state["target_y"] - prev_target_y) > 1
        
        if target_changed_x or target_changed_y:
            # Calculate direction to new target
            dx = microscope_state["target_x"] - microscope_state["x"]
            dy = microscope_state["target_y"] - microscope_state["y"]
            distance = np.sqrt(dx*dx + dy*dy)
            
            if distance > 0:
                # Apply initial velocity boost in direction of movement
                boost_strength = min(8.0, distance * 0.4)  # Scale boost with distance
                dir_x = dx / distance
                dir_y = dy / distance
                
                # Add velocity boost (this makes movement start quickly)
                microscope_state["velocity_x"] += dir_x * boost_strength
                microscope_state["velocity_y"] += dir_y * boost_strength
                
                # Limit the velocity to prevent overshooting
                vel_magnitude = np.sqrt(
                    microscope_state["velocity_x"]**2 + microscope_state["velocity_y"]**2
                )
                if vel_magnitude > microscope_state["max_velocity"]:
                    scale = microscope_state["max_velocity"] / vel_magnitude
                    microscope_state["velocity_x"] *= scale
                    microscope_state["velocity_y"] *= scale
        
        print(f"New target position: ({microscope_state['target_x']}, {microscope_state['target_y']})")
        print(f"Current velocity: ({microscope_state['velocity_x']:.2f}, {microscope_state['velocity_y']:.2f})")
        return {"x": microscope_state["target_x"], "y": microscope_state["target_y"]}
    
    def get_position(context=None):
        """Get current microscope position"""
        return {"x": microscope_state["x"], "y": microscope_state["y"]}
    
    def snap(context=None):
        print("snap an image")
        return {"status": "image captured", "position": {"x": microscope_state["x"], "y": microscope_state["y"]}}
        
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
            "get_position": get_position,
            "snap": snap
        }
    )
    
    print(
        f"Service (client_id={client_id}, service_id={service_id}) started successfully, available at https://hypha.aicell.io/{server.config.workspace}/services"
    )
    print(f"You can access the webrtc stream at https://oeway.github.io/webrtc-hypha-demo/?service_id={service_id}")
    print(f"Or use the integrated web app at: https://hypha.aicell.io/{server.config.workspace}/apps/{web_app_info['id'].split(':')[1]}")
    
    # Keep the server running
    await server.serve()

async def main():
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

    await start_service(
        args.service_id,
        workspace=None,
        token=None,
    )

if __name__ == "__main__":
    asyncio.run(main())

    
