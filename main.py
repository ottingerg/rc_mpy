import uasyncio as asyncio
from uasyncio.websocket.server import WSReader, WSWriter
import uos as os
import machine
import socket
import utime


buf = bytearray(512)
buf2 = bytearray(32)
buf3 = bytearray(32)

pin_lights = machine.Pin(5, machine.Pin.OUT)


while ap_if.isconnected() == False:
    pin_lights.value(1)
    utime.sleep(1)
    pin_lights.value(0)
    print(gc.mem_free())
    utime.sleep(1)


#define IOs

pin_motor1_n = machine.Pin(0)
pin_motor1_p = machine.Pin(4)
pin_motor2_n = machine.Pin(2)
pin_motor2_p = machine.Pin(15)
pin_motors_enable = machine.Pin(16, machine.Pin.OUT)
pin_servo_steering = machine.Pin(12)
pin_servo_leveler1 = machine.Pin(13)
pin_servo_leveler2 = machine.Pin(14)

pwm_motor1_n = machine.PWM(pin_motor1_n, freq=50)
pwm_motor1_p = machine.PWM(pin_motor1_p)
pwm_motor2_n = machine.PWM(pin_motor2_n)
pwm_motor2_p = machine.PWM(pin_motor2_p)

pwm_servo_steering = machine.PWM(pin_servo_steering)
pwm_servo_leveler1 = machine.PWM(pin_servo_leveler1)
pwm_servo_leveler2 = machine.PWM(pin_servo_leveler2)


def init_ios():
    pin_motors_enable.value(0)


def set_lights(value):
    if value == 100:
        pin_lights.value(1)
    else:
        pin_lights.value(0)

def set_steering(value):
    steering_max = const(106)
    steering_min = const(50)
    servo_pos = int(float(steering_max-steering_min)/200.0*float(value+100)+steering_min)
    pwm_servo_steering.duty(servo_pos)

def set_motor(value):
    min_duty = const(120)
    pin_motors_enable.value(0)
    if value != 0:
        duty_value = int(abs(value) * 1023 / 100)
        if duty_value < min_duty:
            duty_value = min_duty
        if value < 0:
            pwm_motor1_n.duty(0)
            pwm_motor2_n.duty(0)
            pwm_motor1_p.duty(duty_value)
            pwm_motor2_p.duty(duty_value)
        else:
            pwm_motor1_n.duty(duty_value)
            pwm_motor2_n.duty(duty_value)
            pwm_motor1_p.duty(0)
            pwm_motor2_p.duty(0)
        pin_motors_enable.value(1)

def set_leveler(value):
    servo1_min = const(102)
    servo2_min = const(40)
    servo1_max = const(40)
    servo2_max = const(108)

    servo1_pos = int(float(servo1_max-servo1_min)/200.0*float(value+100)+servo1_min)
    servo2_pos = int(float(servo2_max-servo2_min)/200.0*float(value+100)+servo2_min)
    pwm_servo_leveler1.duty(servo1_pos)
    pwm_servo_leveler2.duty(servo2_pos)

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
        buf2 = await reader.readline()
        try:
            buf3 = buf2.rstrip()
            buf2 = str(buf3).split("\'")[1]
            rc_cmd = buf2.split(" ")[0]
            rc_value = int(buf2.split(" ")[1])
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
    while True:
        await asyncio.sleep(1)
        m = gc.mem_free()
        print(m)

init_ios()
loop = asyncio.get_event_loop()
loop.create_task(show_free_mem())
loop.create_task(dns_server())
loop.create_task(asyncio.start_server(http_handler, "0.0.0.0", 80,backlog = 1))
loop.create_task(asyncio.start_server(websocket_echo_handler, "0.0.0.0", 8081))
loop.create_task(asyncio.start_server(websocket_rc_receiver_handler, "0.0.0.0", 8082))
loop.run_forever()
loop.close()
