# This file is executed on every boot (including wake-boot from deepsleep)
#import esp
#esp.osdebug(None)
import gc
import machine
import network
import esp
#import webrepl
#webrepl.start()
gc.collect()
network.phy_mode(network.MODE_11B)
machine.freq(160000000)
machine.Pin(16,machine.Pin.OUT).value(0)
ap_if=network.WLAN(network.AP_IF)
ap_if.ifconfig(('192.168.4.1','255.255.255.0','192.168.4.1','192.168.4.1'))
esp.osdebug(0)
