import uasyncio as asyncio
from uasyncio.websocket.server import WSReader, WSWriter
import uos as os
import machine
import socket
import utime
from gpio import GPIO


io = GPIO()
g_mem_free = 0
buf = bytearray(512)
buf2 = bytearray(32)
buf3 = bytearray(32)


async def dns_server():
    def getPacketAnswerA(packet, ipV4Bytes) :
        try :
            queryEndPos = 12
            while True :
                domPartLen = packet[queryEndPos]
                if (domPartLen == 0) :
                    break
                queryEndPos += 1 + domPartLen
            queryEndPos += 5

            return b''.join( [
                packet[:2],             # Query identifier
                b'\x85\x80',            # Flags and codes
                packet[4:6],            # Query question count
                b'\x00\x01',            # Answer record count
                b'\x00\x00',            # Authority record count
                b'\x00\x00',            # Additional record count
                packet[12:queryEndPos], # Query question
                b'\xc0\x0c',            # Answer name as pointer
                b'\x00\x01',            # Answer type A
                b'\x00\x01',            # Answer class IN
                b'\x00\x00\x00\x1E',    # Answer TTL 30 secondes
                b'\x00\x04',            # Answer data length
                ipV4Bytes ] )           # Answer data

        except :
            pass

        return None

    s = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    s.bind(('192.168.4.1',53))
    s.setblocking(False)

    while True:

        await asyncio.sleep(1)
        try:
            packet, clientIP = s.recvfrom(256)
            packet = getPacketAnswerA (packet, b'\xC0\xA8\x04\x01') # 192.168.4.1
            s.sendto(packet, clientIP)
        except :
            pass

async def websocket_echo_handler(reader,writer):
    # Consume GET line
    await reader.readline()

    reader = await WSReader(reader, writer)
    writer = WSWriter(reader, writer)

    while True:

        l = await reader.read(256)
        print(l)
        if l == b"\r":
            await writer.awrite(b"\r\n")
        else:
            await writer.awrite(l.upper())

async def websocket_rc_receiver_handler(reader,writer):
    # Consume GET line
    await reader.readline()

    reader = await WSReader(reader, writer)
    writer = WSWriter(reader, writer)

    websocket_working = True

    while websocket_working:

        try:
            buf2 = await reader.readline()
        except:
            websocket_working = False
            print("closing websocket!")
        try:
            buf3 = buf2.rstrip()
            buf2 = str(buf3).split("\'")[1]
            rc_cmd = buf2.split(" ")[0]
            rc_value = int(buf2.split(" ")[1])
            if rc_cmd == "lights":
                io.set_lights(rc_value)
            if rc_cmd == "steering":
                io.set_steering(rc_value)
            if rc_cmd == "motor":            
                io.set_motor(rc_value)
            if rc_cmd == "leveler":
                io.set_leveler(rc_value)
            try:
                await writer.awrite(str(g_mem_free))
            except:
                websocket_working = False
                print("closing websocket!")
        except:
            pass

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
    buf = await reader.read(512)
    cl_ip = writer.get_extra_info('peername')
    try:
        req_file=str(buf).split(" ")[1]
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
        buf = f.read(256)
        while buf:
            await writer.awrite(buf)
            buf = f.read(256)
        f.close()
    except:
        writer.awrite(RESPONSE_NOT_FOUND)

    await writer.aclose()

async def show_free_mem():
    global g_mem_free

    while True:
        await asyncio.sleep(1)
        g_mem_free = gc.mem_free()
        print(g_mem_free)

print("---- EBRO 160D @ WORK ----")
print(machine.reset_cause())

while ap_if.isconnected() == False:
    io.set_lights(100)
    utime.sleep(1)
    io.set_lights(0)
    print(gc.mem_free())
    utime.sleep(1)



loop = asyncio.get_event_loop()
loop.create_task(show_free_mem())
loop.create_task(dns_server())
loop.create_task(asyncio.start_server(http_handler, "0.0.0.0", 80,backlog = 1))
loop.create_task(asyncio.start_server(websocket_echo_handler, "0.0.0.0", 8081))
loop.create_task(asyncio.start_server(websocket_rc_receiver_handler, "0.0.0.0", 8082))
loop.run_forever()
loop.close()
