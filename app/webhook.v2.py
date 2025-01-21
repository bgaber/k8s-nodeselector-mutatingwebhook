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

        # Extract the request details from the request body
        request_uid = admission_review["request"]["uid"]
        # pod_name    = admission_review["request"]["object"]["metadata"]["name"]
        # namespace   = admission_review["request"]["object"]["metadata"]["namespace"]
        pod_metadata = admission_review["request"]["object"]["metadata"]
        pod_name     = pod_metadata.get("name", "unnamed") # Default to "unnamed" if name is not set
        namespace    = pod_metadata.get("namespace", "default")  # Default to "default" if namespace is not set

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
