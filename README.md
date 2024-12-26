# k8s-nodeselector-mutatingwebhook

# Objective

The objective of this project is add a NodeSelector to all new Pods in the NPRI Cluster.  Two methods of deploying the K8s MutatingWebhook are explained:

1. Manual installation of the K8s MutatingWebhook using K8s resource manifest files deployed using the kubectl command.
2. Standalone Helm Chart package that deploys the K8s MutatingWebhook solution using Helm templates and values file (see separate README.md in the [/helm](helm/README.md) directory).

# Manual installation of the K8s MutatingWebhook

## Prerequisites

### Access to Linux CLI

### kubectl

In the case of this PoC I installed `kubectl` by following the instructions found at the Gangway Kubectl link [https://kubectl-green.private.dev.app.tecsys.cloud/commandline](https://kubectl-green.private.dev.app.tecsys.cloud/commandline)

### Kubernetes NPRI Cluster

I used the Tecsys itopia-npri-default-us-east-1-blue cluster.

## Docker Repository Access

A Docker repository like Docker Hub, AWS Elastic Container Registry (ECR), JFrog Artifactory, etc is required for storing the Webhook Docker image that will be used in the solution.  For this PoC I initially used AWS ECR and then switched to Artifactory using an image pushed using the [https://gitlab.tecsysrd.cloud/ops/noc/noc-base-docker-images.git](https://gitlab.tecsysrd.cloud/ops/noc/noc-base-docker-images.git) repository.

## PoC Solution Implementation Steps

### Step 1: Generate TLS Certificates

Kubernetes admission webhooks require the webhook server to use HTTPS. A TLS certificate and key needs to be generated with a Subject Alternative Name that **must match** the name of the Service.  This can be done using the following five openssl commands:

*Generate a Private Key for the CA*<br>
`openssl genrsa -out ca.key 2048`<br>
*Create a Self-Signed Certificate for the CA*<br>
`openssl req -x509 -new -nodes -key ca.key -subj "/CN=MutatingWebhookCA" -days 365 -out ca.crt`<br>
*Generate the Webhook Server Private Key*<br>
`openssl genrsa -out webhook-server.key 2048`<br>
*Create a Certificate Signing Request (CSR) for the Webhook Server*<br>
`openssl req -new -key webhook-server.key -subj "/CN=nodeselector-mutating-webhook-svc.nodeselector-mwh.svc" -out webhook-server.csr`<br>
*Sign the Webhook Server Certificate with the CA*<br>
`openssl x509 -req -in webhook-server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out webhook-server.crt -days 365 -extfile <(echo "subjectAltName=DNS:nodeselector-mutating-webhook-svc.nodeselector-mwh.svc")`<br>

I wrote a bash script to run the preceding five openssl commands called gencert.sh.

## Step 2: Write the Webhook Server Code

We will use a simple Python Flask server (webhook.py) to handle mutating admission requests. Here’s the Python code:

```
import json
from flask import Flask, request, jsonify
import base64

app = Flask(__name__)

@app.route('/mutate', methods=['POST'])
def mutate_pod():
    """Handles admission requests to mutate Pods."""
    try:
        admission_review = request.get_json()

        # Ensure the request is valid
        if not admission_review:
            return jsonify({"error": "Invalid request"}), 400

        # Extract the request details
        request_uid = admission_review["request"]["uid"]
        pod_name    = admission_review["request"]["object"]["metadata"]["name"]
        namespace   = admission_review["request"]["object"]["metadata"]["namespace"]

        print(f"Received request for Pod: {pod_name} in namespace: {namespace}")

        # Check if the pod name matches the desired pattern

        # Validate request payload
        if not admission_review["request"]["object"]["metadata"] or not pod_name:
            return jsonify({"error": "Invalid pod object"}), 400

        # Skip mutation if the Pod name doesn't match the pattern
        # if not pod_name.find("-main-tecsys-log"):
        #     print(f"Skipping mutation for Pod {pod_name}, as it doesn't match the name pattern.")
        #     admission_response.uid = admission_review['request']['uid']
        #     admission_response.allowed = True  # Allow the Pod creation without mutation
        #     admission_review.response = admission_response
        #     return jsonify(admission_review.to_dict())
        
        if "-main-tecsys-log" not in pod_name:
            print(f"Skipping mutation for Pod {pod_name}, as it doesn't match the name pattern.")
            # Respond without mutation
            response = {
                "response": {
                    "uid": request_uid,
                    "allowed": True
                }
            }
            return jsonify(response)

        # Patch to add nodeSelector
        patch = [
            {
                "op": "add",
                "path": "/spec/nodeSelector",
                "value": {"kubelet.kubernetes.io/role": "datadog-monitored"}
            }
       ]

        # Encode the patch to base64
        patch_base64 = base64.b64encode(json.dumps(patch).encode()).decode()

        # Prepare the admission review response
        admission_response = {
            "uid": request_uid,
            "allowed": True,
            "patchType": "JSONPatch",
            "patch": patch_base64
        }

        # Return the admission review response
        response = {
            "apiVersion": "admission.k8s.io/v1",
            "kind": "AdmissionReview",
            "response": admission_response
        }

        return jsonify(response)

    except Exception as e:
        # Log the error and return a 500 status code
        print(f"Error processing request: {str(e)}")
        return jsonify({"error": "An internal error occurred"}), 500

if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=443, ssl_context=('/tls/tls.crt', '/tls/tls.key'))
    except Exception as e:
        print(f"Error starting the webhook server: {str(e)}")
```

## Step 3: Create a Dockerfile

Packaging the webhook server shown in Step 2 as a Docker service involves creating a Docker image for the server and then deploying that image in your Kubernetes cluster.  The Docker image is created using a Dockerfile. The Dockerfile will describe how to build the Docker image from the webhook.py server code.

```
# Use the official Python image.
FROM python:3.9-slim

# Set the working directory.
WORKDIR /app

# Copy the requirements file.
COPY requirements.txt requirements.txt

# Install dependencies.
RUN pip install --no-cache-dir -r requirements.txt

# Copy the webhook server code.
COPY app/webhook.py webhook.py

# Expose port 443 for the webhook.
EXPOSE 443

# Run the webhook server.
CMD ["python", "webhook.py"]
```

## Step 4: Create a requirements.txt file

Create a requirements.txt file to include the Python dependencies for the Flask server:

```
Flask==3.0.2
jsonify
Werkzeug==3.0.3
Kubernetes
```

## Step 5: Build the Docker Image

The Docker image was built using the [https://gitlab.tecsysrd.cloud/ops/noc/noc-base-docker-images.git](https://gitlab.tecsysrd.cloud/ops/noc/noc-base-docker-images.git) repository.

## Step 6: Push the Docker Image to a Container Registry

The image was pushed to Artifactory using the [https://gitlab.tecsysrd.cloud/ops/noc/noc-base-docker-images.git](https://gitlab.tecsysrd.cloud/ops/noc/noc-base-docker-images.git) repository.

## Step 7: Deploy the Webhook Server as a Kubernetes Service

### *Create a Kubernetes NameSpace, ConfigMap, Deployment and Service Manifest for the webhook server.*

Create a namespace.yaml manifest file:

```
apiVersion: v1
kind: Namespace
metadata:
  namespace: nodeselector-mwh
```

Create a deployment.yaml manifest file:

```
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nodeselector-mutating-webhook
  namespace: nodeselector-mwh 
spec:
  replicas: 2
  selector:
    matchLabels:
      app: nodeselector-mutating-webhook
  template:
    metadata:
      labels:
        app: nodeselector-mutating-webhook
    spec:
      containers:
        - name: webhook
          image: artifactory.tecsysrd.cloud/tecsys-noc/nodeselector-mutating-webhook:v1-66a12831
          ports:
            - containerPort: 443
          volumeMounts:
            - name: tls-certs
              mountPath: /tls
              readOnly: true
          resources:
            limits:
              cpu: "500m"
              memory: "512Mi"
            requests:
              cpu: "250m"
              memory: "256Mi"
      volumes:
        - name: tls-certs
          secret:
            secretName: webhook-tls

```

Create a hpa.yaml manifest file:

```
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: nodeselector-mutating-webhook-hpa
  namespace: nodeselector-mwh 
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: nodeselector-mutating-webhook
  minReplicas: 1
  maxReplicas: 5
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80

```
Create a service.yaml manifest file:

```
apiVersion: v1
kind: Service
metadata:
  name: nodeselector-mutating-webhook-svc
  namespace: nodeselector-mwh
spec:
  ports:
    - port: 443
      targetPort: 443
  selector:
    app: nodeselector-mutating-webhook
```

## Step 8: Create a Kubernetes Secret for the TLS Certificates

Create a Kubernetes Secret to hold the TLS certificate and key:

`kubectl create secret tls webhook-tls --cert=certificates/webhook-server.crt --key=certificates/webhook-server.key -n nodeselector-mwh`

## Step 9: Apply the Deployment and Service

Deploy the K8s webhook server resources:

```
kubectl apply -f namespace.yaml
kubectl apply -f deployment.yaml
kubectl apply -f hpa.yaml
kubectl apply -f service.yaml
```
 
## Step 10: Configure the MutatingWebhookConfiguration Manifest

Create a mutatingwebhookconfiguration.yaml file:

```
apiVersion: admissionregistration.k8s.io/v1
kind: MutatingWebhookConfiguration
metadata:
  name: nodeselector-mutating-webhook
  namespace: nodeselector-mwh
webhooks:
  - name: nodeselector-mutating.k8s.io
    clientConfig:
      service:
        name: nodeselector-mutating-webhook-svc
        namespace: nodeselector-mwh
        path: "/mutate"
      caBundle: <base64-encoded-ca-cert>
    rules:
      - operations: ["CREATE"]
        apiGroups: [""]
        apiVersions: ["v1"]
        resources: ["pods"]
    failurePolicy: Ignore
    admissionReviewVersions: ["v1"]
    sideEffects: None
```

For the caBundle value, encode the CA certificate (tls.crt) created in Step 1 to base64:

`cat ca.crt | base64 | tr -d '\n'`

Replace <BASE64_ENCODED_CA_CERT> in the mutatingwebhookconfiguration.yaml file with the base64-encoded certificate.

Finally, apply the configuration:

`kubectl apply -f mutatingwebhookconfiguration.yaml`

Now, only in the namespace that matches the namespaceSelector, the webhook server should be intercepting pod creation requests and adding the specified labels dynamically.

## Testing

To check the kubectl installation run the following command:
 
```
kubectl -n nodeselector-mwh get all,cm,secret,MutatingWebhookConfiguration -o wide
```

A correct installation should show these K8s resources:
* Pod,
* ReplicaSet,
* Deployment,
* HorizontalPodAutoscaler,
* Service,
* Secret, and
* MutatingWebhookConfiguration

There are two Pod manifests in the test-pods subdirectory that will create a basic nginx in the default and nodeselector-mwh namespace.  If you describe these Pods you will see the required labels in the nginx Pod in the mutatingmh namespace.
Also, the testing can be just solely from the CLI using these kubectl commands:

```
kubectl run nginx --image=nginx
kubectl run nginx --image=nginx -n latest
kubectl run test-main-tecsys-log-xyz789 --image=nginx -n latest

kubectl describe pod nginx
kubectl -n latest describe pod nginx
kubectl -n latest describe pod test-main-tecsys-log-xyz789
kubectl -n latest get pod test-main-tecsys-log-xyz789 -o yaml
```

### List All Pods In All Namespaces Sorted By Creation Time

Check that this MutatingWebhook is not preventing new Pods from being created by running the following command:

```
kubectl get po -A --sort-by={metadata.creationTimestamp} --no-headers
```

Confirm Pods have been created after the MutatingWebhook was installed.

# Cleanup

```
kubectl delete pod nginx
kubectl -n latest delete pod nginx
kubectl -n latest delete pod test-main-tecsys-log-xyz789
```
