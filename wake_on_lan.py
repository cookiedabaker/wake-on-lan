#!/usr/bin/python
# -*- coding: utf-8 -*-
# Created on: 2022-06-11

import socket
import struct
import re
import argparse

_version = (1, 0, 0)
__version__ = ".".join(str(n) for n in _version)


def wakeOnLAN(magic_packet: bytes):
    """Takes a magic packet and broadcasts it to the network."""

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    s.sendto(magic_packet, ('<broadcast>', 7))

def formatMagicPacket(mac_address):
    """Takes a MAC address and formats it into a the correct format for broadcast."""
    
    check_format = re.fullmatch(
        '(([0-9A-Fa-f]{2}[-:\.]){5}[0-9A-Fa-f]{2})|'
        '(([0-9A-Fa-f]{4}[-:\.]){2}[0-9A-Fa-f]{4})',
        mac_address)

    if not check_format:
        raise ValueError("Incorrect MAC address format.")

    # Convert hex to packed binary
    mac_formatted = b''
    for h in mac_address.split(mac_address[2]):
        mac_formatted = b''.join([mac_formatted, struct.pack('B', int(h, 16))])

    # Add the magic
    packet = b''.join([b'\xff' * 6, mac_formatted * 16])

    return(packet)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Version: {0}\nSends a Wake-On-LAN magic packet for a designated MAC address.".format(__version__))
    parser.add_argument('-m', '--mac', nargs='*', help="Specifies a/multiple mac address(es) as input(s)")
    parser.add_argument('-f', '--file', nargs='*', help="Specifies a/multiple file(s) containing a/multiple mac address(es) as input(s)")
    parser.add_argument('-v', '--version', action='version', version=__version__)
    args = parser.parse_args()

    if args.mac is not None:
        for mac in args.mac:
            magic_packet = formatMagicPacket(mac)
            wakeOnLAN(magic_packet)
    
    if args.file is not None:
        for f in args.file:
            with open(f, 'r') as macfile:
                raw_mac = macfile.read()
                mac_list = raw_mac.splitlines()
                for mac in mac_list:
                    magic_packet = formatMagicPacket(mac)
                    wakeOnLAN(magic_packet)