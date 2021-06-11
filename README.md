# ISSM (Intelligent slice and service manager)

**Note: This is a work in progress. Ensure to monitor this repository frequently**

ISSM runs on kubernetes. You can use [these instructions](https://github.com/5GZORRO/infrastructure/blob/master/docs/kubernetes.md) to provision such a one

## Pre-requisites

* ISSM requires kafka broker. You can use [these instructions](https://github.com/5GZORRO/infrastructure/blob/master/docs/kafka.md) to provision such a one
* Install argo and argo-events per [these instructions](docs/argo.md)
* Install vertical slicer per [these instructions](docs/slicer.md)
* Install datalake services per [these instructions](docs/datalake.md)
* Install discovery application per [these instructions](https://github.com/5GZORRO/Smart-Resource-and-Service-Discovery-application/blob/main/readme.txt)
* Install optimizer service per [these instructions](https://github.com/5GZORRO/issm-optimizer/blob/master/README.md)

## Deploy

Log into kuberneters master

### Set ISSM role

```
kubectl create -n argo-events -f deploy/role.yaml
```

### Create ISSM kafka event source

Update ISSM kafka ip and port settings per your environment

```
export KAFKA_HOST=172.28.3.196
export KAFKA_PORT=9092
```

```
envsubst < deploy/kafka-event-source.yaml.template | kubectl create -n argo-events -f -
```

**Note:** Kafka `issm-topic` is automatically created during the creation of the event-source

### Apply docker-secrete.yaml

Create docker-secrete.yaml file [these instructions](https://github.com/5GZORRO/infrastructure/blob/master/docs/kubernetes-private-dockerregistry.md) and apply it

```
kubectl apply -f docker-secrete.yaml -n argo-events
```

## Onboard ISSM flow

You may need to customize the flow definition with access information to the 5G Zorro services

Open `flows/issm-sensor.yaml`

Update access info for:

* ISSM kafka bus
* Discovery service
* Vertical slicer service

```
                arguments:
                  parameters:
                  - name: kafka_ip
                    value: 172.28.3.196
                  - name: kafka_port
                    value: 9092
                  - name: discovery_ip
                    value: 172.15.0.180
                  - name: discovery_port
                    value: 80
                  - name: slicer_ip
                    value: 172.28.3.42
                  - name: slicer_port
                    value: 31082
```

Onboard the flow

```
kubectl apply -f flows/issm-sensor.yaml -n argo-events
```

## Deploy common template libraries

```
kubectl create -f wf-templates/base.yaml -n argo-events
kubectl create -f wf-templates/slice.yaml -n argo-events
```

## Trigger ISSM business flow

**Important:**
* the offers loaded into discovery application are of `VideoStreaming`, hence, ensure to [pre-onboard the corresponding blueprint](./scripts/slicer/onboard.md) into the vertical slicer.
* service owner (i.e mno/tenant) should be pre-defined along with SLA, hence ensure to [create it](./scripts/slicer/define_tenant.md) in the vertical slicer.
* service owner (i.e mno/tenant) should pre-exist in datalake, hence ensure to [create it](docs/datalake.md#create-user) passing `operator-a` as parameter

### Manual steps

>{"event_uuid": "1234", "transaction_uuid": "123", "operation": "submit_intent", "offered_price": "1700", "latitude": "56", "longitude": "5", "slice_segment": "edge", "category": "VideoStreaming", "qos_parameters": {"bandwidth": "30"}, "service_owner": "operator-a"}

The flow is invoked automatically

## Watch flow progress using Argo GUI

Browse to `http://<kubernetes master ipaddress>:2746`
