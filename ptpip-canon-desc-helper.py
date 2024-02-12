#!/usr/bin/env python3
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

import http.server
import socketserver
from socket import gethostname
from functools import partial
from http import HTTPStatus
import sys
import argparse
import os
import logging

VERSION = "0.1.0"

logging.basicConfig()

logger = logging.getLogger("ptpip-desc-helper")
logger.setLevel(logging.INFO)


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Respond to device description requests from Canon PTP/IP cameras")
    parser.add_argument("-V", "--version", action="version", version="%(prog)s {}".format(VERSION))
    parser.add_argument(
        "-p",
        "--port",
        help="Listen on this port (default: 8043)",
        default=8043,
        type=int,
    )
    parser.add_argument(
        "-f",
        "--file-path",
        help="Path to answer requests on (default: ptpip-canon-desc-helper.xml)",
        default="ptpip-canon-desc-helper.xml",
    )
    parser.add_argument(
        "-u",
        "--uuid",
        help="uuid of device",
        required=True,
    )
    parser.add_argument(
        "-n",
        "--name",
        help="friendly name of device (default: Hostname)",
        default=gethostname(),
    )
    parser.add_argument(
        "--bind",
        help="bind to specified IP (otherwise, all)",
        default=''
    )
    return parser.parse_args(argv)

def format_response(name,uuid):
    # cams (elph130, at least) will accept a bare <friendlyName>...</friendlyName>
    # below includes fields required by spec, plus some informational values
    # in case it shows up in other UPnP software UIs
    data = (
'<?xml version="1.0"?>'
'<root xmlns="urn:schemas-upnp-org:device-1-0">'
'	<specVersion>'
'		<major>1</major>'
'		<minor>0</minor>'
'	</specVersion>'
'	<device>'
'		<UDN>uuid:{}</UDN>'
# normal windows friendlyName is in the form 'Computer: User:'
# cam only display computer part
'		<friendlyName>{}: PTPIPResponder:</friendlyName>'
'		<deviceType>urn:chdk-fandom-com:device:PTPIPConnectHelper:1</deviceType>'
'		<manufacturer>CHDK Project</manufacturer>'
'		<modelNumber>1.0</modelNumber>'
'		<manufacturerURL>https://chdk.fandom.com/wiki/CHDK</manufacturerURL>'
'		<modelName>Helper for establishing PTP/IP connections with some Canon cameras</modelName>'
'		<modelURL>https://chdk.fandom.com/wiki/PTP_Extension</modelURL>'
'	</device>'
'</root>'
    ).format(uuid,name)

    return data.encode("utf-8")


PORT = 8000

class MyServer(http.server.BaseHTTPRequestHandler):
    # must spoof windows for cam to recognize
    server_version = 'Microsoft-Windows/10.0 UPnP/1.0 UPnP-Device-Host/1.0'
    sys_version = 'Microsoft-HTTPAPI/2.0'
    protocol_version = 'HTTP/1.1'

    def __init__(self, *args, responder_data=None, **kwargs):
        self.responder_name = responder_data['name']
        self.responder_uuid = responder_data['uuid']
        self.responder_path = responder_data['path']
        super().__init__(*args, **kwargs)

    def do_GET(self):
        """Serve a GET request."""
        if self.path != os.path.join('/',self.responder_path):
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return

        body = format_response(self.responder_name,self.responder_uuid)
        self.send_response(HTTPStatus.OK)
        # cam requires this content type
        self.send_header("Content-type", 'text/xml; charset="utf-8"')
        self.send_header("Content-Length", len(body))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

def main(argv=None):
    args = parse_args(argv)

    responder_data = {
        'name':args.name,
        'uuid':args.uuid,
        'path':args.file_path
    }
    handler_class = partial(MyServer,responder_data=responder_data)
    with socketserver.TCPServer((args.bind, args.port), handler_class) as httpd:
        host, port = httpd.socket.getsockname()[:2]
        url_host = f'[{host}]' if ':' in host else host
        logger.info(f"Serving http://{url_host}:{port}/{args.file_path}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            logger.error("Keyboard interrupt received, exiting.")
            sys.exit(0)

main()
