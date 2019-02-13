#!/usr/bin/env python

from sanic import Sanic
from sanic.response import json

from imbox import Imbox

app = Sanic()
client = None

@app.route("/")
async def root(request):
    global client
    if not client:
        return json({"error": "Please, login"})
    else:
        # TODO: return only few header fields
        return json(list(client.messages()))

@app.post('/login')
async def post_handler(request):
    global client
    username = request.json["username"]
    password = request.json["password"]
    client = Imbox("imap.gmail.com", username=username, password=password)
    return json({"success": "logged in"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
