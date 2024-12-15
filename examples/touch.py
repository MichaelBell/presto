from machine import Pin, I2C
import math

class FT6236:
    TOUCH_INT = const(32)
    TOUCH_I2C = const(1)
    TOUCH_SDA = const(30)
    TOUCH_SCL = const(31)
    TOUCH_ADDR = const(0x48)
    
    STATE_DOWN = const(0b00)
    STATE_UP = const(0b01)
    STATE_CONTACT = const(0b10)
    STATE_NONE = const(0b11)

    def __init__(self, enable_interrupt=False):
        self.debug = False
        self.irq = enable_interrupt

        self.x = 120
        self.y = 120
        self.state = False

        self.x2 = 120
        self.y2 = 120
        self.state2 = False

        self.distance = 0
        self.angle = 0
        
        self.gesture = 0
        
        self.buf = bytearray(15)
        self.data = memoryview(self.buf)

        self.i2c = I2C(self.TOUCH_I2C, sda=Pin(self.TOUCH_SDA), scl=Pin(self.TOUCH_SCL), freq=1000000)
        self.touch_int = Pin(self.TOUCH_INT, Pin.IN, Pin.PULL_UP)
        
        if self.irq:
            self.touch_int.irq(self.handle_touch, trigger=Pin.IRQ_FALLING)
        
    def poll(self):
        if self.irq:
            return None

        if not self.touch_int.value() or self.state or self.state2:
            self.handle_touch(self.touch_int)
            
    def read_touch(self, data):
        e = data[0] >> 6
        x = ((data[0] & 0x0f) << 8) | data[1]
        y = ((data[2] & 0x0f) << 8) | data[3]
        w = data[4]
        return int(x / 2), int(y / 2), e not in (self.STATE_NONE, self.STATE_UP)

    def handle_touch(self, pin):
        self.state = self.state2 = False

        self.i2c.writeto(self.TOUCH_ADDR, b'\x00', False)
        self.i2c.readfrom_into(self.TOUCH_ADDR, self.buf)

        mode, gesture, touches = self.data[:3]
        touches &= 0x0f
        
        if self.debug:
            print(mode, gesture, touches)

        for n in range(touches):
            data = self.data[3  + n * 6:]
            touch_id = data[2] >> 4
            if touch_id == 0:
                self.x, self.y, self.state = self.read_touch(data)
            else:
                self.x2, self.y2, self.state2 = self.read_touch(data)

        if self.state and self.state2:
            self.distance = math.sqrt(abs(self.x2 - self.x)**2 + abs(self.y2 - self.y)**2)
            self.angle = math.degrees(math.atan2(self.y2 - self.y, self.x2 - self.x)) + 180

        if self.debug:
            print(self.x, self.y, self.x2, self.y2, self.distance, self.angle, self.state, self.state2)
        

#touch = FT6236()
