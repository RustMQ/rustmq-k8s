# Example: Job with Work Queue with Pod Per Work Item

In this example, we will run a Kubernetes Job with multiple parallel
worker processes.  You may want to be familiar with the basic,
non-parallel, use of [Job](https://kubernetes.io/docs/concepts/workloads/controllers/jobs-run-to-completion/) first.

In this example, as each pod is created, it picks up one unit of work
from a task queue, completes it, deletes it from the queue, and exits if queue has no other unit of work in it.

Here is an overview of the steps in this example:

1. **Start a RustMQ service to hold the work queue.**  In this example, we use RustMQ service to store our work items in a queue. In this example, we use a custom client library to detect when a work queue is empty.
1. **Create a queue, and fill it with messages.**  Each message represents one task to be done.  In
  this example, a message is just an fruit name that we will print in stdout.
1. **Start a Job that works on tasks from the queue.**  The Job starts two pods. Each pod takes one unit of work from a task queue, completes it, deletes it from the queue, and exits if queue has no other unit of work in it.

## Starting RustMQ

### Starting Redis

For this example, we will start instance of Redis.
See the [Redis](https://hub.kubeapps.com/charts/stable/redis) for an instruction how to start a Redis instance.

*Note:* Test configuration is secured via password. This password is required in next step

### Start RustMQ Service

Now lets start the queue service called RustMQ.

```console
$ kubectl create -f ./rustmq-web-deployment.yaml
deployment "rustmq-web" created
$ kubectl create -f ./rustmq-web-service.yaml
service "rustmq-web" created
```

#### Filling the Queue with tasks

Now lets create the queue and fill it with some "tasks". In our example, our tasks are just strings to be printed.

First, create a job called **job1**:

```console
$ curl -d '{"queue":{"message_timeout":60,"message_expiration":3600,"type":"pull"}}' -H "Content-Type: application/json" -X PUT http://<minikube_ip>:<rustmq_web_internal_ip>/3/projects/1/queues/job1
```

**Note:** Replace with your Minikube IP and RustMQ Web Service internal IP

Now when queue is created we could add some work items:

```console
curl -d '{"messages":[{"body":"apple","delay":0},{"body":"banana","delay":0},{"body":"cherry","delay":0},{"body":"date","delay":0},{"body":"fig","delay":0},{"body":"grape","delay":0},{"body":"lemon","delay":0},{"body":"melon","delay":0},{"body":"orange","delay":0}]}' -H "Content-Type: application/json" -X POST http://<minikube_ip>:<rustmq_web_internal_ip>/3/projects/1/queues/job1/messages
```

## Create an Image

Now we are ready to create an image that we will run.

We will use a python worker program with requests HTTP library to read the messages from the message queue.

The "worker" program in each Pod of the Job uses the work queue
client library to get work.  Here it is:

<!-- BEGIN MUNGE: EXAMPLE worker.py -->

```python
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
```

[Download example](worker.py?raw=true)
<!-- END MUNGE: EXAMPLE worker.py -->

If you are working from the source tree,
change directory to the `examples/job/work-queue-3` directory.
Otherwise, download [`worker.py`](worker.py?raw=true), and [`Dockerfile`](Dockerfile?raw=true)
using above links. Then build the image:

```console
$ docker build -t job-wq-3 .
```

### Push the image

For the [Docker Hub](https://hub.docker.com/), tag your app image with
your username and push to the Hub with the below commands. Replace
`<username>` with your Hub username.

```
docker tag job-wq-3 <username>/job-wq-3
docker push <username>/job-wq-3
```

You need to push to a public repository or [configure your cluster to be able to access
your private repository](../../../docs/user-guide/images.md).

If you are using [Google Container
Registry](https://cloud.google.com/tools/container-registry/), tag
your app image with your project ID, and push to GCR. Replace
`<project>` with your project ID.

```
docker tag job-wq-3 gcr.io/<project>/job-wq-3
gcloud docker push gcr.io/<project>/job-wq-3
```


## Defining a Job

Here is the job definition:


<!-- BEGIN MUNGE: EXAMPLE job.yaml -->

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: job-wq-3
spec:
  parallelism: 2
  template:
    metadata:
      name: job-wq-3
    spec:
      containers:
      - name: c
        image: gcr.io/myproject/job-wq-3 # image: job-wq-3 -> from local Docker rigistry
        #imagePullPolicy: IfNotPresent
      restartPolicy: OnFailure
```

[Download example](job.yaml?raw=true)
<!-- END MUNGE: EXAMPLE job.yaml -->

Be sure to edit the job template to
change `gcr.io/myproject` to your own path.

In this example, each pod works on several items from the queue and then exits when there are no more items.
Since the workers themselves detect when the workqueue is empty, and the Job controller does not
know about the workqueue, it relies on the workers to signal when they are done working.
The workers signal that the queue is empty by exiting with success.  So, as soon as any worker
exits with success, the controller knows the work is done, and the Pods will exit soon.
So, we set the completion count of the Job to 1.  The job controller will wait for the other pods to complete
too.


## Running the Job

So, now run the Job:

```console
$ kubectl create -f ./job.yaml
```

Now wait a bit, then check on the job.

```console
$ ./kubectl describe jobs/job-wq-2
Name:		job-wq-2
Namespace:	default
Image(s):	gcr.io/exampleproject/job-wq-2
Selector:	app in (job-wq-2)
Parallelism:	2
Completions:	Unset
Start Time:	Mon, 11 Jan 2016 17:07:59 -0800
Labels:		app=job-wq-2
Pods Statuses:	1 Running / 0 Succeeded / 0 Failed
No volumes.
Events:
  FirstSeen	LastSeen	Count	From			SubobjectPath	Type		Reason			Message
  ---------	--------	-----	----			-------------	--------	------			-------
  33s		33s		1	{job-controller }			Normal		SuccessfulCreate	Created pod: job-wq-2-lglf8


$ kubectl logs pods/job-wq-2-7r7b2
Working on banana
Working on date
Working on lemon
```

As you can see, one of our pods worked on several work units.
