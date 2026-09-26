# INCIDENT-002 - Application Unavailable After Deployment

Priority: P1

## Summary

A new release was deployed using the starter Kubernetes manifest
(kubernetes/broken-api-original.yaml, based on starter/kubernetes/broken-api.yaml
from the assessment repo). Pods started, but the application was unreachable.
Investigation found five distinct configuration defects, several of which
would independently cause this exact symptom on their own.

## Investigation

Applied the original manifest into a dedicated `minipay` namespace and checked
pod status:

    kubectl get pods -n minipay

Both replicas showed `0/1 Running` with restarts already climbing. `0/1` means
the container process was up but Kubernetes did not consider it ready to
serve traffic.

Checked why, via pod events:

    kubectl describe pod -n minipay -l app=minipay-api

This showed both the readiness probe (port 8081) and the liveness probe
(port 8080) failing with "connection refused" - meaning nothing was
listening on either port.

Checked the Service separately:

    kubectl get endpoints minipay-api -n minipay

Returned no endpoints at all - the Service had zero pods to route to,
independent of whether the pods were ready.

Since the liveness probe on port 8080 (the port declared in the container
spec itself) was also failing, that meant the container wasn't even
listening where the manifest assumed. Checked actual application logs:

    kubectl logs -n minipay -l app=minipay-api --previous

Logs showed `Uvicorn running on http://0.0.0.0:8000` - the real application
listens on 8000, not 8080 or 8081. Neither port in the manifest matched the
actual running application at all.

## Root causes

Five independent defects found in the starter manifest:

1. Service selector (`app: minipay-backend`) did not match the Deployment's
   pod labels (`app: minipay-api`). The Service had no endpoints regardless
   of pod health.
2. Readiness probe targeted port 8081, which nothing in the container
   listens on.
3. Service `targetPort` was set to 8081 as well, same problem one layer up -
   even a healthy pod would receive no traffic through the Service.
4. Container port, both probe ports, and the Service's targetPort were all
   set to 8080 or 8081, but the actual application (confirmed via logs)
   listens on 8000. Every port in the manifest was wrong relative to the
   real container, independent of whether they agreed with each other.
5. Only DB_HOST was supplied as an environment variable. The application
   also requires DB_PORT, DB_NAME, DB_USER, and DB_PASSWORD to connect to
   Postgres; without them the app would fail to reach the database even
   with networking fully corrected.

Any one of defects 1, 2/3/4 (all port-related), or 5 would independently
have caused "pods start, application unreachable" - they are not one bug
wearing different masks, they're genuinely separate mistakes that happened
to produce the same visible symptom.

## Correction

Fixed manifest: kubernetes/broken-api-fixed.yaml. Changes made:
- Container port, both probe ports, and Service targetPort all set to 8000,
  matching the real application.
- Service selector changed to app: minipay-api, matching the Deployment's
  pod labels.
- Full set of DB_* environment variables added, matching what the
  application actually requires (confirmed against the working deployment
  in kubernetes/03-api-deployment.yaml).
- DB_HOST set to postgres.default.svc.cluster.local rather than a bare
  "postgres", since the Postgres Service lives in the default namespace
  while this Deployment runs in minipay - same-name Services in different
  namespaces need the fully-qualified form to resolve.

## Validation

    kubectl apply -f kubernetes/broken-api-fixed.yaml
    kubectl get pods -n minipay -w

Both new pods reached 1/1 Running with 0 restarts; the old broken
ReplicaSet's pods terminated cleanly.

    kubectl get endpoints minipay-api -n minipay

Returned two real pod IP:port entries on 8000, confirming the selector fix.

Ran a temporary pod inside the cluster to prove actual traffic flow, not
just that endpoints existed:

    kubectl run -n minipay curl-test --image=curlimages/curl --restart=Never -- sleep 3600
    kubectl exec -n minipay curl-test -- curl -s http://minipay-api/health

Returned `{"status":"ok"}` - confirmed end to end: Service routes to a real
pod, and that pod successfully reaches Postgres.

## Preventive controls

- A CI step that lints or dry-run applies manifests (kubectl apply
  --dry-run=server) against a real test cluster before merge would have
  caught the label/selector mismatch and the invalid ports immediately,
  since dry-run still validates against the live API and existing objects.
- Probes should be tested against the actual built container image before
  the manifest is written, not assumed from a generic convention - here,
  three separate port numbers (8080, 8081, and the real 8000) were used
  across one file for what should have been a single value.
- A documented "required environment variables" list per service (e.g. in
  ARCHITECTURE.md) would make an incomplete env block like the DB_PASSWORD
  omission here obvious at review time.
- Keeping Service selectors and Deployment pod labels defined from a single
  shared value (e.g. a Kustomize base or Helm template variable) rather
  than duplicated by hand in two places would prevent them from silently
  drifting apart.
