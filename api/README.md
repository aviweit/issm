# issm-api

[TODO]

## Deploy the service

Log into kuberneters master where ISSM is installed

Invoke the below in this order

**Note:**

1. you may need to update below settings according to your environment

```
export ISSM_KAFKA_HOST=172.28.3.196
export ISSM_KAFKA_PORT=9092
```

## API

### submit

Submit slice intent to ISSM kafka bus

`./kafka-console-producer.sh --topic issm-in-operator-a --bootstrap-server $ISSM_KAFKA_HOST:$ISSM_KAFKA_PORT`

```
Data payload:
    event_uuid                  - unique identifier for this request (uuid)
    service_owner               - the id of the service owner to perform this request (str)
    operation                   - the operation to perform (submit) (str)
    sub_operation               - should be set with new_intent (str)
    requested_price             - price of the resource (range e.g. "15-25") (str)
    latitude                    - the desired location of the slice/resource (str)
    longitude                   - the desired location of the slice/resource (str)
    resourceSpecCharacteristic  - the type of the resource (e.g, "CDN") (str)
    category                    - category (e.g "vnf") (str)
    qos_parameters              - (json - e.g. {"users": "10"}) (json)
    service_id                  - existing vertical service id to extend (e.g. "23") (str)

Other parameters:
    topic            - issm input topic for this service owner e.g. issm-in-operator-a
    bootstrap-server - ipaddress kafka broker.
```

Invocation example:

```
{"event_uuid": "123", "transaction_uuid": "123", "operation": "submit", "sub_operation": "new_intent", "service_owner": "operator-a", "requested_price": "15-25", "latitude": "43", "longitude": "10", "resourceSpecCharacteristic": "CDN", "category": "vnf", "qos_parameters": {"users": "10"}, "service_id": "23"}
```

### list

List business flows for a given service provider

Send the request to input topic:

`./kafka-console-producer.sh --topic issm-in-operator-a --bootstrap-server $ISSM_KAFKA_HOST:$ISSM_KAFKA_PORT`

```
Data payload:
    event_uuid       - unique identifier for this request (uuid)
    service_owner    - the id of the service owner to perform this request (str)
    operation        - the operation to perform (list) (str)

Other parameters:
    topic            - issm input topic for this service owner e.g. issm-in-operator-a
    bootstrap-server - ipaddress kafka broker.
```

Payload example:

```
{"event_uuid": "456", "operation": "list", "service_owner": "operator-a"}
```

Consume the response from output topic:

`./kafka-console-consumer.sh --topic issm-out-operator-a --from-beginning --bootstrap-server $ISSM_KAFKA_HOST:$ISSM_KAFKA_PORT`

Response example

```
{"items": [{"name": "84979a2c612d4cb2a45c48c6c7a9b8b2", "transaction_uuid": "123", "phase": "Succeeded"}, {"name": "39b2b25fea354eeb9558445e35a3aceb", "transaction_uuid": "123", "phase": "Succeeded"}, {"name": "123", "transaction_uuid": "123", "phase": "Succeeded"}], "event_uuid": "456"}
```

## Build (**relevant for developers only**)

1.  Set the `REGISTRY` environment variable to hold the name of your docker registry. The following command sets it
    equal to the docker github package repository.

    ```
    $ export REGISTRY=docker.pkg.github.com
    ```

1.  Set the `IMAGE` environment variable to hold the image.

    ```
    $ export IMAGE=$REGISTRY/5gzorro/issm/issm-api:c065565
    ```

1.  Invoke the below command.

    ```
    $ docker build --tag "$IMAGE" --force-rm=true .
    ```

1.  Push the image.

    ```
    $ docker push "$IMAGE"
    ```
