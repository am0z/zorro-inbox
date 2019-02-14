#!/usr/bin/env python

import shlex

from sanic import Sanic
from sanic.response import json

from imbox import Imbox, parser

# TODO: flask?
# TODO: multiuser

app = Sanic()
client = None

@app.route("/<tag>/")
async def get_list(request, tag):
    global client
    if not client:
        return json({"error": "Please, login"})
    else:
        messages = []
        if client.selected is not tag:
            for item in client.connection.list()[1]:
                real_tag = shlex.split(item.decode())[-1]
                if real_tag.lower().count(tag):
                    break
            client.connection.select(real_tag)
        client.selected = tag
        uids = client.connection.uid('search', None, '(ALL)')[1][0].split()
        response = client.connection.uid("fetch", b",".join(uids), "(BODY.PEEK[HEADER.FIELDS (FROM TO DATE SUBJECT)])")
        for labels, message in response[1][::2]:
            message = parser.parse_email(message)
            message.uid = labels.split()[2]
            messages.append(message)
        return json(messages)

@app.route("/<tag>/<uid>/")
async def get_message(request, tag, uid):
    if client.selected is not tag:
        for item in client.connection.list()[1]:
            real_tag = shlex.split(item.decode())[-1]
            if real_tag.lower().count(tag):
                break
        client.connection.select(real_tag)
    client.selected = tag

    response = client.connection.uid("fetch", uid, "(BODY.PEEK[])")
    labels, message = response[1][0]
    message = parser.parse_email(message)
    del message.raw_email
    message.uid = labels.split()[2]
    return json(message)

@app.post('/login')
async def post_handler(request):
    global client
    password = request.json["password"]
    client = Imbox("imap.gmail.com", username="andrey@gethappie.me", password=password)
    client.selected = None
    return json({"success": "logged in"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
