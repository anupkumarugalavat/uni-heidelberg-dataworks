# Decoupling Strategy: Running the Same System Anywhere (Cloud or On-Prem)

## Main Idea
We want to build a system that works the same way whether an organization uses AWS (the cloud) or keeps everything on their own servers.

## Storage Layer: It's All the Same Bucket
### The Problem
If we write our code to only talk to AWS S3, then an organization with their own local storage (think of it as a fake S3 that runs on their server) can't use the system without completely rewriting everything.

### The Solution
We write the code to be "Storage-neutral" Instead of saying "go to AWS S3" we say "go to whatever storage location is configured."

### How It Works
- When the code runs in AWS, the system automatically talks to AWS S3.
- When the code runs on-prem, it gets an environment variable that says "use local storage at http://local-storage:port" instead.
- The actual code doesn't change, it just receives a different address to talk to.

## Processing Layer: Containers = Portability
### The Problem
If the processing logic only runs on AWS ECS, an organization can't run it on their own servers without major rewrites.

### The Solution
We package everything (code + all dependencies) into a Docker container. This container is like a "box" that contains everything needed to run the processor. It doesn't care if it's running on AWS or on a local storage.

### How It Works
- In AWS: The container runs on AWS ECS Fargate (a managed service).
- On-Prem: The same container runs on the organization's local Docker engine or Kubernetes cluster.
- The container is identical in both places, same Python libraries, same operating system, same everything.

## Trigger Layer: Standard Format, Any Source
### The Problem
In AWS, S3 automatically sends a "notification" when a file is uploaded. An on-prem system doesn't have this automatic trigger.

### The Solution
We define a standard message format (JSON) that describes "a file was uploaded." Whether this message comes from AWS S3 or a local monitoring script doesn't matter, the processor reads the same format.

### How It Works
- In AWS: When a file lands in S3, AWS creates a JSON message and sends it to Lambda.
- On-Prem: A simple local script watches a folder and, when a file appears, creates the same JSON message and sends it to the processor.
- The processor doesn't care how the message arrived, it just processes whatever message it receives.

## Audit Layer: Log it Somewhere, Anywhere
### The Problem
If the code always writes audit logs to DynamoDB (AWS), an organization with their own servers has nowhere to put the logs.

### The Solution
Instead of the code directly talking to DynamoDB, we create a simple "middleman service" (an API endpoint) that accepts audit logs. This middleman decides where to actually store them.

### How It Works
- In AWS: The middleman receives the log and saves it to DynamoDB.
- On-Prem: The middleman receives the same log and saves it to their local PostgreSQL database or any other storage they want.
- The processor code doesn't change, it just sends the log to the middleman and moves on.

### The Bottom Line
- The "brain" of the system (the logic that validates files, processes data, and logs everything) is written once and works everywhere.
- The "infrastructure" (storage, compute, databases) is pluggable, swap it in and out like changing a lightbulb.
- An organization can use AWS today and switch to their own servers tomorrow without rewriting a single line of core code.

## What an Organization Needs to Do (To Use This On-Prem)
1. Pull the Docker container (the same one used in AWS).
2. Set environment variables to point to their local storage, their local servers (Docker/Kubernetes), and their local database (PostgreSQL).
3. Run it. Everything works the same.
4. No code changes. No rewrites. Just configuration.