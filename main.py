import uasyncio as asyncio
from uasyncio.websocket.server import WSReader, WSWriter
import uos as os
import machine
import socket

#define IOs
io_lights = 5
io_motor1_n = 0
io_motor1_p = 4
io_motor2_n = 2
io_motor2_p = 15
io_motors_enable = 16
io_servo_steering = 12
io_servo_leveler1 = 13
io_servo_leveler2 = 14

def init_ios():
    machine.Pin(io_motors_enable,machine.Pin.OUT).value(0)
    machine.Pin(io_motor1_n,machine.Pin.OUT).value(0)
    machine.Pin(io_motor1_p,machine.Pin.OUT).value(0)
    machine.Pin(io_motor2_n,machine.Pin.OUT).value(0)
    machine.Pin(io_motor2_p,machine.Pin.OUT).value(0)


def set_lights(value):
    if value == 100:
        machine.Pin(io_lights,machine.Pin.OUT).value(1)
    else:
        machine.Pin(io_lights,machine.Pin.OUT).value(0)

def set_steering(value):
    steering_max = 106
    steering_min = 50
    servo_pos = int(float(steering_max-steering_min)/200.0*float(value+100)+steering_min)
    machine.PWM(machine.Pin(io_servo_steering), freq=50).duty(servo_pos)

def set_motor(value):
    min_duty = 120
    machine.Pin(io_motors_enable,machine.Pin.OUT).value(0)
    if value != 0:
        duty_value = int(abs(value) * 1023 / 100)
        if duty_value < min_duty:
            duty_value = min_duty
        if value < 0:
            machine.Pin(io_motor1_n,machine.Pin.OUT).value(0)
            machine.Pin(io_motor2_n,machine.Pin.OUT).value(0)
            machine.PWM(machine.Pin(io_motor1_p), freq=50).duty(duty_value)
            machine.PWM(machine.Pin(io_motor2_p), freq=50).duty(duty_value)
        else:
            machine.Pin(io_motor1_p,machine.Pin.OUT).value(0)
            machine.Pin(io_motor2_p,machine.Pin.OUT).value(0)
            machine.PWM(machine.Pin(io_motor1_n), freq=50).duty(duty_value)
            machine.PWM(machine.Pin(io_motor2_n), freq=50).duty(duty_value)
        machine.Pin(io_motors_enable,machine.Pin.OUT).value(1)

def set_leveler(value):
    servo1_min = 102
    servo2_min = 40
    servo1_max = 40
    servo2_max = 108

    servo1_pos = int(float(servo1_max-servo1_min)/200.0*float(value+100)+servo1_min)
    servo2_pos = int(float(servo2_max-servo2_min)/200.0*float(value+100)+servo2_min)
    machine.PWM(machine.Pin(io_servo_leveler1), freq=50).duty(servo1_pos)
    machine.PWM(machine.Pin(io_servo_leveler2), freq=50).duty(servo2_pos)



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

    while True:
        l = await reader.readline()
        try:
            l = l.rstrip()
            l = str(l).split("\'")[1]
            rc_cmd = l.split(" ")[0]
            rc_value = int(l.split(" ")[1])
            if rc_cmd == "lights":
                set_lights(rc_value)
            if rc_cmd == "steering":
                set_steering(rc_value)
            if rc_cmd == "motor":
                set_motor(rc_value)
            if rc_cmd == "leveler":
                set_leveler(rc_value)

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
        writer.awrite(RESPONSE_NOT_FOUND)

    await writer.aclose()



init_ios()
loop = asyncio.get_event_loop()
loop.create_task(dns_server())
loop.create_task(asyncio.start_server(http_handler, "0.0.0.0", 80,backlog = 1))
loop.create_task(asyncio.start_server(websocket_echo_handler, "0.0.0.0", 8081))
loop.create_task(asyncio.start_server(websocket_rc_receiver_handler, "0.0.0.0", 8082))
loop.run_forever()
loop.close()
