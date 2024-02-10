# UPnP SSDP responder for Canon cameras
These scripts are intended to support connecting to Canon PowerShot (point and shoot)
and similar models over WiFi from a PC. They may or may not work with other Canon product
lines.

The supported cameras use [PTP/IP](https://en.wikipedia.org/wiki/Picture_Transfer_Protocol)
with [UPnP](https://en.wikipedia.org/wiki/Universal_Plug_and_Play) for discovery and pairing.
These scripts provide support only for the UPnP portion, a PTP/IP client such as
[chdkptp](https://app.assembla.com/spaces/chdkptp/wiki) or [gphoto2](http://www.gphoto.org/)
must be connected after the UPnP sequence to interact with the camera.

They are primarily intended for use on Linux, since Windows can natively
send UPnP responses recognized by the cameras, however, they can also be
used from from Windows with [msys2](https://www.msys2.org/) msys or mingw python,
and likely other Windows Pythons. They are also known to work on MacOS 11, 12 and
likely work on other versions.

See [this CHDK forum thread](https://chdk.setepontos.com/index.php?topic=10724.msg145418#msg145418)
for additional details.

## Scripts

### ptpip-canon-upnp-helper.py
Responds to UPnP `M-SEARCH` requests for `upnp:rootdevice` and `ssdp:all`

Note `ptpip-canon-upnp-helper.py` responds to requests for `upnp:rootdevice` and
ssdp:all, so it may respond to requests from devices other than Canon cameras.
The response also falsely identifies itself as a Windows server, because Canon
firmware requires it. This is probably harmless in most cases, but SSDP/UPnP
aware software might display the configured name in a UI, or conceivably become
confused in some other way.

Note IPv6 is not supported by these scripts. In my testing, the cameras only
attempted IPv4. However, I have not tested an IPv6-only environment

### ptpip-canon-desc-helper.py
Responds HTTP GET requests with an XML file containing a suitable description
By default, started automatically by `ptpip-canon-upnp-helper.py`, so you
shouldn't need to run it directly. When using native windows (mingw etc)
python, it will be opened in a new window.

## Install / Dependencies
* Python 3
* Optionally, a venv
   * `python3 -m venv env/ptpip-helpers`
   * `. env/ptpip-helpers/bin/activate`
* `pip install ssdpy`

## Connecting
To connect from [chdkptp](https://app.assembla.com/spaces/chdkptp/wiki) you must
build chdkptp with PTP/IP support by setting `PTPIP_SUPPORT=1` in `config.mk`

### Basic usage
```
ptpip-canon-upnp-helper.py LAN_IP_Address
```

`LAN_IP_Address` must be an IPv4 address (not hostname) on the computer you
want to connect the camera to, reachable from the wifi network the camera
will connect from.

### Basic options
Use -n to set the name that will appear in the Canon UI. It defaults to the
computer hostname, as returned by `socket.gethostname()`

Pass -P to `ptpip-canon-upnp-helper.py` to set the port used for description
requests. Default is 8043

UPnP requests are listened for on UDP port 1900. This is defined on the camera
and cannot be changed.

To provide a persistent ID for your connection `ptpip-canon-upnp-helper.py` will
create a file named `ptpip-canon-helper.uuid` in the current directory if it does
not already exist. Cameras require a UPnP response from the corresponding GUID
for every connection after pairing completes.

### Connecting a camera
To connect a camera, go to the connection menu on the camera, select computer
and "Add a Device..."

If it works, you should see the hostname of your computer (or the name specified
with the -name option) listed on the Canon display.

This process will generate some requests to the scripts, which will show the
requesting IP in standard output, like
```
INFO:ptpip-upnp-helper:Received qualifying M-SEARCH from ('192.168.123.45', 58981)
192.168.123.45 - - [29/Mar/2021 22:36:47] "GET /ptpip-canon-desc-helper.xml HTTP/1.1" 200 -
```

Select the name and press set. The camera will go into a screen that says
`Connected to device <name>`

To connect in chdkptp, enter
```
connect -h=<camera_ip>
```
You can use the helper output to get the camera IP, but as noted above,
beware queries from other devices may also be present.

To prevent the camera from timing out and closing the connection, use
```
!con:ptp_get_object_handles()
```

The screen will go black. To re-enable the screen, enter
```
=post_levent_to_ui(4482)
```
for DryOS cameras, or
```
=post_levent_to_ui(4418)
```
for VxWorks

chdkptp starting from r1161 in the default configuration does both the above
steps automatically, based on the settings
```
cam_connect_set_ptp_mode
cam_connect_unlock_ui
```

## CHDK functionality over PTP/IP
File transfers, non-shooting script and most other non-shooting related
operations should work. Switching to shooting mode or shooting fail on some
cameras. In some cases, this can work worked around with additional hacking.
See the thread linked at the start for additional discussion.

## Disconnecting
Use the Canon UI or `dis` in chdkptp.

Use control+C to kill the scripts.

## Changelog
* 0.1.1 - 2024/02/09 Public repo, doc updates, no code changes
* 0.1.1 - 2021/04/18 Improved windows support
* 0.1.0 - 2021/03/29 Initial release

