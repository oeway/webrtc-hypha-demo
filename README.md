# WebRTC demo for Hypha


This is a demo repo for showing how to use Hypha as a singaling server, and stream video to the browser.


## Installation
```
pip install aiortc numpy imjoy-rpc
```

## Start

Start the server:
```
python server.py --service-id=my-video-stream
```

Then visit the URL printed in the console, e.g. https://oeway.github.io/webrtc-hypha-demo/?service_id=my-video-stream .

