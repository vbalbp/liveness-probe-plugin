import requests
import re
from ruxit.api.base_plugin import RemoteBasePlugin
import logging

logger = logging.getLogger(__name__)
GROUP_NAME = "WebChecks"

class WebcheckPluginRemote(RemoteBasePlugin):

    def initialize(self, **kwargs):
        logger.info("Config: %s", self.config)
        self.url = self.config["url"]
        self.timeout = self.config["timeout"]
        self.expected_code = self.config["code"]
        self.expected_body = self.config["response"]
        self.name = self.config["name"]
        self.proxy = self.config["proxy"]
        self.entity_id = self.config["entityid"]


    def query(self, **kwargs):
        group = self.topology_builder.create_group(GROUP_NAME, GROUP_NAME)
        device_name = self.name
        device = group.create_device(device_name, device_name)
        try:
          if self.proxy == '':
            webcheck = requests.get(self.url, timeout=self.timeout, verify=False)
          else:
            proxy_dict = {"http": self.proxy}
            webcheck = requests.get(self.url, timeout=self.timeout, proxies=proxy_dict, verify=False)
          state = self.process_result(webcheck, device)
        except requests.exceptions.Timeout:
          state = 0
          self.problem_description = "Timeout of " + str(self.timeout) + " seconds reached."
          self.push_error(device=device)
        except requests.exceptions.RequestException as e:
          state = 0
          self.problem_description = "Unknown error received: " + e
          self.push_error(device=device)          
        device.absolute(key='availability', value=state)
        

    def process_result(self, webcheck, device, **kwargs):
        '''
        When a response is correctly received by the GET request,
        process it to send data to Dynatrace
        '''
        code = str(webcheck.status_code)
        body = webcheck.text
        response_time = webcheck.elapsed.total_seconds()*1000

        code_result = re.search(self.expected_code, code)
        body_result = re.search(self.expected_body, body)

        if code_result == None:
          state = 0
          self.problem_description = "HTTP response code " + code + " does not match code regex."
          self.push_error(device=device)
        elif body_result == None:
          state = 0
          self.problem_description = "Response body regex check failed."
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
          requests.post("https://hyf63039.sprint.dynatracelabs.com/api/v1/events?Api-Token=ZCIW4Vr2SvaykDKXENQM9", json=request_body, headers=headers)
