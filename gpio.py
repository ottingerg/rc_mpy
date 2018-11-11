import machine
import utime

class GPIO():

    def __init__(self):
        self.pin_lights = machine.Pin(5, machine.Pin.OUT)

        self.pin_motor1_n = machine.Pin(0)
        self.pin_motor1_p = machine.Pin(4)
        self.pin_motor2_n = machine.Pin(2)
        self.pin_motor2_p = machine.Pin(15)
        self.pin_motors_enable = machine.Pin(16, machine.Pin.OUT)
        self.pin_servo_steering = machine.Pin(12)
        self.pin_servo_leveler1 = machine.Pin(13)
        self.pin_servo_leveler2 = machine.Pin(14)

        self.pwm_motor1_n = machine.PWM(self.pin_motor1_n, freq=50)
        self.pwm_motor1_p = machine.PWM(self.pin_motor1_p)
        self.pwm_motor2_n = machine.PWM(self.pin_motor2_n)
        self.pwm_motor2_p = machine.PWM(self.pin_motor2_p)

        self.pwm_servo_steering = machine.PWM(self.pin_servo_steering)
        self.pwm_servo_leveler1 = machine.PWM(self.pin_servo_leveler1)
        self.pwm_servo_leveler2 = machine.PWM(self.pin_servo_leveler2)
        self.pin_motors_enable.value(0)

        self.old_motor_value = 0

    def set_lights(self,value):
        if value == 100:
            self.pin_lights.value(1)
        else:
            self.pin_lights.value(0)

    def set_steering(self,value):
        steering_max = const(106)
        steering_min = const(50)
        servo_pos = int(float(steering_max-steering_min)/200.0*float(value+100)+steering_min)
        self.pwm_servo_steering.duty(servo_pos)

    def set_motor(self,value):
        min_duty = const(120)

        def sign(x):
            if x > 0:
                return 1.
            elif x < 0:
                return -1.
            elif x == 0:
                return 0.
            else:
                return x

        if sign(value) != sign(self.old_motor_value):
            self.pin_motors_enable.value(0)
            utime.sleep_ms(100)

        self.old_motor_value = value
        if value != 0:
            duty_value = int(abs(value) * 1023 / 100)
            if duty_value < min_duty:
                duty_value = min_duty

            if value < 0:
                self.pwm_motor1_n.duty(0)
                self.pwm_motor2_n.duty(0)
                self.pwm_motor1_p.duty(duty_value)
                self.pwm_motor2_p.duty(duty_value)
            else:
                self.pwm_motor1_n.duty(duty_value)
                self.pwm_motor2_n.duty(duty_value)
                self.pwm_motor1_p.duty(0)
                self.pwm_motor2_p.duty(0)
            self.pin_motors_enable.value(1)
        else:
            self.pwm_motor1_n.duty(0)
            self.pwm_motor2_n.duty(0)
            self.pwm_motor1_p.duty(0)
            self.pwm_motor2_p.duty(0)
            self.pin_motors_enable.value(0)


    def set_leveler(self,value):
        servo1_min = const(120)
        servo2_min = const(47)
        servo1_max = const(47)
        servo2_max = const(120)

        servo1_pos = int(float(servo1_max-servo1_min)/200.0*float(value+100)+servo1_min)
        servo2_pos = int(float(servo2_max-servo2_min)/200.0*float(value+100)+servo2_min)
        self.pwm_servo_leveler1.duty(servo1_pos)
        self.pwm_servo_leveler2.duty(servo2_pos)
