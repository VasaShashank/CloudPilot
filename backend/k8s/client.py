import logging
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from backend.config import NAMESPACE

logger = logging.getLogger('cloudpilot')

def get_batch_client() -> client.BatchV1Api:
    config.load_kube_config()
    return client.BatchV1Api()

def get_core_client() -> client.CoreV1Api:
    config.load_kube_config()
    return client.CoreV1Api()

def ensure_namespace(namespace: str = NAMESPACE):
    core_client = get_core_client()
    ns_body = client.V1Namespace(metadata=client.V1ObjectMeta(name=namespace))
    try:
        core_client.create_namespace(body=ns_body)
        logger.info(f"Namespace {namespace} created.")
    except ApiException as e:
        if e.status == 409:
            logger.info(f"Namespace {namespace} already exists.")
        else:
            raise
