#!/usr/bin/env python
"""
zorro-inbox backend app.

An Inbox by Google clone
"""

import chardet
import imaplib
import shlex
import time

from sanic import Sanic
from sanic.response import json, file, text, html

from imbox import Imbox, parser

# TODO: flask?


iframe_script = """<script src="/inline.js"></script>"""

FLAGS = {
    "seen": "\\Seen",
    "delete": "\\Deleted",
}

app = Sanic()
clients = {}
text_cache = {}  # TODO: cache the whole message maybe
html_cache = {}


def decode_bytes(b: bytes):
    """
    Decodes bytes to a string using chardet.  If a string comes in...just returns it.
    Args:
        b (bytes): bytes or string
    """
    if b is None:
        return None
    if isinstance(b, str):
        return b
    r = chardet.detect(b)
    encoding = r.get("encoding") if r else "utf-8"
    if not encoding:
        encoding = "utf-8"
    return b.decode(encoding, errors="ignore")


def quote_folder_name(folder_name: str):
    folder_name = folder_name.replace("\\", "\\\\")
    folder_name = folder_name.replace('"', '\\"')
    return f'"{folder_name}"'


@app.route("/api/<username>/<tag>/")
async def get_list(request, username, tag):
    global clients
    client, timestamp = clients.get(username, [None, None])
    if client and time.time() - timestamp > 60 * 60:  # over an hour
        del clients[username]
        client = None
    if not client:
        return json(None, status=401)
    messages = []
    if client.selected is not tag:
        for item in client.connection.list()[1]:
            real_tag = shlex.split(item.decode())[-1]
            if real_tag.lower().count(tag):
                break
        client.connection.select(quote_folder_name(real_tag))
    client.selected = tag
    uids = client.connection.uid('search', None, '(ALL)')[1][0].split()
    if not uids:
        return json([])
    response = client.connection.uid(
        "fetch",
        b",".join(uids[-100:]),
        "(BODY.PEEK[HEADER.FIELDS (FROM TO DATE SUBJECT)] FLAGS)")
    for labels, message in response[1][::2]:
        message = parser.parse_email(message)
        message.uid = labels.split()[2]
        message.flags = imaplib.ParseFlags(labels)
        del message.raw_email
        messages.append(message)
    return json(reversed(messages))


@app.get("/api/<username>/<tag>/<uid>.txt")
async def get_message_text(request, username, tag, uid):
    global text_cache
    response = text_cache.get(uid)
    if not response:
        client, _ = clients.get(username)
        response = client.connection.uid("fetch", uid, "(BODY.PEEK[])")
        labels, message = response[1][0]
        message = parser.parse_email(message)
        response = message.body["plain"][0] if message.body["plain"] else "No text"
        text_cache[uid] = decode_bytes(response)
    return text(response)


@app.get("/api/<username>/<tag>/<uid>.html")
async def get_message_html(request, username, tag, uid):
    global html_cache
    response = html_cache.get(uid)
    if not response:
        client, _ = clients.get(username)
        response = client.connection.uid("fetch", uid, "(BODY.PEEK[])")
        labels, message = response[1][0]
        message = parser.parse_email(message)
        if not message.body["html"] and message.body["plain"]:
            message.body["html"] = message.body["plain"]
        response = iframe_script + decode_bytes(message.body["html"][0]) if message.body["html"] else "No html"
    return html(response)


@app.delete("/api/<username>/<tag>/<uid>/flags/<flag>/")
async def delete_flag(request, username, tag, uid, flag):
    client, _ = clients.get(username)
    flag = FLAGS[flag]
    flags = client.connection.uid("store", uid, "-FLAGS", flag)[1][0]
    if flags is None:
        flags = ""
    flags = imaplib.ParseFlags(flags)
    return json(flags)


@app.post("/api/<username>/<tag>/<uid>/flags/<flag>/")
async def add_flag(request, username, tag, uid, flag):
    client, _ = clients.get(username)
    flag = FLAGS[flag]
    flags = client.connection.uid("store", uid, "+FLAGS", flag)[1][0]
    if flags is None:
        flags = ""
    flags = imaplib.ParseFlags(flags)
    return json(flags)


@app.post("/api/<username>")
async def post_handler(request, username):
    global clients
    password = request.json["password"]
    client = Imbox("imap.gmail.com", username=username, password=password)
    client.selected = None
    clients[username] = client, time.time()
    return json(None, status=200)


@app.route("")
@app.route("/<username>")
@app.route("/<username>/<tag>")
async def handle_request(request, username=None, tag=None):
    return await file("index.html")


@app.route("/inline.js")
async def handle_request(request, username=None, tag=None):
    return await file("inline.js")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
