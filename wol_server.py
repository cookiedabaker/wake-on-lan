#!/usr/bin/python
# -*- coding: utf-8 -*-
# Created on: 2024-09-08

from flask import Flask, request, abort
from markupsafe import escape
from wake_on_lan import wakeOnLAN, formatMagicPacket

app = Flask(__name__)

@app.route("/mac/<mac_address>")
def wake_on_mac(mac_address):
    try:
        magic_packet = formatMagicPacket(mac_address)
        wakeOnLAN(magic_packet)
    except ValueError:
        abort(400)
    return f"This MAC has been waked: {escape(mac_address)}"

@app.route('/file', methods=['GET', 'POST'])
def wake_on_file():
    if request.method == 'POST':
        f = request.files['the_file']

if __name__ == '__main__':
    app.run()