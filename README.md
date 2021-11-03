# ISSM

This is the __Intelligent slice and service manager__ component responsible for executing orchestration workflows in a context of a business transaction, such as extending a slice across a second domain in cooperation with the Network Slice and Service Orchestration.

## Pre-requisites

To install ISSM follow the installation guidelines per component following the below flow:
1. **Provision kubernetes cluster**. The guidelines are available [here](docs/kubernetes.md).
2. **Install kafka broker.** Follow the guidelines [here](docs/kafka.md).
3. **Install Argo and Argo-events**. Follow the guidelines [here](docs/argo.md).
4. **Install Datalake services**. Follow the guidelines [here](https://github.com/5GZORRO/datalake).
5. **Install NSSO**. Follow the guidelines [here](https://github.com/5GZORRO/nsso).
6. **Install SRSD**. Follow the guidelines [here](https://github.com/5GZORRO/Smart-Resource-and-Service-Discovery-application/tree/main/demo_June_21).
7. **Install ISSM-API**. Follow the guidelines [here](api).
8. **Install ISSM-O**. Follow the guidelines [here](https://github.com/5GZORRO/issm-optimizer).

ISSM is comprised of a centralized component and a local instance running at the mobile network operator (MNO) premises

![Testbed](images/issm-distributed.png)


## Deploy ISSM centralized components

Log into 5GZorro platform kuberneters master

### Create namespace

```
kubectl create namespace issm
```

### Create eventsource

Update ISSM kafka ip and port settings per your environment

```
export KAFKA_HOST=172.28.3.196
export KAFKA_PORT=9092
```

```
envsubst < deploy/kafka-sla-breach-event-source.yaml.template | kubectl apply -n issm -f -
```

### Add argo-event roles

```
kubectl apply -f deploy/install-v1.1.0.yaml
```

### Onboard SLA breach workflow

```
kubectl apply -f flows/issm-sla-breach-sensor.yaml -n issm
```

### ISSM-API service

Follow the guidelines [here](api/README.md)

## Deploy ISSM local instance

Follow the instructions in this order to deploy it in a given MNO. Repeat for every MNO you manage

Log into MNO kuberneters master

### Create MNO namespace

Assuming MNO is called `operator-a`

**Note:** ensure to define namespace with `domain-` prefix

```
kubectl create namespace domain-operator-a
```

export it

```
export MNO_NAMESPACE=domain-operator-a
```


### Add roles to MNO namespace

Run the below to add additional roles to `default` service account of the operator namespace. These roles are used by argo workflow

```
kubectl apply -f deploy/role.yaml -n $MNO_NAMESPACE
```

### Add argo-event roles to MNO namespace

```
envsubst < deploy/install-v1.1.0-operator.yaml.template | kubectl apply -f -
```

### Create Eventbus in MNO namespace

```
kubectl apply -n $MNO_NAMESPACE -f https://raw.githubusercontent.com/argoproj/argo-events/v1.1.0/examples/eventbus/native.yaml
```

### Create MNO kafka event source for ISSM bus

Update ISSM kafka ip and port settings per your environment

```
export KAFKA_HOST=172.28.3.196
export KAFKA_PORT=9092
```

**Note:** ensure to define topic with `issm-in-` prefix

```
export ISSM_DOMAIN_TOPIC=issm-in-$MNO_NAMESPACE
envsubst < deploy/kafka-event-source.yaml.template | kubectl apply -n $MNO_NAMESPACE -f -
```

Kafka topics are automatically created during the creation of the event sources


### Onboard orchestration workflow

First, customize the workflow with access information to the 5G Zorro services

Open `flows/issm-sensor.yaml`

Update access info for:

* ISSM kafka bus
* Datalake kafka bus
* Smart resource and service discovery
* Argo server ip and port

```
                arguments:
                  parameters:
                  - name: kafka_ip
                    value: 172.28.3.196
                  - name: kafka_port
                    value: 9092
                  - name: kafka_dl_ip
                    value: 172.28.3.196
                  - name: kafka_dl_port
                    value: 9092
                  - name: discovery_ip
                    value: 172.28.3.42
                  - name: discovery_port
                    value: 32000
                  - name: argo_server
                    value: 10.43.204.81:2746
```

then, onboard the flow

```
kubectl apply -f flows/issm-sensor.yaml -n $MNO_NAMESPACE
```

### Deploy common templates

Deploy common and orchestration libraries

```
kubectl apply -f wf-templates/submit.yaml -n $MNO_NAMESPACE
kubectl apply -f wf-templates/list.yaml -n $MNO_NAMESPACE
kubectl apply -f wf-templates/orchestration.yaml -n $MNO_NAMESPACE
kubectl apply -f wf-templates/base.yaml -n $MNO_NAMESPACE
kubectl apply -f wf-templates/slice.yaml -n $MNO_NAMESPACE
```

## Trigger ISSM business flow

Follow the guidelines [here](https://github.com/5GZORRO/issm/tree/master/api#api)

then watch business flow progress with Argo GUI (`http://<kubernetes master ipaddress>:2746`) running on the participated MNOs

## Licensing

This 5GZORRO component is published under Apache 2.0 license. Please see the [LICENSE](./LICENSE) file for further details.