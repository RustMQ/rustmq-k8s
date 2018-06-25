#!/usr/bin/env python

import requests
import time
import os
import json

service = "rustmq-web-service"

url = "http://" + service + ":80/3/projects/1/queues/job1/reservations"
print("URL: " + url)
reserve_payload = {
    'n': 1,
    'delete': True
}
time.sleep(10) # Put your actual work here instead of sleep.

while True:
    r = requests.post(url, json=reserve_payload, timeout=30)
    res = r.json()
    messages = res['messages']
    if not messages:
        print("Queue empty, exiting")
        break

    for message in messages:
        print("Working on " + message['body'])
        time.sleep(10)
