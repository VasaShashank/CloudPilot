from kubernetes import client, config

def _load_k8s_config():
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()

def get_batch_client() -> client.BatchV1Api:
    _load_k8s_config()
    return client.BatchV1Api()

def get_core_client() -> client.CoreV1Api:
    _load_k8s_config()
    return client.CoreV1Api()
