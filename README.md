# Liveness Probe
## ActiveGate plugin for Dynatrace
###### Author: Víctor Balbuena Pantigas


This is an ActiveGate plugin developed as an add-on for the software Dynatrace. Its purpose is to be able to check if external resources that accept connections, let it be HTTP or TCP, are up and accepting connections or are unavailable, pushing problems into Dynatrace when needed.

In order to be used, you need first to change the code in `liveness_probe_activegate_plugin.py`, and add a correct value to `API_ENDPOINT` and `API_TOKEN`, corresponding to your environment. Make sure to have the source files already changed available in your ActiveGate. Once this is done, download the `plugin_sdk` tool from Dynatrace Settings, under Add a new Technology Monitoring, and install it in your ActiveGate. Run plugin_sdk build_plugin -t API_TOKEN and the plugin will be uploaded to that ActiveGate and will be configurable from Dynatrace Settings.

## Release notes

###### v1.0.0
Official release
- HTTP Connection available
- TCP Connection available
- Multiple configuration parameters added
- Push an error to another service feature added
- Different error messages caught, shown on problem view
