#! /usr/bin/env python
"""
run ngrok http 5000, flask defaults to run on port 5000
update outgoing webhooks link at https://plotkin-home.slack.com/apps/A0F7VRG6Q-outgoing-webhooks
then run Groceries.py as nohup ./Groceries.py
"""

#TODO: add function to show when an item was last purchased

import os
from flask import Flask, request, Response
import slackbots as sb

app = Flask(__name__)

SLACK_WEBHOOK_SECRET = os.environ.get('SLACK_WEBHOOK_SECRET')

mrpear = sb.GroceryBot()

@app.route('/slack', methods=['POST'])
def inbound():
    if request.form.get('token') == SLACK_WEBHOOK_SECRET:
        channel = request.form.get('channel_name')
        username = request.form.get('user_name')
        text = request.form.get('text')
        inbound_message = username + " in " + channel + " says: " + text
        print(inbound_message)

        mrpear.listen(text, user = username)
    return Response(), 200

@app.route('/', methods=['GET'])
def test():
    return Response('It works!')

if __name__ == "__main__":
    app.run(debug=True)
