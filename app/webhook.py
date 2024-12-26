import json
from flask import Flask, request, jsonify
import base64
import logging

app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Log level: can be DEBUG, INFO, WARNING, ERROR, CRITICAL
    format='%(asctime)s - %(levelname)s - %(message)s',  # Log format
    handlers=[
        logging.StreamHandler()  # Output logs to stdout/stderr
    ]
)
logger = logging.getLogger(__name__)  # Create a logger

@app.route('/mutate', methods=['POST'])
def mutate_pod():
    """Handles admission requests to mutate Pods."""
    try:
        # Read the admission review request JSON body
        admission_review = request.get_json()

        # Ensure the request is valid
        if admission_review:
            logger.debug(f"AdmissionReview Request: {json.dumps(admission_review)}")
        else:
            logger.warning("Received an invalid request with no JSON payload.")
            return jsonify({"error": "Invalid request"}), 400

        # Extract the request details from the request body
        request_uid  = admission_review["request"]["uid"]
        pod_metadata = admission_review["request"]["object"]["metadata"]
        pod_name     = pod_metadata.get("name", "unnamed")       # Default to "unnamed" if pod name is not set
        namespace    = pod_metadata.get("namespace", "default")  # Default to "default" if namespace is not set

        logger.info(f"Received mutation request for Pod: {pod_name} in Namespace: {namespace}")

        # Check if the pod name matches the desired pattern

        # Validate request payload
        if not admission_review["request"]["object"]["metadata"] or not pod_name:
            logger.error("Invalid Pod object in the admission review request.")
            return jsonify({"error": "Invalid pod object"}), 400

        # Skip mutation if the Pod name doesn't match the pattern
        if "-main-tecsys-log" not in pod_name:
            logger.info(f"Skipping mutation for Pod {pod_name}, as it doesn't match the name pattern.")
            # Respond without mutation
            response = {
                "response": {
                    "uid": request_uid,
                    "allowed": True
                }
            }
            return jsonify(response)

        # Define the tolerations to add
        tolerations = [
            {
                "key": "kubernetes.io/role",
                "operator": "Equal",
                "value": "datadog-monitored",
                "effect": "NoSchedule"
            }
        ]

        # Patch to add nodeSelector and tolerations
        patch = [
            {
                "op": "add",
                "path": "/spec/nodeSelector",
                "value": {"kubelet.kubernetes.io/role": "datadog-monitored"}
            },
            {
                "op": "add",
                "path": "/spec/tolerations",
                "value": tolerations
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

        logger.info(f"Node Selector mutation applied to the {pod_name} Pod in the {namespace} Namespace.")
        return jsonify(response)

    except Exception as e:
        # Log the error and return a 500 status code
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({"error": "An internal error occurred"}), 500

if __name__ == '__main__':
    try:
        logger.info("Starting the webhook server...")
        app.run(host='0.0.0.0', port=443, ssl_context=('/tls/tls.crt', '/tls/tls.key'))
    except Exception as e:
        logger.critical(f"Error starting the webhook server: {str(e)}")
