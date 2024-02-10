#!/usr/bin/env python3
# based https://github.com/MoshiBin/ssdpy cli server
# Copyright (c) 2019 Moshi Binyamini
#
# Modified to send a 200 OK response instead of NOTIFY
# and various other specifics expected by Canon cameras
#
# Copyright 2021 reyalp (at) gmail.com
#
# MIT License
#
#   Permission is hereby granted, free of charge, to any person obtaining a copy
#   of this software and associated documentation files (the "Software"), to deal
#   in the Software without restriction, including without limitation the rights
#   to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#   copies of the Software, and to permit persons to whom the Software is
#   furnished to do so, subject to the following conditions:
#
#   The above copyright notice and this permission notice shall be included in all
#   copies or substantial portions of the Software.
#
#   THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#   IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#   FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#   AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#   LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#   OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#   SOFTWARE.

# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import logging
import uuid
import os
import sys
from ssdpy.server import SSDPServer
from ssdpy.http_helper import parse_headers

import subprocess

VERSION = "0.1.1"

logging.basicConfig()

logger = logging.getLogger("ptpip-upnp-helper")
logger.setLevel(logging.INFO)

def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Respond to UPnP M-SEARCH requests from Canon cameras to support PTP/IP connection"
    )
    parser.add_argument("-V", "--version", action="version", version="%(prog)s {}".format(VERSION))
    parser.add_argument("-v", "--verbose", help="Be more verbose", action="store_true")
    proto_group = parser.add_mutually_exclusive_group()
    proto_group.add_argument("-4", "--ipv4", help="Listen on IPv4 (default: True)", action="store_true")
    proto_group.add_argument("-6", "--ipv6", help="Listen on IPv6 instead of IPv4", action="store_true")
    parser.add_argument("-i", "--iface", help="Listen on a specific network interface")
    parser.add_argument(
        "-p",
        "--port",
        help="Listen on this port (default: 1900)",
        default=1900,
        type=int,
    )
    parser.add_argument(
        "--max-age",
        help="Seconds responses should be cached for (default: 900)",
        type=int,
        default=900,
    )
    parser.add_argument(
        "local_ip",
        help="IP address response should point to (required)",
    )
    parser.add_argument(
        "-P",
        "--desc-port",
        help="Port address response should point to (default: 8043)",
        default="8043"
    )
    parser.add_argument(
        "-f",
        "--file-path",
        help="File path response should point to (default: ptpip-canon-desc-helper.xml)",
        default="ptpip-canon-desc-helper.xml",
    )
    parser.add_argument(
        "-a",
        "--bind-all",
        help="Bind all addresses (or as spec by -i, -4, -6), not just local-ip",
        action="store_true"
    )
    parser.add_argument(
        "--no-start-desc",
        help="do not start ptpip-canon-desc-helper.py",
        action="store_true"
    )
    parser.add_argument(
        "-n",
        "--name",
        help="friendly name of device (default: Hostname)",
    )
    return parser.parse_args(argv)

# uuids are supposed to be stable
def get_uuid():
    fname = 'ptpip-canon-helper.uuid'
    if os.path.isfile(fname):
        with open(fname,'r') as infile:
            uuid_str = infile.read()
        logger.info("read uuid {} {}".format(fname,uuid_str))
    else:
        uuid_str = str(uuid.uuid4())
        with open(fname,'w') as outfile:
            outfile.write(uuid_str)
        logger.info("created new uuid {} {}".format(fname,uuid_str))

    return uuid_str

def create_upnp_resp_payload(st, usn, location, max_age=900, extra_fields=None):
    """
    Create a UPnP response packet using the given parameters.
    Returns a bytes object containing a valid search response.

    :param st: Search target. Based on M-SEARCH st
    :type st: str

    :param usn: Unique identifier for the service.
    :type usn: str

    :param location: A URL for more information about the service. Required
    :type location: str

    :param max_age: Amount of time in seconds response should be cached. In UPnP, this header is required.
    :type max_age: int

    :param extra_fields: Extra header fields to send. UPnP SSDP section 1.1.3 allows for extra vendor-specific fields to be sent in the NOTIFY packet. According to the spec, the field names MUST be in the format of `token`.`domain-name`, for example `myheader.philips.com`. SSDPy, however, does not check this. Normally, headers should be in ASCII - but this function does not enforce that.

    :return: A bytes object containing the generated response payload.
    """
    if max_age is not None and not isinstance(max_age, int):
        raise ValueError("max_age must by of type: int")
    data = (
        "HTTP/1.1 200 OK\r\n"
        "ST: {}\r\n"
        "USN: {}\r\n"
        "LOCATION: {}\r\n"
        "Cache-Control: max-age={}\r\n"
        ).format(st, usn, location, max_age)
    if extra_fields is not None:
        for field, value in extra_fields.items():
            data += "{}:{}\r\n".format(field, value)
    data += "\r\n"
    return data.encode("utf-8")

class UPnPResponder(SSDPServer):
    def on_recv(self, data, address):
        logger.debug("Received packet from {}: {}".format(address, data))
        try:
            headers = parse_headers(data)
        except ValueError:
            # Not an SSDP M-SEARCH; ignore.
            logger.debug("NOT M-SEARCH - SKIPPING")
            headers = {}
            pass
        # NOTE cam only sends upnp:rootdevice, could ignore ssdp:all
        if data.startswith(b"M-SEARCH") and (headers.get("st") == self.device_type or headers.get("st") == "ssdp:all"):
            logger.info("Received qualifying M-SEARCH from {}".format(address))
            logger.debug("M-SEARCH data: {}".format(headers))
            response_payload = create_upnp_resp_payload(
                st=self.device_type,
                usn=self.usn,
                location=self.location,
                max_age=self.max_age,
                extra_fields=self._extra_fields,
            )
            logger.debug("Created response: {}".format(response_payload))
            try:
                # NOTE spec requires a random delay
                self.sock.sendto(response_payload, address)
            except OSError as e:
                # Most commonly: We received a multicast from an IP not in our subnet
                logger.debug("Unable to send response to {}: {}".format(address, e))


def main(argv=None):
    args = parse_args(argv)

    if not args.bind_all:
        address = args.local_ip
    else:
        address = None

    location = 'http://{}:{}{}'.format(args.local_ip, args.desc_port,os.path.join('/',args.file_path))

    logger.info("Description location: {}".format(location))

    extra_fields = {
        # Cam requires Microsoft-Windows
        'Server':'Microsoft-Windows/10.0 UPnP/1.0 UPnP-Device-Host/1.0',
        'Ext':' ', # Cam doesn't require, but spec appears to
    }
    if args.ipv6:
        proto = "ipv6"
    else:
        proto = "ipv4"

    if args.iface is not None:
        args.iface = args.iface.encode("utf-8")

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    device_type = "upnp:rootdevice"

    uuid_str = get_uuid()

    if not args.no_start_desc:
        self_dir = os.path.dirname(os.path.abspath(__file__))

        helper_path = os.path.join(self_dir,'ptpip-canon-desc-helper.py')
        helper_args = [
            helper_path,
            '-p',args.desc_port,
            '-f',args.file_path,
            '-u',uuid_str
        ]
        if not args.bind_all:
            helper_args = [*helper_args, '--bind', args.local_ip]

        if args.name:
            helper_args = [*helper_args, '-n', args.name]

        # on windows, directly opening python script may not work, so run with python executable
        # and control+c on child processes may be wonky, so start in new window
        # msys2 msys returns 'posix' and behaves correctly with non-windows code
        if os.name == 'nt':
            helper_args = [sys.executable, *helper_args]
            desc_helper = subprocess.Popen(helper_args,close_fds=True, creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:
            desc_helper = subprocess.Popen(helper_args)

    server = UPnPResponder(
        "uuid:{}::{}".format(uuid_str,device_type),
        proto=proto,
        device_type=device_type,
        port=args.port,
        iface=args.iface,
        address=address,
        max_age=args.max_age,
        location=location,
        extra_fields=extra_fields,
    )

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.error("Keyboard interrupt received, shutting down")

main()
