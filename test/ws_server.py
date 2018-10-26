#!/usr/bin/env python

# WS server example

import asyncio
import websockets

async def hello(websocket, path):
    while True:
        d = await websocket.recv()
        print(d)
        #await websocket.send(d)


start_server = websockets.serve(hello, 'localhost', 1234)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
