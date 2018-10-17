import uasyncio as asyncio
from uasyncio.websocket.server import WSReader, WSWriter
import uos as os
import machine

PWM_CHANNELS = {
    machine.PWM(machine.Pin(5), freq=50),
    machine.PWM(machine.Pin(12), freq=50),
    machine.PWM(machine.Pin(13), freq=50),
    machine.PWM(machine.Pin(14), freq=50),
    machine.PWM(machine.Pin(15), freq=50),
}

def res():
    machine.reset()

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
    s.bind(('127.0.0.1',53))
    s.setblocking(False)

    while True:
        try:
            await asyncio.sleep(1)
            packet, clientIP = s.recvfrom(256)
            packet = getPacketAnswerA (packet, b'\x01\x02\x03\x04')
            s.sendto(packet, clientIP)
        except socket.error:
            pass

async def websocket_echo_handler(reader,writer):
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

async def websocket_rc_receiver_handler(reader,writer):
    # Consume GET line
    yield from reader.readline()

    reader = yield from WSReader(reader, writer)

    while True:
        l = yield from reader.readline()
        try:
            channel = int(l.split(",")[0])
            motor_type = int(l.split(",")[1])
            value = float(l.split(",")[2])

            if motor_type == "servo":
                #convert angle to pwm
                value = value / 180 * 75 + 40
            else:
                #convert percent to pwm
                value = value / 100 * 1023

            PWM_CHANNELS[channel].duty(value)

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
loop.create_task(dns_server())
loop.create_task(asyncio.start_server(http_handler, "0.0.0.0", 80))
loop.create_task(asyncio.start_server(websocket_echo_handler, "0.0.0.0", 8081))
loop.create_task(asyncio.start_server(websocket_rc_receiver_handler, "0.0.0.0", 8082))
loop.run_forever()
loop.close()
