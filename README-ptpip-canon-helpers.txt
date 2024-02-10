These scripts are intended to support connecting Canon cameras using PTP/IP.
They are primarily intended for use on Linux, since Windows can natively
send UPnP responses recognized by the cameras, however, they can also be
used from from windows with msys2 msys or mingw python.
They also work on MacOS 11, 12 and probably other versions.

See this CHDK forum thread for additional details
https://chdk.setepontos.com/index.php?topic=10724.msg145418#msg145418

ptpip-canon-upnp-helper.py
Responds to UPnP M-SEARCH requests for upnp:rootdevice and ssdp:all

ptpip-canon-desc-helper.py
Responds HTTP GET requests with an XML file containing a suitable description
By default, started automatically by ptpip-canon-upnp-helper.py, so you
shouldn't need to run it directly. When using native windows (mingw etc)
python, it will be opened in a new window.

Note ptpip-canon-upnp-helper.py responds to requests for upnp:rootdevice and
ssdp:all, so it may respond to requests from devices other than Canon cameras.
The response also falsely identifies itself as a Windows server, because Canon
firmware requires it. This is probably harmless in most cases, but SSDP/UPnP
aware software might display the configured name in a UI, or conceivably become
confused in some other way.


Dependencies:
Python 3
pip install ssdpy

To connect from chdkptp (https://app.assembla.com/wiki/show/chdkptp) you must
build chdkptp with PTP/IP support by setting PTPIP_SUPPORT=1 in config.mk

Basic usage:
ptpip-canon-upnp-helper.py LAN_IP_Address

LAN_IP_Address must be an IPv4 address (not hostname) on the computer you
want to connect the camera to, reachable from the wifi network the camera
will connect from.

Basic options:
Use -n to set the name that will appear in the Canon UI. It defaults to the
computer hostname, as returned by socket.gethostname()

Pass -P to ptpip-canon-upnp-helper.py to set the port used for description
requests. Default is 8043

UPnP requests are listened for on UDP port 1900. This is defined on the camera
and cannot be changed.

To provide a persistent ID for your connection ptpip-canon-upnp-helper.py will
create a file named ptpip-canon-helper.uuid in the current directory if it does
not already exist.


To connect a camera, go to the connection menu on the camera, select computer
and "Add a Device..."

If it works, you should see the hostname of your computer (or the name specified
with the -name option) listed on the Canon display.

This process will generate some requests to the scripts, which will show the
requesting IP in standard output, like
INFO:ptpip-upnp-helper:Received qualifying M-SEARCH from ('192.168.123.45', 58981)
192.168.123.45 - - [29/Mar/2021 22:36:47] "GET /ptpip-canon-desc-helper.xml HTTP/1.1" 200 -

Select the name and press set. The camera will go into a screen that says
"Connected to device <name>"

To connect in chdkptp, enter
connect -h=<camera_ip>

To prevent the camera from timing out and closing the connection, use
!con:ptp_get_object_handles()

The screen will go black. To re-enable the screen, enter
=post_levent_to_ui(4482)
for DryOS cameras, or
=post_levent_to_ui(4418)
for VxWorks

chdkptp starting from r1161 in the default configuration does both the above
steps automatically, based on the settings
cam_connect_set_ptp_mode
cam_connect_unlock_ui

File transfers, non-shooting script and most other non-shooting related
operations should work. Switching to shooting mode or shooting fail on some
cameras. In some cases, this can work worked around with additional hacking.
See the thread linked at the start for additional discussion.

Use control+C to kill the scripts.


Note IPv6 is not supported by these scripts. In my testing, the cameras only
attempted IPv4. However, I have not tested an IPv6-only environment

Changelog:
0.1.1 - 2021/04/18 Improved windows support
0.1.0 - 2021/03/29 Initial release

