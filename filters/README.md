# Writing custom filters

There are cases when a device doesn't work correctly when proxying the events through.
Here we'll take a look at how to debug and fix these issues, along with a real example for the Contour Rollermouse Red.
The Contour Rollermouse Red has a double-click button, but when proxied through bthidhub this doesn't work.

## Debugging

First thing is to find out why the events don't work (this is assuming that they work correctly when connected directly).
If you first connect the device directly to your machine, then run ``sudo hid-recorder``, you can see what events the device sends.

Here's the output after using the double-click button on the Rollermouse:
```
R: 220 05 01 09 02 a1 01 09 01 a1 01 85 01 05 09 19 01 29 08 15 00 25 01 75 01 95 08 81 02
05 01 09 30 09 31 16 08 80 26 ff 7f 75 10 95 02 81 06 09 38 15 81 25 7f 75 08 95 01 81 06
05 0c 0a 00 ff 81 06 06 00 ff 09 01 75 08 95 08 81 02 c0 c0 05 01 09 06 a1 01 85 02 05 07
19 e0 29 e7 15 00 25 01 75 01 95 08 81 02 06 00 ff 09 02 75 08 95 01 81 02 05 07 19 00 29
7f 15 00 25 7f 75 08 95 05 81 00 c0 05 0c 09 01 a1 01 85 03 05 09 19 09 29 18 15 00 25 01
75 01 95 10 81 02 05 0c 19 00 2a ff 03 15 00 26 ff 03 95 01 75 10 81 00 05 01 1a 81 00 2a
83 00 15 00 25 01 75 01 95 03 81 02 95 05 81 01 06 00 ff 09 02 75 08 95 0a 81 02 85 04 06
00 ff 0a 00 ff 75 08 95 0f b1 02 c0
N: Contour Design Contour RollerMouse Red
I: 3 0b33 1004
# ReportID: 1 / Button: 0 0 0 0 0 0 0 0 | X: 0 | Y: 0 | Wheel: 0 | 0xcff00: 0 | Vendor Usage 1: 1 , -128 , 0 , 0 , 0 , 0 , 0 , 0
E: 000000.000000 16 01 00 00 00 00 00 00 00 01 80 00 00 00 00 00 00
# ReportID: 1 / Button: 1 0 0 0 0 0 0 0 | X: 0 | Y: 0 | Wheel: 0 | 0xcff00: 0 | Vendor Usage 1: 1 , -128 , 0 , 0 , 0 , 0 , 0 , 0
E: 000000.003905 16 01 01 00 00 00 00 00 00 01 80 00 00 00 00 00 00
# ReportID: 1 / Button: 0 0 0 0 0 0 0 0 | X: 0 | Y: 0 | Wheel: 0 | 0xcff00: 0 | Vendor Usage 1: 1 , -128 , 0 , 0 , 0 , 0 , 0 , 0
E: 000000.007800 16 01 00 00 00 00 00 00 00 01 80 00 00 00 00 00 00
# ReportID: 1 / Button: 1 0 0 0 0 0 0 0 | X: 0 | Y: 0 | Wheel: 0 | 0xcff00: 0 | Vendor Usage 1: 1 , -128 , 0 , 0 , 0 , 0 , 0 , 0
E: 000000.011843 16 01 01 00 00 00 00 00 00 01 80 00 00 00 00 00 00
# ReportID: 1 / Button: 0 0 0 0 0 0 0 0 | X: 0 | Y: 0 | Wheel: 0 | 0xcff00: 0 | Vendor Usage 1: 1 , -128 , 0 , 0 , 0 , 0 , 0 , 0
E: 000000.015822 16 01 00 00 00 00 00 00 00 01 80 00 00 00 00 00 00
# ReportID: 1 / Button: 0 0 0 0 0 0 0 0 | X: 0 | Y: 0 | Wheel: 0 | 0xcff00: 0 | Vendor Usage 1: 1 , 0 , 0 , 0 , 0 , 0 , 0 , 0
E: 000000.171955 16 01 00 00 00 00 00 00 00 01 00 00 00 00 00 00 00
```

Then if we reconnect the device to the RPi, we can run ``sudo hid-recorder`` again and this time see what is sent by the RPi.
Here's the output from the RPi for the same double-click button:
```
R: 553 05 01 09 06 a1 01 85 01 05 07 19 e0 29 e7 15 00 25 01 75 01 95 08 81 02 95 01 75 08
81 03 95 05 75 01 05 08 19 01 29 05 91 02 95 01 75 03 91 03 95 06 75 08 15 00 25 6d 05 07
19 00 29 6d 81 00 c0 05 0c 09 01 a1 01 85 02 05 0c 15 00 25 01 75 01 95 07 09 b5 09 b6 09
b7 09 cd 09 e2 09 e9 09 ea 81 02 95 01 81 01 c0 05 01 09 02 a1 01 09 01 a1 00 85 03 05 09
19 01 29 07 15 00 25 01 95 08 75 01 81 02 06 00 ff 09 40 95 02 75 08 15 81 25 7f 81 02 05
01 09 38 15 81 25 7f 75 08 95 01 81 06 09 30 09 31 16 00 80 26 ff 7f 75 10 95 02 81 06 c0
05 ff 09 02 15 00 25 ff 75 08 95 5a b1 01 c0 05 01 09 02 a1 01 09 01 a1 01 85 04 05 09 19
01 29 08 15 00 25 01 75 01 95 08 81 02 05 01 09 30 09 31 16 08 80 26 ff 7f 75 10 95 02 81
06 09 38 15 81 25 7f 75 08 95 01 81 06 05 0c 0a 00 ff 81 06 06 00 ff 09 01 75 08 95 08 81
02 c0 c0 05 01 09 06 a1 01 85 05 05 07 19 e0 29 e7 15 00 25 01 75 01 95 08 81 02 06 00 ff
09 02 75 08 95 01 81 02 05 07 19 00 29 7f 15 00 25 7f 75 08 95 05 81 00 c0 05 0c 09 01 a1
01 85 06 05 09 19 09 29 18 15 00 25 01 75 01 95 10 81 02 05 0c 19 00 2a ff 03 15 00 26 ff
03 95 01 75 10 81 00 05 01 1a 81 00 2a 83 00 15 00 25 01 75 01 95 03 81 02 95 05 81 01 06
00 ff 09 02 75 08 95 0a 81 02 85 07 06 00 ff 0a 00 ff 75 08 95 0f b1 02 c0 05 01 09 06 a1
01 85 0a 05 07 19 e0 29 e7 15 00 25 01 75 01 95 08 81 02 95 06 75 08 15 00 26 a4 00 05 07
19 00 2a a4 00 81 00 c0 05 01 09 02 a1 01 85 0b 09 01 a1 00 95 10 75 01 15 00 25 01 05 09
19 01 29 10 81 02 05 01 16 01 f8 26 ff 07 75 0c 95 02 09 30 09 31 81 06 15 81 25 7f 75 08
95 01 09 38 81 06 95 01 05 0c 0a 38 02 81 06 c0 c0 06 43 ff 0a 02 02 a1 01 85 1a 75 08 95
13 15 00 26 ff 00 09 02 81 00 09 02 91 00 c0
N: Bluetooth HID Hub - RPi
I: 5 1d6b 0246
# ReportID: 4 / Button: 0 0 0 0 0 0 0 0 | X: 0 | Y: 0 | Wheel: 0 | 0xcff00: 0 | Vendor Usage 1: 1 , 0 , 0 , 0 , 0 , 0 , 0 , 0
E: 000000.000000 16 04 00 00 00 00 00 00 00 01 00 00 00 00 00 00 00
# ReportID: 4 / Button: 1 0 0 0 0 0 0 0 | X: 0 | Y: 0 | Wheel: 0 | 0xcff00: 0 | Vendor Usage 1: 1 , 1 , 0 , 0 , 0 , 0 , 0 , 0
E: 000000.000698 16 04 01 00 00 00 00 00 00 01 01 00 00 00 00 00 00
# ReportID: 4 / Button: 0 0 0 0 0 0 0 0 | X: 0 | Y: 0 | Wheel: 0 | 0xcff00: 0 | Vendor Usage 1: 1 , 0 , 0 , 0 , 0 , 0 , 0 , 0
E: 000000.001094 16 04 00 00 00 00 00 00 00 01 00 00 00 00 00 00 00
# ReportID: 4 / Button: 1 0 0 0 0 0 0 0 | X: 0 | Y: 0 | Wheel: 0 | 0xcff00: 0 | Vendor Usage 1: 1 , 1 , 0 , 0 , 0 , 0 , 0 , 0
E: 000000.001470 16 04 01 00 00 00 00 00 00 01 01 00 00 00 00 00 00
# ReportID: 4 / Button: 0 0 0 0 0 0 0 0 | X: 0 | Y: 0 | Wheel: 0 | 0xcff00: 0 | Vendor Usage 1: 1 , 0 , 0 , 0 , 0 , 0 , 0 , 0
E: 000000.001878 16 04 00 00 00 00 00 00 00 01 00 00 00 00 00 00 00
# ReportID: 4 / Button: 0 0 0 0 0 0 0 0 | X: 0 | Y: 0 | Wheel: 0 | 0xcff00: 0 | Vendor Usage 1: 1 , 0 , 0 , 0 , 0 , 0 , 0 , 0
E: 000000.044655 16 04 00 00 00 00 00 00 00 01 00 00 00 00 00 00 00
```

One difference is that the ReportID has been changed from 1 to 4 on each event.
This is needed for the RPi to be able to handle multiple devices. This is not the cause.

If we save the above output to a file, then we can repeat the event with ``hid-replay my-recording.hid``.
This allows us to change parts and test them out.

Through trial and error we can figure out that the double-click only works when the vendor ID (middle value under ``I:``) is set to ``0b33``.
This is the ID for Contour and it suggests that there is vendor-specific code in the kernel to make this button work. Not helpful...

## Finding a fix

Let's look at what a normal left-click looks like from the mouse. These are the events emitted:

```
# ReportID: 1 / Button: 1 0 0 0 0 0 0 0 | X: 0 | Y: 0 | Wheel: 0 | 0xcff00: 0 | Vendor Usage 1: 1 , 1 , 0 , 0 , 0 , 0 , 0 , 0
E: 000000.000000 16 01 01 00 00 00 00 00 00 01 01 00 00 00 00 00 00
# ReportID: 1 / Button: 0 0 0 0 0 0 0 0 | X: 0 | Y: 0 | Wheel: 0 | 0xcff00: 0 | Vendor Usage 1: 1 , 0 , 0 , 0 , 0 , 0 , 0 , 0
E: 000000.129961 16 01 00 00 00 00 00 00 00 01 00 00 00 00 00 00 00
```

It looks interesting that a left-click has a ``01`` where the double-click sends a ``80``
(it also switches to ``00`` on the up event which doesn't happen on the double-click).
Hmm, it seems like the double-click actually sends 2 clicks of a different button.
What if we change the ``80`` to ``01``, so we actually send 2 left-click events?
Running that through ``hid-replay``, it works!

## Writing a filter

To implement the fix we need to create a new filter function.
While ssh'd into the RPi, create the new file: ``bthidhub/filters/contour.py``:

```
"""Contour Rollermouse"""

def message_filter(msg: bytes) -> bytes:
    if len(msg) >= 10 and msg[9] == 0x80:
        # Convert vendor specific double click (button 0x80), to normal double click (button 1).
        msg = msg[:9] + (b"\x01" if msg[1] else b"\x00") + msg[10:]
    return msg
```

The docstring on the first line can be used to customise the name in the UI.
If omitted, the name will be based on the filename.
Each module in the filters directory must define a function named ``message_filter``.
This function will be automatically imported and available as a filter.

The above filter function changes the byte sequence for the double click button, so it
looks like regular single clicks.

Restart the service:
``sudo systemctl restart remapper``

After a few seconds, refresh the web page and you should see the new filter in the dropdown
options. Select the new filter and it will immediately be applied to all events from that
device.

If you add ``print()`` calls for debugging, you can view the logs with:
``journalctl -xeu remapper``

### Using clases to store state

With the above code, it seems that the double click is only getting recognised as a single
click. Through more trial and error, comparing working/non-working events we can also
figure out that the 2 left-click events only get interpreted as a double-click if there's
a gap between the events of atleast around 25ms (the first number after ``E:`` is a
timestamp of the event).

To emulate this, we can create a class to store a boolean state and then sleep for 25ms in
the middle of the double click events. A complete filter for this might look like:

```
"""Contour Rollermouse"""

import time

class ContourMessageFilter:
    delay = False

    def filter_message(self, msg: bytes) -> bytes:
        if len(msg) >= 10 and msg[9] == 0x80:
            # Convert vendor specific double click (button 0x80), to normal double click (button 1).
            msg = msg[:9] + (b"\x01" if msg[1] else b"\x00") + msg[10:]
            if msg[1]:
                # Ensure a small delay between click events otherwise it won't register as a double click.
                if self.delay:
                    time.sleep(0.025)
                self.delay = not self.delay
        return msg

message_filter = ContourMessageFilter().filter_message
```

Note the last line which assigns the bound method to the ``message_filter`` name, so it
can still be imported the same way as our first example.

### Suppressing events

If you want to block some messages from being sent entirely, instead of returning the
message, simply ``return None``.

You will need to change the return type annotation in this case to ``-> bytes | None:``.

### Compiling for maximum performance

Once you have your filters working correctly, you can compile the code to ensure
maximum performance. Simply run:

```
cd $HOME/bthidhub/
mypyc
```

This may take upto 20 mins to complete.

## Notes

The same techniques could be used to remap events when you just want to change
the behaviour of a device.

[This post](http://who-t.blogspot.com/2018/12/understanding-hid-report-descriptors.html)
is super helpful in getting your head around HID descriptors.

If you have a report descriptor and don't want to use hid-tools to decode, an online parser is:
https://eleccelerator.com/usbdescreqparser/
