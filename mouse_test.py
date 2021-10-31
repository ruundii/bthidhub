from mouse_message_filter import MouseMessageFilter
from mouse_g502_message_filter import G502MessageFilter
from mouse_mx510_message_filter import MX510MessageFilter

m = MouseMessageFilter()
g = G502MessageFilter()
mx = MX510MessageFilter()

#generic mouse test
#  Button: 0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0 | X:     -1 | Y:    -13 | Wheel:    0
print(m.filter_message_to_host(b'\x00\x00\xff\xff\xf3\xff\x00')==b'\xa1\x03\x00\x00\xff\xff\xf3\xff\x00')

#  Button: 0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0 | X:      1 | Y:      5 | Wheel:    0
print(m.filter_message_to_host(b'\x00\x00\x01\x00\x05\x00\x00')==b'\xa1\x03\x00\x00\x01\x00\x05\x00\x00')

#  Button: 0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0 | X:      0 | Y:      0 | Wheel:    1
print(m.filter_message_to_host(b'\x00\x00\x00\x00\x00\x00\x01')==b'\xa1\x03\x00\x00\x00\x00\x00\x00\x01')

#  Button: 0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0 | X:      0 | Y:      0 | Wheel:   -1
print(m.filter_message_to_host(b'\x00\x00\x00\x00\x00\x00\xff')==b'\xa1\x03\x00\x00\x00\x00\x00\x00\xff')

#  Button: 1  0  1  0  0  0  0  0  0  0  0  0  0  0  0  0 | X:      0 | Y:      0 | Wheel:    0
print(m.filter_message_to_host(b'\x05\x00\x00\x00\x00\x00\x00')==b'\xa1\x03\x05\x00\x00\x00\x00\x00\x00')


#G502  mouse test
#  Button: 0  0  0  0  0  0  0  0  0  0  0  0  0  0  0  0 | X:     -1 | Y:    -13 | Wheel:    0 | AC Pan:    0
print(g.filter_message_to_host(b'\x00\x00\xff\xff\xf3\xff\x00\x00')==b'\xa1\x03\x00\x00\xff\xff\xf3\xff\x00')

#MX510 mouse test
from bitarray import bitarray
from bitarray.util import ba2int

#  Button: 0  0  0  0  0  0  0  0 | # | 0xff000040:   23 ,   12 | Wheel:    0 | X:    23 | Y:    12
#00 17 0c 00 17 c0 00
print(mx.filter_message_to_host(b'\x00\x17\x0c\x00\x17\xc0\x00')==b'\xa1\x03\x00\x00\x17\x00\x0c\x00\x00')


#  Button: 0  0  0  0  0  0  0  0 | # | 0xff000040:   15 ,  -42 | Wheel:    0 | X:    15 | Y:   -42
#00 0f d6 00 0f 60 fd
print(mx.filter_message_to_host(b'\x00\x0f\xd6\x00\x0f\x60\xfd')==b'\xa1\x03\x00\x00\x0f\x00\xd6\xff\x00')


#  Button: 0  0  0  0  0  0  0  0 | # | 0xff000040:   -7 ,   18 | Wheel:    0 | X:    -7 | Y:    18
#00 f9 12 00 f9 2f 01
print(mx.filter_message_to_host(b'\x00\xf9\x12\x00\xf9\x2f\x01')==b'\xa1\x03\x00\x00\xf9\xff\x12\x00\x00')

#  Button: 1  1  0  0  0  0  0  0 | # | 0xff000040:    0 ,    0 | Wheel:    0 | X:     0 | Y:     0
#03 00 00 00 00 00 00
print(mx.filter_message_to_host(b'\x03\x00\x00\x00\x00\x00\x00')==b'\xa1\x03\x03\x00\x00\x00\x00\x00\x00')

#  Button: 0  0  0  0  0  0  0  0 | # | 0xff000040:    0 ,    0 | Wheel:   -1 | X:     0 | Y:     0
#00 00 00 ff 00 00 00
print(mx.filter_message_to_host(b'\x00\x00\x00\xff\x00\x00\x00')==b'\xa1\x03\x00\x00\x00\x00\x00\x00\xff')
