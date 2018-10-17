import uasyncio as asyncio
from uasyncio.websocket.server import WSReader, WSWriter
import uos as os
import machine

def res():
    machine.reset()

async def websocket_handler(reader,writer):
    # Consume GET line
    yield from reader.readline()

    reader = yield from WSReader(reader, writer)
    writer = WSWriter(reader, writer)

    while True:
        l = yield from reader.read(256)
        print(l)
        if l == b"\r":
            await writer.awrite(b"\r\n")
        else:
            await writer.awrite(l.upper())


async def http_handler(reader,writer):
    DIR_PREFIX = "www/"
    RESPONSE_NOT_FOUND = b"HTTP/1.0 404 Not Found\r\n"
    RESPONSE_OK = b"HTTP/1.0 200 OK\r\n"
    MIMETYPES = {
        "gif": "image/gif",
        "htm": "text/html",
        "jpg": "image/jpeg",
        "png": "image/png",
        "txt": "text/plain"
    }
    req = await reader.read(512)
    cl_ip = writer.get_extra_info('peername')
    try:
        req_file=str(req).split(" ")[1]
        if req_file == "/":
            req_file = "index.htm"
        else:
            req_file = req_file.split("/")[1]
        req_file = DIR_PREFIX + req_file
        req_filetype=req_file.split(".")[1]
        f = open(req_file,"rb")
        filesize = os.stat(req_file)[6]
        print("Client: "+str(cl_ip)+" File: " + req_file + " Filetype: "+req_filetype + " Filesize: "+str(filesize))
        await writer.awrite(RESPONSE_OK)
        await writer.awrite("Content-Type: "+MIMETYPES[req_filetype]+"\r\n")
        await writer.awrite("Content-Length: "+str(filesize)+"\r\n\r\n")
        chunk = f.read(256)
        while chunk:
            await writer.awrite(chunk)
            chunk = f.read(256)
        f.close()
    except:
        await writer.awrite(RESPONSE_NOT_FOUND)

    await writer.aclose()



loop = asyncio.get_event_loop()
loop.create_task(asyncio.start_server(http_handler, "0.0.0.0", 80))
loop.create_task(asyncio.start_server(websocket_handler, "0.0.0.0", 8081))
loop.run_forever()
loop.close()
