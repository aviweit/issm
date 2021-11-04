# Copyright 2020 - 2021 IBM Corporation

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

# http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import flask
import json
import os
import requests
import sys
import uuid

from gevent.wsgi import WSGIServer
from werkzeug.exceptions import HTTPException

import kubernetes
from kubernetes.client.rest import ApiException

from kafka import KafkaProducer
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import KafkaError, TopicAlreadyExistsError


KAFKA_API_VERSION = (0, 10, 1)
KAFKA_TIMEOUT = 10  # seconds


KAFKA_IP = os.getenv('ISSM_KAFKA_HOST')
KAFKA_PORT = os.getenv('ISSM_KAFKA_PORT', 9092)

if not KAFKA_IP:
    print ('ISSM_KAFKA_HOST not set')
    raise sys.exit(1)

ARGO_SERVER = os.getenv('ARGO_SERVER')

if not ARGO_SERVER:
    print ('ARGO_SERVER not set')
    raise sys.exit(1)



def publish_intent(kafka_ip, kafka_port, topic, payload):
    """
    Send the intent to the ISSM kafka bus

    :param kafka_ip: kafka broker ipaddress
    :type kafka_ip: ``str``

    :param kafka_port: kafka broker port
    :type kafka_port: ``int``

    :param payload: the payload (intent) to send
    :type payload: ``dict``
    """
    producer = KafkaProducer(bootstrap_servers="%s:%s" % (kafka_ip, kafka_port),
                             api_version=KAFKA_API_VERSION,
                             value_serializer=lambda v: json.dumps(v).encode('utf-8'))

    print('[INTENT] %s' % payload)
    t = producer.send(topic, payload)

    # Block for 'synchronous' send; set timeout on X seconds
    try:
        t.get(timeout=KAFKA_TIMEOUT)
    except KafkaError as ke:
        print('[ERROR] KafkaError: %s' % str(ke))
        raise ke
    finally:
        producer.close()


class Proxy:
    def __init__(self):
        """
        Initialize with the in-cluster configuration and the required
        APIs
        """
#         kubernetes.config.load_incluster_config()
#         self.api = kubernetes.client.CustomObjectsApi()
#         self.core_api = kubernetes.client.CoreV1Api()
        sys.stdout.write('ISSM-API initialized\n')

    def instantiate(self, service_owner, operation, intent):
        """
        Instantiate ISSM flow with the given intent on-behalf of the service_owner.

        :param service_owner: the name of the service owner e.g. tenant name.
        :type service_owner: ``str``

        :param operation: the operation for this flow. Currently
                          'submit_intent' is supported
        :type operation: ``str``

        :param intent: intent payload e.g. slice creation intent
        :type intent: ``dict``
        """
        event_uuid = str(uuid.uuid4()).replace('-','')
        print ('** event_uuid: %s' % event_uuid)

        payload = dict(event_uuid=event_uuid, transaction_uuid=event_uuid,
                       service_owner=service_owner,
                       operation=operation, sub_operation='new_intent')
        payload['callback'] = dict(type='kafka', kafka_topic=service_owner)
        payload.update(intent)
        publish_intent(KAFKA_IP, KAFKA_PORT,
                       topic='issm-in-%s' % service_owner, payload=payload)
        return {'transaction_uuid': event_uuid}

    def get_workflows(self, service_owner):
        """
        Retrieve list of business workflows for the given service owner (i.e. namespace)
        passing a predefined query.
        """
        query_str = "fields=items.metadata.name,items.metadata.creationTimestamp,"\
        "items.metadata.labels.transaction_uuid,items.status.phase&"\
        "listOptions.labelSelector=operation=submit"

        headers = {'Content-Type': 'application/json'}
        r = requests.get("http://%(argo_server)s/api/v1/workflows/%(namespace)s?%(query)s" %
                        {
                           "argo_server": ARGO_SERVER,
                           "namespace": "domain-"+service_owner,
                           "query": query_str
                        }, headers=headers)

        return r.json()

    def get_workflow_ref(self, argo_url, service_owner, transaction_uuid):
        """
        Retrieve list of business workflows for the given service owner (i.e. namespace)
        passing a predefined query.
        """
        query_str = "fields=items.metadata.name,items.metadata.creationTimestamp,"\
        "items.metadata.labels.transaction_uuid,items.status.phase&"\
        "listOptions.labelSelector=transaction_uuid=%s" % transaction_uuid

        #headers = {'Content-Type': 'application/json'}
        # transaction spans namespaces
        #r = requests.get("http://%(argo_server)s/api/v1/workflows?%(query)s" %
        #                {
        #                   "argo_server": ARGO_SERVER,
        #                   "namespace": "domain-"+service_owner,
        #                   "query": query_str
        #                }, headers=headers)

        #return r.json()
        return {
            'ref': 'http://%(argo_server)s/workflows/?label=transaction_uuid=%(transaction_uuid)s' %
                {
                    'argo_server': argo_url, 
                    'transaction_uuid': transaction_uuid
                }
        }

proxy = flask.Flask(__name__)
proxy.debug = True
server = None

proxy_server = None


def setServer(s):
    global server
    server = s


def setProxy(p):
    global proxy_server
    proxy_server = p


def getMessagePayload():
    message = flask.request.get_json(force=True, silent=True)
    if message and not isinstance(message, dict):
        flask.abort(400, 'message payload is not a dictionary')
    else:
        value = message if (message or message == {}) else {}
    if not isinstance(value, dict):
        flask.abort(400, 'message payload did not provide binding for "value"')
    return value


@proxy.route("/hello")
def hello():
    sys.stdout.write ('Enter /hello\n')
    return ("Greetings from the ISSM-API server! ")


@proxy.route("/instantiate/<service_owner>",  methods=['POST'])
def instantiate(service_owner):
    sys.stdout.write('Received flow instantiate request for [%s] \n' % service_owner)
    try:
        value = getMessagePayload()

        operation='submit'
        intent = value
        response = flask.jsonify(
            proxy_server.instantiate(
                service_owner=service_owner, operation=operation,
                intent=intent))

        response.status_code = 200
        return response

    except Exception as e:
        response = flask.jsonify({'error': 'Internal error. {}'.format(e)})
        response.status_code = 500

    sys.stdout.write('Exit /instantiate %s\n' % str(response))
    return response


@proxy.route("/get_workflows/<service_owner>",  methods=['GET'])
def get_workflows(service_owner):
    try:
        flow_json = proxy_server.get_workflows(service_owner)
        response = flask.jsonify(flow_json)
        response.status_code = 200
        return response
    except HTTPException as e:
        return e
    except Exception as e:
        response = flask.jsonify({'error': 'Internal error. {}'.format(e)})
        response.status_code = 500
        return response

@proxy.route("/get_workflow_ref/<service_owner>/<transaction_uuid>",  methods=['POST'])
def get_workflow_ref(service_owner, transaction_uuid):
    try:
        value = getMessagePayload()
        argo_url = value.get('argo-server-url', '')
        flow_json = proxy_server.get_workflow_ref(argo_url, service_owner, transaction_uuid)
        response = flask.jsonify(flow_json)
        response.status_code = 200
        return response
    except HTTPException as e:
        return e
    except Exception as e:
        response = flask.jsonify({'error': 'Internal error. {}'.format(e)})
        response.status_code = 500
        return response

def main():
    port = int(os.getenv('LISTEN_PORT', 8080))
    server = WSGIServer(('0.0.0.0', port), proxy, log=None)
    setServer(server)
    print ('\n\n-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-')
    print ("Starting ISSM-API .. ready to serve requests on PORT: %s..\n\n"
           "KAFKA_SERVER '%s:%s' "
           "KAFKA_API_VERSION '%s' " %
           (int(port), KAFKA_IP, str(KAFKA_PORT), KAFKA_API_VERSION))
    print ('-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-\n\n')
    
    server.serve_forever()


if __name__ == '__main__':
    setProxy(Proxy())
    main()
