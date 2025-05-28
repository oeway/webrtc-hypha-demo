# WebRTC Hypha Demo

An interactive WebRTC microscope simulation with real-time streaming and control capabilities, built with Hypha RPC and modern web technologies.

![WebRTC Demo](https://img.shields.io/badge/WebRTC-Interactive-blue) ![Hypha](https://img.shields.io/badge/Hypha-RPC-green) ![Tailwind](https://img.shields.io/badge/Tailwind-CSS-blue)

## ✨ Features

### 🔬 **Interactive Microscope Simulation**
- **Realistic Microscope View**: Simulated optical microscope with vignette effects and measurement grid
- **Live Specimens**: Multiple colored objects with floating motion and pulsing effects
- **Smooth Navigation**: Real-time position tracking with smooth interpolation
- **Visual Feedback**: Position indicators, crosshairs, and coordinate displays

### 🎮 **Intuitive Controls**
- **Floating Controls**: Hover over video to reveal directional navigation buttons
- **Real-time Movement**: Click arrows to move microscope view in real-time
- **Position Tracking**: Live X/Y coordinate display with color coding
- **Image Capture**: Snap function with visual confirmation

### 🎨 **Modern UI Design**
- **Professional Interface**: Clean, card-based layout with Tailwind CSS
- **Responsive Design**: Works seamlessly on desktop and mobile devices
- **Glass Morphism**: Modern visual effects with backdrop blur and transparency
- **Interactive Animations**: Smooth hover effects and transitions

### 🔐 **Secure Authentication**
- **Hypha Integration**: Secure login/logout with Hypha authentication
- **Session Management**: Automatic connection state handling
- **User Context**: Per-user service isolation and permissions

## 🚀 Quick Start

### Prerequisites
```bash
pip install -r requirements.txt
```

### Running the Server

**Option 1: Async Version (Recommended)**
```bash
python server.py --service-id your-service-id
```

**Option 2: Sync Version**
```bash
python server_sync.py --service-id your-service-id
```

### Accessing the Application

The server provides multiple access points:

1. **Integrated Web App** (Recommended):
   ```
   https://hypha.aicell.io/{workspace}/apps/webrtc-demo-app
   ```

2. **External Web App**:
   ```
   https://oeway.github.io/webrtc-hypha-demo/?service_id=your-service-id
   ```

3. **Local Development**:
   ```
   http://localhost:8000 (when running locally)
   ```

## 🎯 How to Use

### 1. **Login**
- Click the "Login" button in the sidebar
- Complete Hypha authentication in the popup window
- Status indicator will show "Logged in" when successful

### 2. **Start Streaming**
- Click "Start Stream" to begin video transmission
- The microscope view will appear with live specimens
- Stream status indicator shows "Live" when active

### 3. **Navigate the Microscope**
- **Hover** over the video area to reveal floating controls
- **Click** directional arrows to move the microscope view
- **Watch** objects move in real-time as you navigate
- **Monitor** position coordinates in the top-right overlay

### 4. **Capture Images**
- Click the "Snap Image" button to capture the current view
- Visual confirmation shows successful capture
- Position information is included with each capture

## 🛠️ Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `--service-id` | Custom service identifier | `"aiortc-demo"` |
| `--verbose` / `-v` | Enable debug logging | `False` |

## 🏗️ Architecture

### Server Components
- **`server.py`**: Async WebRTC service with FastAPI integration
- **`server_sync.py`**: Synchronous version for compatibility
- **`index.html`**: Modern web interface with Tailwind CSS

### Key Technologies
- **WebRTC**: Real-time video streaming with aiortc
- **Hypha RPC**: Service registration and authentication
- **FastAPI**: Web application framework
- **Tailwind CSS**: Modern utility-first styling
- **NumPy**: Video frame generation and processing

### Microscope Simulation
```python
# Global state tracking
microscope_state = {
    "x": 240, "y": 180,           # Current position
    "target_x": 240, "target_y": 180,  # Target position
    "objects": [...]               # Specimen objects
}
```

## 🎨 UI Components

### Sidebar Controls
- **Configuration**: Service ID input
- **Authentication**: Login/logout with status
- **Stream Control**: Start/stop streaming
- **Image Capture**: Snap functionality
- **Instructions**: User guidance

### Video Interface
- **Live Stream**: 480x360 microscope view at 30 FPS
- **Floating Controls**: Hover-activated directional buttons
- **Status Overlays**: Stream status and position indicators
- **Visual Effects**: Glass morphism and smooth animations

## 🔧 Development

### File Structure
```
webrtc-hypha-demo/
├── server.py              # Main async server
├── server_sync.py          # Sync server version
├── index.html             # Web interface
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

### Key Functions

**Movement Control**:
```python
def move(value, axis, is_absolute=True, is_blocking=True):
    """Move microscope to specified position"""
    
def get_position():
    """Get current microscope coordinates"""
```

**Video Generation**:
```python
class VideoTransformTrack:
    """Generates realistic microscope view with interactive objects"""
```

### Customization

**Adding New Specimens**:
```python
microscope_state["objects"].append({
    "x": 200, "y": 150,
    "color": [255, 200, 100],
    "size": 25
})
```

**Adjusting Movement Speed**:
```python
# In moveRelative function
deltaX = 25  # Smaller values = finer control
deltaY = 25
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with both server versions
5. Submit a pull request

## 📝 License

This project is open source and available under the MIT License.

## 🆘 Support

For issues and questions:
- Check the Hypha documentation
- Review WebRTC troubleshooting guides
- Open an issue in the repository

---

**Built with ❤️ using Hypha, WebRTC, and modern web technologies**

