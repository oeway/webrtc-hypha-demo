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

Now start a dev server for serving the webpage:
```
python -m http.server 9000
```


Then visit http://localhost:9000/index.html to start streaming, before you connect, please fill in the correct service id of your server (in this example, it should be `my-video-stream`).


