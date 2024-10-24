#!/bin/env python

# Standard library imports
import logging
import json
# Third-party imports
from tabulate import tabulate

# Needed for aetest script
from pyats import aetest
from pyats.log.utils import banner

# Genie Imports
from genie.conf import Genie
from genie.abstract import Lookup
# Import the genie libs
from genie.libs import ops  # noqa

# Configure logger for the script
log = logging.getLogger(__name__)


###################################################################
#                      COMMON SETUP SECTION                       #
###################################################################

class CommonSetup(aetest.CommonSetup):  # Revised: Class name updated to follow PEP8
    """Common Setup section."""

    @aetest.subsection
    def connect(self, testbed):
        """Establish connection to devices in the testbed."""  # Revised: Improved docstring
        genie_testbed = Genie.init(testbed)
        self.parent.parameters['testbed'] = genie_testbed
        device_list = []

        for device in genie_testbed.devices.values():
            log.info(banner(f"Connecting to device '{device.name}'"))  # Revised: Used f-strings for better readability
            try:
                device.connect()
                device_list.append(device)  # Revised: Device only appended on successful connection
            except Exception as e:  # Revised: Captured the exception
                self.failed(f"Failed to establish connection to '{device.name}': {str(e)}")  # Revised: Added error message with exception details
        
        # Pass list of connected devices to testcases
        self.parent.parameters['devices'] = device_list  # Revised: Changed from 'dev' to 'devices' for clarity


###################################################################
#                      TESTCASES SECTION                          #
###################################################################

class BGPNeighborsEstablished(aetest.Testcase):  # Revised: Class name updated to follow PEP8
    """Test case to verify BGP neighbors are established."""

    @aetest.test
    def learn_bgp(self):
        """Learn BGP information from devices."""  # Revised: Improved docstring
        self.all_bgp_sessions = {}

        for device in self.parent.parameters['devices']:  # Revised: Updated parameter to 'devices'
            log.info(banner(f"Gathering BGP Information from {device.name}"))  # Revised: Used f-string
            abstract = Lookup.from_device(device)
            bgp = abstract.ops.bgp.bgp.Bgp(device)
            bgp.learn()

            if hasattr(bgp, 'info'):
                self.all_bgp_sessions[device.name] = bgp.info
            else:
                self.failed(f"Failed to learn BGP info from device {device.name}", goto=['common_cleanup'])  # Revised: Improved failure message

    @aetest.test
    def check_bgp(self):
        """Check the state of BGP neighbors."""  # Revised: Improved docstring
        failed_dict = {}
        results_table = []  # Revised: Changed 'mega_tabular' to 'results_table' for clarity

        for device, bgp_info in self.all_bgp_sessions.items():
            vrfs_dict = bgp_info.get('instance', {}).get('default', {}).get('vrf', {})  # Revised: Used .get() to avoid KeyError

            for vrf_name, vrf_data in vrfs_dict.items():
                neighbors = vrf_data.get('neighbor', {})  # Revised: Used .get() for safety

                for nbr, props in neighbors.items():
                    state = props.get('session_state', 'Unknown').lower()  # Revised: Default to 'Unknown' if session_state is not available
                    result = 'Passed' if state == 'established' else 'Failed'  # Revised: Cleaner conditional assignment

                    # Track failed cases
                    if result == 'Failed':
                        failed_dict.setdefault(device, {})[nbr] = props  # Revised: Using setdefault for efficient failure tracking

                    # Build the table row
                    results_table.append([vrf_name, nbr, state.capitalize(), result])  # Revised: Changed variable name to be more descriptive

            # Log the results table per device
            log.info(f"Device {device} BGP Neighbors:\n")  # Revised: Used f-string
            log.info(tabulate(results_table, headers=['VRF', 'Peer', 'State', 'Result'], tablefmt='orgtbl'))  # Revised: Improved readability

        if failed_dict:
            log.error(json.dumps(failed_dict, indent=3))  # Revised: Cleaner error output
            self.failed("Some BGP neighbors are not established.")
        else:
            self.passed("All BGP neighbors are established.")


###################################################################
#                      COMMON CLEANUP SECTION                     #
###################################################################

class CommonCleanup(aetest.CommonCleanup):  # Revised: Class name updated to follow PEP8
    """Common Cleanup section."""

    @aetest.subsection
    def clean_up(self):
        """Perform common cleanup actions."""  # Revised: Changed method name to be more descriptive
        log.info("Aetest Common Cleanup")


if __name__ == '__main__':  # pragma: no cover
    aetest.main()