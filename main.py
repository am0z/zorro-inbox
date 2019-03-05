#!/usr/bin/env python

import imaplib
import shlex

from sanic import Sanic
from sanic.response import json, file

from imbox import Imbox, parser

# TODO: flask?


FLAGS = {
    "seen": "\\Seen",
    "delete": "\\Deleted",
}

app = Sanic()
clients = {}


def quote_folder_name(folder_name: str):
    folder_name = folder_name.replace("\\", "\\\\")
    folder_name = folder_name.replace('"', '\\"')
    return f'"{folder_name}"'


@app.route("/api/<username>/<tag>/")
async def get_list(request, username, tag):
    global clients
    client = clients.get(username)
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
    response = client.connection.uid("fetch", b",".join(uids[-100:]), "(BODY.PEEK[HEADER.FIELDS (FROM TO DATE SUBJECT)] FLAGS)")
    for labels, message in response[1][::2]:
        message = parser.parse_email(message)
        message.uid = labels.split()[2]
        message.flags = imaplib.ParseFlags(labels)
        del message.raw_email
        messages.append(message)
    return json(reversed(messages))

@app.get("/api/<username>/<tag>/<uid>/")
async def get_message(request, username, tag, uid):
    client = clients.get(username)
    response = client.connection.uid("fetch", uid, "(BODY.PEEK[])")
    labels, message = response[1][0]
    message = parser.parse_email(message)
    del message.raw_email
    message.uid = labels.split()[2]
    return json(message)

@app.delete("/api/<username>/<tag>/<uid>/flags/<flag>/")
async def delete_flag(request, username, tag, uid, flag):
    client = clients.get(username)
    flag = FLAGS[flag]
    flags = client.connection.uid("store", uid, "-FLAGS", flag)[1][0]
    if flags is None:
        flags = ""
    flags = imaplib.ParseFlags(flags)
    return json(flags)

@app.post("/api/<username>/<tag>/<uid>/flags/<flag>/")
async def add_flag(request, username, tag, uid, flag):
    client = clients.get(username)
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
    clients[username] = client
    return json(None, status=200)

@app.route("")
@app.route("/<username>")
@app.route("/<username>/<tag>")
async def handle_request(request, username=None, tag=None):
    return await file('index.html')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
