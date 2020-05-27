'''
Code for the Liveness Probe Plugin extension for Dynatrace's environment ActiveGates.
From the ActiveGate, use HTTP or TCP to connect to an external endpoint and determine if it's available or not.
Make sure to change the ``API_ENDPOINT`` and ``API_TOKEN`` to the values of your environment
(Check https://www.dynatrace.com/support/help/dynatrace-api/environment-api/events/post-event/ for more information about the called endpoint)
'''

import logging
import re
import requests
import socket
import time

from ruxit.api.base_plugin import RemoteBasePlugin

logger = logging.getLogger(__name__)
GROUP_NAME = "Liveness Probe"
API_ENDPOINT = "https://{your-domain}/e/{your-environment}/api/v1/events"
API_TOKEN = "xxxxxxxxxxxxxxxxxxxxx"

class LivenessProbePluginRemote(RemoteBasePlugin):

    def initialize(self, **kwargs):
        '''
        Pass on configuration parameters to the class.
        '''
        logger.info("Config: %s", self.config)
        self.url = self.config["url"]
        self.timeout = self.config["timeout"]
        self.expected_code = self.config["code"]
        self.expected_body = self.config["response"]
        self.name = self.config["name"]
        self.proxy = self.config["proxy"]
        self.entity_id = self.config["entityid"]
        self.connection_type = self.config["type"]


    def query(self, **kwargs):
        '''
        Method present in RemoteBasePlugin as abstract, overwritten in the plugin.
        Called each and every execution of the plugin.
        '''
        group = self.topology_builder.create_group(GROUP_NAME, GROUP_NAME)
        device_name = self.name
        device = group.create_device(device_name, device_name)
        if self.connection_type == 'HTTP':
          state = self.http_query(device)
        elif self.connection_type == 'TCP':
          state = self.tcp_query(device)
        device.absolute(key='availability', value=state)


    def tcp_query(self, device, **kwargs):
        '''
        Establish a TCP connection and determine if it works or not.

        Parameters:
          device(ruxit.api.topology_builder.MetricSink): Dynatrace defined object used for creating a technology.

        Returns:
          state (int): 0 (unavailable) or 1 (available). 
        '''
        tcp_url = self.url.split(':')[0]
        tcp_port = int(self.url.split(':')[1])
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
          s.connect((tcp_url,tcp_port))
          time.sleep(self.timeout)
          state = 1
          s.close()
        except:
          state = 0
          self.problem_description = "TCP Connection unsuccessful"
          self.push_error(device=device)
        return state      


    def http_query(self, device, **kwargs):
        '''
        EStablish an HTTP connection and determine if it works or not, also based onthe configuration of the endpoint.

        Parameters:
          device(ruxit.api.topology_builder.MetricSink): Dynatrace defined object used for creating a technology.

        Returns:
          state (int): 0 (unavailable) or 1 (available). 
        '''
        try:
          if self.proxy == '':
            webcheck = requests.get(self.url, timeout=self.timeout, verify=False)
          else:
            proxy_dict = {"http": self.proxy, "https": self.proxy}
            webcheck = requests.get(self.url, timeout=self.timeout, proxies=proxy_dict, verify=False)
          state = self.process_result(webcheck, device)
        except requests.exceptions.ConnectionError:
          state = 0
          self.problem_description = "Connection error"
          self.push_error(device=device)
        except requests.exceptions.Timeout:
          state = 0
          self.problem_description = "Timeout of " + str(self.timeout) + " seconds reached."
          self.push_error(device=device)
        except requests.exceptions.RequestException as e:
          state = 0
          self.problem_description = "Unknown error received: " + e
          self.push_error(device=device)
        return state


    def process_result(self, webcheck, device, **kwargs):
        '''
        When a response is correctly received by the GET request,
        process it to send data to Dynatrace.

        Parameters:
          webcheck(requests.Response): The response from the HTTP request containing code and body.
          device(ruxit.api.topology_builder.MetricSink): Dynatrace defined object used for creating a technology.

        Returns:
          state (int): 0 (unavailable) or 1 (available). 
        '''
        code = str(webcheck.status_code)
        body = webcheck.text
        response_time = webcheck.elapsed.total_seconds()*1000

        code_result = re.search(self.expected_code, code)
        body_result = re.search(self.expected_body, body)

        if code_result == None:
          state = 0
          self.problem_description = "HTTP response code " + code + " does not match code regex: " + self.expected_code + " ."
          self.push_error(device=device)
        elif body_result == None:
          state = 0
          self.problem_description = "Response body regex " + self.expected_body + " does not match response's body.\n" + body
          self.push_error(device=device)
        else:
          state = 1
        device.absolute(key='responsetime', value=response_time)
        return state


    def push_error(self, device, **kwargs):
        '''
        Creates a custom info event for the failing webcheck
        and also pushes an availability problem to the entity
        specified in the configuration through the Dynatrace API.

        Parameters:
          device(ruxit.api.topology_builder.MetricSink): Dynatrace defined object used for creating a technology.
        '''
        device.report_custom_info_event(title = "Webcheck " + self.name + " is failing")
        if self.entity_id != '':
          request_body = {
            "eventType": "AVAILABILITY_EVENT",
            "timeoutMinutes": 5,
            "attachRules": {
              "entityIds": [
                 self.entity_id
              ]
            },
            "source": self.name,
            "description": self.problem_description
          }
          headers = {"accept": "application/json", "Content-Type": "application/json"}
          requests.post(API_ENDPOINT + "?Api-Token=" + API_TOKEN, json=request_body, headers=headers)
