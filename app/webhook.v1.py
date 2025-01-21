from flask import Flask, request, jsonify
import json
from kubernetes.admission import AdmissionReview, AdmissionResponse

app = Flask(__name__)

@app.route('/mutate', methods=['POST'])
def mutate_pod():
    """Handles admission requests to mutate Pods."""
    try:
        admission_review_request = request.get_json()

        # Ensure the request is valid
        if not admission_review_request:
            return jsonify({"error": "Invalid request"}), 400

        admission_review = AdmissionReview(admission_review_request)
        request_object = admission_review.request.object

        # Validate request payload
        if not request_object or not request_object.metadata or not request_object.metadata.name:
            return jsonify({"error": "Invalid pod object"}), 400

        pod_name = request_object.metadata.name
        namespace = request_object.metadata.namespace
        print(f"Received request for Pod: {pod_name} in namespace: {namespace}")

        # Skip mutation if the Pod name doesn't match the pattern
        if not pod_name.find("-main-tecsys-log"):
            print(f"Skipping mutation for Pod {pod_name}, as it doesn't match the name pattern.")
            admission_response = AdmissionResponse(uid=admission_review.request.uid)
            admission_response.allowed = True  # Allow the Pod creation without mutation
            admission_review.response = admission_response
            return jsonify(admission_review.to_dict())

        # Patch to add nodeSelector
        node_selector_patch = {
            "op": "add",
            "path": "/spec/nodeSelector",
            "value": {"kubelet.kubernetes.io/role": "datadog-monitored"}
        }

        # Create response
        response = AdmissionResponse(uid=admission_review.request.uid)
        response.allowed = True
        response.patch = json.dumps([node_selector_patch])
        response.patchType = "JSONPatch"

        # Attach response to AdmissionReview
        admission_review.response = response
        return jsonify(admission_review.to_dict())

    except Exception as e:
        # Log the error and return a 500 status code
        print(f"Error processing request: {str(e)}")
        return jsonify({"error": "An internal error occurred"}), 500

if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=443, ssl_context=('/tls/tls.crt', '/tls/tls.key'))
    except Exception as e:
        print(f"Error starting the webhook server: {str(e)}")
