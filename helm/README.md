# Overview

This document explains how to setup the standalone Helm Chart package that deploys the K8s MutatingWebhook solution using Helm templates and values file.

# Prerequisites

## [Install helm](https://helm.sh/docs/intro/install/)

Helm is a Kubernetes deployment tool for automating creation, packaging, configuration, and deployment of applications and services to Kubernetes clusters.

```
curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3
chmod 700 get_helm.sh
./get_helm.sh
which helm
helm version
```

# Helm Project Setup Background

The Helm Chart structure for this project was created using a command that is typically only executed once, per project. This command is executed at the beginning of the Helm project setup,
in order to create the correct Helm project directory structure with required manifest files.  This command is only shown below for education puproses and should not be run if using the cloned repository.

**IMPORTANT: DO NOT RUN THIS COMMAND ON THE CLONED REPO BECAUSE IT WILL OVERWRITE ALL MANIFEST FILES WITH DEFAULT VERSIONS**

```
helm create k8s-nodeselector-mutatingwebhook
```

# Validation of Helm Templates and Values

After running the previous command, the Chart.yaml, values.yaml and other manifest files in the /templates directory were modified for this project.

Those K8s manifests files in the /templates directory can be validated using the following command:

```
helm template k8s-nodeselector-mutatingwebhook --debug
```

# Installation

The K8s MutatingWebhook resources can be installed with the following Helm Chart command:

```
helm install k8s-nodeselector-mutatingwebhook k8s-nodeselector-mutatingwebhook
```

# Upgrade

If a manifest file changes, perhaps the number of replicas in the deployment or the values in a ConfigMap then an upgrade needs to be performed.  The K8s MutatingWebhook resources can be upgraded with the following Helm Chart command:

```
helm upgrade k8s-nodeselector-mutatingwebhook k8s-nodeselector-mutatingwebhook
```

# Testing

To check the helm installation run the following command:
 
```
kubectl -n nodeselector-mwh get all,cm,secret,MutatingWebhookConfiguration,hpa -o wide
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
Also, the testing can be performed just from the CLI using these kubectl commands:

```
kubectl run nginx --image=nginx
kubectl run nginx --image=nginx -n latest
kubectl run test-main-tecsys-log-xyz789 --image=nginx -n latest
kubectl run test-main-tecsys-log-xyz789 --image=nginx -n latest --dry-run=server -o yaml

kubectl describe pod nginx
kubectl -n latest describe pod nginx
kubectl -n latest describe pod test-main-tecsys-log-xyz789
kubectl -n latest get pod test-main-tecsys-log-xyz789 -o yaml
```

## List All Pods In All Namespaces Sorted By Creation Time

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

# Problem Troubleshooting

## Service and DNS Configuration

The webhook relies on the Kubernetes DNS service to resolve the service name (nodeselector-mutating-webhook-svc.nodeselector-mwh.svc). If DNS is not properly configured or delayed, the webhook request might time out.

### Solutions

Verify that the service is reachable:

```
kubectl run test --rm -it --image=busybox -- /bin/sh
nslookup nodeselector-mutating-webhook-svc.nodeselector-mwh.svc
```

or

```
kubectl run test --rm -it --image=busybox -- /bin/sh
nslookup nodeselector-mutating-webhook-svc.nodeselector-mwh.svc.cluster.local
```

If the DNS resolution fails, check the kube-dns or coredns deployment.

## Network Policies or Admission Control

If your cluster uses network policies, admission controllers, or other security mechanisms, they might block communication between the API server and the webhook.

### Solutions

Ensure network policies allow traffic between the API server and the webhook service.

Test connectivity

```
kubectl run test --rm -it --image=busybox -- /bin/sh
wget https://nodeselector-mutating-webhook-svc.nodeselector-mwh.svc:443/mutate --no-check-certificate
```

or

```
kubectl run test --rm -it --image=busybox -- /bin/sh
wget https://nodeselector-mutating-webhook-svc.nodeselector-mwh.svc.cluster.local:443/mutate --no-check-certificate
```

Review the kube-apiserver logs for errors related to webhook communication.

## Debugging Steps

1. Check the logs of the running webhook pod

```
kubectl logs <webhook-pod-name>
```

2. Look for specific Python stack traces or timeout messages.

3. Increase logging verbosity for kube-apiserver and look for webhook-related errors.

# Uninstallation

All the K8s MutatingWebhook resources are uninstalled with the following Helm Chart command:

```
helm uninstall k8s-nodeselector-mutatingwebhook
```