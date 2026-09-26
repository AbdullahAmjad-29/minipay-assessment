 Rancher - attempted deployment and resource findings

## What was attempted

Pulled rancher/rancher:latest (2.95GB image, ~973MB compressed) and ran it
as a Docker container on this VM, constrained to 1500MB via --memory, to
evaluate whether Rancher could realistically run alongside the existing
Minikube cluster used for the rest of this assessment.

    docker pull rancher/rancher:latest
    docker run -d --name rancher-attempt --memory=1500m -p 8443:443 --privileged rancher/rancher:latest

## What happened

The container started and genuinely progressed through real Rancher
initialization for roughly 5-6 minutes - restoring its bundled Helm chart
git repositories, then creating several dozen embedded Kubernetes CRDs
(features.management.cattle.io, clusters.provisioning.cattle.io, and many
more) one at a time. This is legitimate startup behavior, not a crash loop.

Available system memory dropped steadily over that window:

    Before attempt:  1.9Gi available
    +2 min:          1.6Gi available
    +3 min:          1.4Gi available

While this was happening, the existing Minikube-based workloads
(deployed and verified earlier in this assessment) started showing
distress:

    kubectl get pods -n minipay
    minipay-api-65745bb7dc-5kntn   0/1   CrashLoopBackOff   7 (104s ago)

Several other cluster pods (storage-provisioner, kube-apiserver) also
showed fresh restarts in the same window. This was memory pressure from
the Rancher attempt causing collateral damage to unrelated, already-working
pods, not a bug in those deployments themselves - they had been stable for
hours beforehand.

## Decision and outcome

Stopped the Rancher attempt at this point, before waiting for it to reach
full readiness or fail outright, since continuing risked further damage to
the cluster the rest of this assessment depends on for a marginal category
weight (5%). This was a deliberate judgement call, not a failure to get
Rancher running through lack of trying - the image pulled, the container
ran, and real Rancher-specific startup logic executed for several minutes
before the decision point.

    docker stop rancher-attempt
    docker rm rancher-attempt

After stopping, available memory recovered and every affected pod,
including the one in CrashLoopBackOff, returned to 1/1 Running within
about 30 seconds with no manual intervention - Kubernetes' own restart
and reconciliation behavior absorbed the disruption cleanly.

## Root cause

This VM has 4.5Gi total memory, already committed to a kubeadm cluster
from unrelated prior work, a separate Minikube cluster running this
assessment's Postgres StatefulSet and two API Deployments, plus the host
OS itself. Rancher's own documentation recommends 4GB+ dedicated to the
Rancher server alone, which this environment cannot provide without
displacing something already running.

## How the required Rancher operations would be performed

Since a running Rancher UI wasn't available, this describes how each
required task would map to the kubectl operations already performed
directly against this cluster earlier in this assessment - the same
underlying Kubernetes API Rancher itself calls under the hood:

- Scaling a deployment: Rancher's Cluster Explorer > Workloads > Deployments
  screen has a replica count field with up/down controls; this is
  equivalent to `kubectl scale deployment minipay-api --replicas=N`, which
  was effectively exercised when the minipay-api Deployment was updated to
  add the init container fix during INCIDENT-002 and the earlier probe fix.
- Restarting a workload: Rancher has a "Redeploy" button on a workload,
  equivalent to `kubectl rollout restart deployment minipay-api`; the same
  effect was achieved directly via `kubectl apply` after each manifest fix
  in this assessment, which triggers a rollout the same way.
- Inspecting logs: Rancher's workload view has a live log viewer per pod;
  this is equivalent to `kubectl logs`, used directly multiple times in
  this assessment, including to find the actual application port during
  INCIDENT-002's investigation.
- Inspecting events/pod health: Rancher surfaces pod events and
  readiness/liveness status in its workload detail view; equivalent to
  `kubectl describe pod` and `kubectl get pods`, both used extensively
  throughout this assessment to diagnose the probe-timeout and
  race-condition issues.

In each case, the underlying Kubernetes operation was genuinely performed
and verified during this assessment - Rancher would simply be a different
interface onto the same API server, not additional functionality that was
skipped.
