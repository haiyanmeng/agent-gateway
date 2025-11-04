kind create cluster --config=kind-config.yaml

kubectl get --raw /.well-known/openid-configuration

kubectl run tmp-curl --image=curlimages/curl -it --rm -- sh

Inside the pod's shell, run the test:

# 1. Get secrets
TOKEN=$(cat /var/run/secrets/kubernetes.io/serviceaccount/token)
CACERT=/var/run/secrets/kubernetes.io/serviceaccount/ca.crt

# 2. Query the endpoint using the internal service name
curl --cacert $CACERT -H "Authorization: Bearer $TOKEN" \
     https://kubernetes.default.svc/.well-known/openid-configuration


kubectl run tmp-netshoot --image=nicolaka/netshoot -it --rm -- sh

Inside the pod's shell, run the command:
openssl s_client -connect $KUBERNETES_SERVICE_HOST:$KUBERNETES_SERVICE_PORT_HTTPS -servername $KUBERNETES_SERVICE_HOST </dev/null 2>/dev/null | \
  openssl x509 -noout -ext subjectAltName
