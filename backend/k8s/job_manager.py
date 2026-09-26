import logging
from kubernetes import client
from kubernetes.client.rest import ApiException
from backend.config import NAMESPACE
from backend.k8s.client import get_batch_client, get_core_client, ensure_namespace

logger = logging.getLogger('cloudpilot')

class JobManager:
    def __init__(self):
        self.batch_client = get_batch_client()
        self.core_client = get_core_client()
        ensure_namespace()

    def create_job(self, job: client.V1Job) -> str:
        try:
            resp = self.batch_client.create_namespaced_job(namespace=NAMESPACE, body=job)
            return resp.metadata.name
        except ApiException as e:
            logger.error(f"Error creating job: {e}")
            raise

    def get_job_status(self, job_name: str) -> dict:
        try:
            job = self.batch_client.read_namespaced_job(name=job_name, namespace=NAMESPACE)
            status = job.status
            return {
                "active": status.active,
                "succeeded": status.succeeded,
                "failed": status.failed
            }
        except ApiException as e:
            logger.error(f"Error getting job status for {job_name}: {e}")
            raise

    def is_job_complete(self, job_name: str) -> bool:
        status = self.get_job_status(job_name)
        return (status["succeeded"] or 0) >= 1

    def is_job_failed(self, job_name: str) -> bool:
        status = self.get_job_status(job_name)
        return (status["failed"] or 0) >= 1

    def get_job_logs(self, job_name: str) -> str:
        try:
            pods = self.core_client.list_namespaced_pod(
                namespace=NAMESPACE, 
                label_selector=f"job-name={job_name}"
            )
            if not pods.items:
                return f"No pods found for job {job_name}"
            pod_name = pods.items[0].metadata.name
            logs = self.core_client.read_namespaced_pod_log(name=pod_name, namespace=NAMESPACE)
            return logs
        except ApiException as e:
            logger.error(f"Error getting logs for job {job_name}: {e}")
            return f"Error getting logs: {str(e)}"

    def delete_job(self, job_name: str, propagation_policy: str = 'Background'):
        try:
            self.batch_client.delete_namespaced_job(
                name=job_name,
                namespace=NAMESPACE,
                propagation_policy=propagation_policy
            )
        except ApiException as e:
            if e.status != 404:
                logger.error(f"Error deleting job {job_name}: {e}")
                raise

    def delete_workflow_jobs(self, workflow_id: str):
        try:
            jobs = self.batch_client.list_namespaced_job(
                namespace=NAMESPACE,
                label_selector=f"cloudpilot/workflow={workflow_id[:8]}"
            )
            for job in jobs.items:
                self.delete_job(job.metadata.name)
        except ApiException as e:
            logger.error(f"Error deleting workflow jobs for {workflow_id}: {e}")
            raise
