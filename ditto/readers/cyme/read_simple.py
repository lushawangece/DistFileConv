# -*- coding: utf-8 -*-

import logging
import math
import cmath
import os
from functools import reduce
from six import string_types

import numpy as np

# Ditto imports
from ditto.readers.abstract_reader import AbstractReader
from ditto.store import Store
from ditto.models.position import Position
from ditto.models.node import Node
from ditto.models.line import Line
from ditto.models.load import Load
from ditto.models.phase_load import PhaseLoad
from ditto.models.regulator import Regulator
from ditto.models.wire import Wire
from ditto.models.capacitor import Capacitor
from ditto.models.phase_capacitor import PhaseCapacitor
from ditto.models.powertransformer import PowerTransformer
from ditto.models.power_source import PowerSource
from ditto.models.winding import Winding
from ditto.models.phase_winding import PhaseWinding
from ditto.models.feeder_metadata import Feeder_metadata
from ditto.models.photovoltaic import Photovoltaic
from ditto.models.storage import Storage
from ditto.models.phase_storage import PhaseStorage

from ditto.models.base import Unicode
from ditto.modify.system_structure import system_structure_modifier

logger = logging.getLogger(__name__)


class Reader(AbstractReader):
    """
    CYME-->DiTTo Reader class

    Author: Nicolas Gensollen. October 2017

    .. note::

        Different versions of CYME might have different header names for the same object.
        The reader class has a mapping between the objects and the header names with the default mapping being for CYME version XXX (see table below).
        When using another version of CYME, make sure to modify this mapping to have something consistent:

        >>> my_reader.update_header_mapping(modifications)

        Here, modification is a dictionary {object: header} of updates to apply to the default mapping.


    **Default header mapping:**

    +-------------------------------------------+--------------------------------------------+
    |                      Object               |                      Header                |
    +===========================================+============================================+
    |                                       NODE PARSER                                      |
    +-------------------------------------------+--------------------------------------------+
    |                      'node'               |                     '[NODE]'               |
    |                'node_connector'           |                '[NODE CONNECTOR]'          |
    +-------------------------------------------+--------------------------------------------+
    |                                       LINE PARSER                                      |
    +-------------------------------------------+--------------------------------------------+
    |     'overhead_unbalanced_line_settings'   |      '[OVERHEADLINEUNBALANCED SETTING]'    |
    +-----------------read.py--------------------------+--------------------------------------------+
    |            'overhead_line_settings'       |            '[OVERHEADLINE SETTING]'        |
    +-------------------------------------------+--------------------------------------------+
    |          'overhead_byphase_settings'      |            '[OVERHEAD BYPHASE SETTING]'    |
    +-------------------------------------------+--------------------------------------------+
    |          'underground_line_settings'      |          '[UNDERGROUNDLINE SETTING]'       |
    +-------------------------------------------+--------------------------------------------+
    |                'switch_settings'          |               '[SWITCH SETTING]'           |
    +-------------------------------------------+--------------------------------------------+
    |                 'fuse_settings'           |                '[FUSE SETTING]'            |
    +-------------------------------------------+--------------------------------------------+
    |               'recloser_settings'         |             '[RECLOSER SETTING]'           |
    +-------------------------------------------+--------------------------------------------+
    |                    'section'              |                    '[SECTION]'             |
    +-------------------------------------------+--------------------------------------------+
    |                     'line'                |                     '[LINE]'               |
    +-------------------------------------------+--------------------------------------------+
    |                'unbalanced_line'          |               '[LINE UNBALANCED]'          |
    +-------------------------------------------+--------------------------------------------+
    |                'spacing_table'            |           '[SPACING TABLE FOR LINE]'       |
    +-------------------------------------------+--------------------------------------------+
    |          'concentric_neutral_cable'       |         '[CONCENTRIC NEUTRAL CABLE]'       |
    +-------------------------------------------+--------------------------------------------+
    |                   'conductor'             |                  '[CONDUCTOR]'             |
    +-------------------------------------------+--------------------------------------------+
    |                                    CAPACITOR PARSER                                    |
    +-------------------------------------------+--------------------------------------------+
    |           'serie_capacitor_settings'      |          '[SERIE CAPACITOR SETTING]'       |
    +-------------------------------------------+--------------------------------------------+
    |           'shunt_capacitor_settings'      |          '[SHUNT CAPACITOR SETTING]'       |
    +-------------------------------------------+--------------------------------------------+
    |                'serie_capacitor'          |               '[SERIE CAPACITOR]'          |
    +-------------------------------------------+--------------------------------------------+
    |                'shunt_capacitor'          |               '[SHUNT CAPACITOR]'          |
    +-------------------------------------------+--------------------------------------------+
    |                                   TRANSFORMER PARSER                                   |
    +-------------------------------------------+--------------------------------------------+
    |          'auto_transformer_settings'      |           '[AUTO TRANSFORMER SETTING'      |
    +-------------------------------------------+--------------------------------------------+
    |       'grounding_transformer_settings'    |       '[GROUNDINGTRANSFORMER SETTINGS]'    |
    +-------------------------------------------+--------------------------------------------+
    | 'three_winding_auto_transformer_settings' | '[THREE WINDING AUTO TRANSFORMER SETTING]' |
    +-------------------------------------------+--------------------------------------------+
    |    'three_winding_transformer_settings'   |     '[THREE WINDING TRANSFORMER SETTING]'  |
    +-------------------------------------------+--------------------------------------------+
    |             'transformer_settings'        |              '[TRANSFORMER SETTING]'       |
    +-------------------------------------------+--------------------------------------------+
    |               'auto_transformer'          |                '[AUTO TRANSFORMER]'        |
    +-------------------------------------------+--------------------------------------------+
    |             'grounding_transformer'       |               '[GROUNDING TRANSFORMER]'    |
    +-------------------------------------------+--------------------------------------------+
    |        'three_winding_auto_transformer'   |        '[THREE WINDING AUTO TRANSFORMER]'  |
    +-------------------------------------------+--------------------------------------------+
    |           'three_winding_transformer'     |           '[THREE WINDING TRANSFORMER]'    |
    +-------------------------------------------+--------------------------------------------+
    |                 'transformer'             |                   '[TRANSFORMER]'          |
    +-------------------------------------------+--------------------------------------------+
    |           'phase_shifter_transformer'     |          '[PHASE SHIFTER TRANSFORMER]'     |
    +-------------------------------------------+--------------------------------------------+
    |                                    REGULATOR PARSER                                    |
    +-------------------------------------------+--------------------------------------------+
    |              'regulator_settings'         |                '[REGULATOR SETTING]'       |
    +-------------------------------------------+--------------------------------------------+
    |                  'regulator'              |                    '[REGULATOR]'           |
    +-------------------------------------------+--------------------------------------------+
    |                                       LOAD PARSER                                      |
    +-------------------------------------------+--------------------------------------------+
    |                'customer_loads'           |                  '[CUSTOMER LOADS]'        |
    +-------------------------------------------+--------------------------------------------+
    |                'customer_class'           |                  '[CUSTOMER CLASS]'        |
    +-------------------------------------------+--------------------------------------------+
    |                     'loads'               |                     '[LOADS]'              |
    +-------------------------------------------+--------------------------------------------+
    |                              DISTRIBUTED GENERATION PARSER                             |
    +-------------------------------------------+--------------------------------------------+
    |                   'converter'             |                  '[CONVERTER]'             |
    +-------------------------------------------+--------------------------------------------+
    |        'converter_control_settings'       |           '[CONVERTER CONTROL SETTING]'    |
    +-------------------------------------------+--------------------------------------------+
    |           'photovoltaic_settings' '       |              [PHOTOVOLTAIC SETTINGS]'      |
    |                                           |   [ELECTRONIC CONVERTER GENERATOR SETTING] |
    +-------------------------------------------+--------------------------------------------+
    |        'long_term_dynamics_curve_ext'     |          '[LONG TERM DYNAMICS CURVE EXT]'  |
    +-------------------------------------------+--------------------------------------------+
    |               'dggenerationmodel'         |                '[DGGENERATIONMODEL]'       |
    +-------------------------------------------+--------------------------------------------+
    |               'bess_settings'             |                '[BESS SETTINGS]'           |
    +-------------------------------------------+--------------------------------------------+
    |                   'bess'                  |                     '[BESS]'               |
    +-------------------------------------------+--------------------------------------------+
    |                               NETWORK EQUIVALENT PARSER                                |
    +-------------------------------------------+--------------------------------------------+
    |        'network_equivalent_setting'       |      '[NETWORK EQUIVALENT SETTING]'        |
    +-------------------------------------------+--------------------------------------------+
    """

    register_names = ["cyme", "Cyme", "CYME"]

    def __init__(self, **kwargs):
        """
            CYME-->DiTTo class constructor
        """
        # Call super
        super(Reader, self).__init__(**kwargs)

        # Setting the file names and path
        #
        # Set the path to the CYME data files
        if "data_folder_path" in kwargs:
            self.data_folder_path = kwargs["data_folder_path"]
        # Default is current directory
        else:
            self.data_folder_path = "."

        # Set the name of the network file
        if "network_filename" in kwargs:
            self.network_filename = kwargs["network_filename"]
        else:
            self.network_filename = "network.txt"

        # Set the name of the equipment file
        if "equipment_filename" in kwargs:
            self.equipment_filename = kwargs["equipment_filename"]
        else:
            self.equipment_filename = "equipment.txt"

        # Set the name of the load file
        if "load_filename" in kwargs:
            self.load_filename = kwargs["load_filename"]
        else:
            self.load_filename = "load.txt"

        # Set the Network Type to be None. This is set in the parse_sections() function
        #self.network_type = None

        # dictionary of sections to components. Used for identifying elements which are  on the same section (which may cause parallel elements to be created)
        self.section_duplicates = {}

        # Header_mapping.
        #
        # Modify this structure if the headers of your CYME version are not the default one.
        # Modification done by the 'update_header_mapping' method
        #
        self.header_mapping = {  # NODES
            "node": ["[NODE]"],
            "node_connector": ["[NODE CONNECTOR]"],
            # LINES
            "overhead_unbalanced_line_settings": ["[OVERHEADLINEUNBALANCED SETTING]"],
            "overhead_line_settings": ["[OVERHEADLINE SETTING]"],
            "overhead_byphase_settings": ["[OVERHEAD BYPHASE SETTING]"],
            "underground_line_settings": ["[UNDERGROUNDLINE SETTING]"],
            "switch": ["[SWITCH]"],
            "switch_settings": ["[SWITCH SETTING]"],
            "sectionalizer": ["[SECTIONALIZER]"],
            "sectionalizer_settings": ["[SECTIONALIZER SETTING]"],
            "fuse": ["[FUSE]"],
            "fuse_settings": ["[FUSE SETTING]"],
            "recloser": ["[RECLOSER]"],
            "recloser_settings": ["[RECLOSER SETTING]"],
            "breaker": ["[BREAKER]"],
            "breaker_settings": ["[BREAKER SETTING]"],
            "section": ["[SECTION]"],
            "line": ["[LINE]"],
            "unbalanced_line": ["[LINE UNBALANCED]"],
            "spacing_table": ["[SPACING TABLE FOR LINE]"],
            "conductor": ["[CONDUCTOR]"],
            "cable": ["[CABLE]"],
            "concentric_neutral_cable": [
                "[CABLE CONCENTRIC NEUTRAL]",
                "[CONCENTRIC NEUTRAL CABLE]",
            ],
            "network_protector": ["[NETWORKPROTECTOR]"],
            "network_protector_settings": ["[NETWORKPROTECTOR SETTING]"],
            # CAPACITORS
            "serie_capacitor_settings": ["[SERIES CAPACITOR SETTING]"],
            "shunt_capacitor_settings": ["[SHUNT CAPACITOR SETTING]"],
            "serie_capacitor": ["[SERIES CAPACITOR]"],
            "shunt_capacitor": ["[SHUNT CAPACITOR]"],
            # TRANSFORMERS
            "auto_transformer_settings": ["[AUTO TRANSFORMER SETTING]"],
            "grounding_transformer_settings": ["[GROUNDINGTRANSFORMER SETTINGS]"],
            "three_winding_auto_transformer_settings": [
                "[THREE WINDING AUTO TRANSFORMER SETTING]"
            ],
            "three_winding_transformer_settings": [
                "[THREE WINDING TRANSFORMER SETTING]"
            ],
            "transformer_settings": ["[TRANSFORMER SETTING]"],
            "phase_shifter_transformer_settings": [
                "[PHASE SHIFTER TRANSFORMER SETTING]"
            ],
            "auto_transformer": ["[AUTO TRANSFORMER]"],
            "grounding_transformer": ["[GROUNDING TRANSFORMER]"],
            "three_winding_auto_transformer": ["[THREE WINDING AUTO TRANSFORMER]"],
            "three_winding_transformer": ["[THREE WINDING TRANSFORMER]"],
            "transformer": ["[TRANSFORMER]"],
            "phase_shifter_transformer": ["[PHASE SHIFTER TRANSFORMER]"],
            # REGULATORS
            "regulator_settings": ["[REGULATOR SETTING]"],
            "regulator": ["[REGULATOR]"],
            # LOADS
            "customer_loads": ["[CUSTOMER LOADS]"],
            "customer_class": ["[CUSTOMER CLASS]"],
            "loads": ["[LOADS]"],
            "source": ["[SOURCE]"],
            "headnodes": ["[HEADNODES]"],
            "source_equivalent": ["[SOURCE EQUIVALENT]"],
            # DISTRIBUTED GENERATION
            "converter": ["[CONVERTER]"],
            "converter_control_settings": ["[CONVERTER CONTROL SETTING]"],
            "photovoltaic_settings": [
                "[PHOTOVOLTAIC SETTINGS]",
                "[ELECTRONIC CONVERTER GENERATOR SETTING]",
            ],
            "long_term_dynamics_curve_ext": ["[LONG TERM DYNAMICS CURVE EXT]"],
            "dggenerationmodel": ["[DGGENERATIONMODEL]"],
            "bess_settings": ["[BESS SETTINGS]"],
            "bess": ["[BESS]"],
            # SUBSTATIONS
            "substation": ["[SUBSTATION]"],
            "subnetwork_connections": ["[SUBNETWORK CONNECTIONS]"],
            # NETWORK EQUIVALENT
            "network_equivalent_setting": ["[NETWORK EQUIVALENT SETTING]"],
        }

    def update_header_mapping(self, update):
        """
        This method changes the default object<->header mapping.
        This can be useful when using a different version of CYME for example.

        **Usage:**

        >>> my_reader.update_header_mapping(modifications)

        :param update: New object<->header mapping
        :type update: dict
        """
        # Check that the update is a Python dict
        if not isinstance(update, dict):
            raise ValueError(
                "update_header_mapping expects a dictionary. A {type} instance was provided".format(
                    type(update)
                )
            )

        # Instanciate new header mapping
        new_mapping = {k: [] for k in self.header_mapping.keys()}

        # Loop over the default header mapping and update as requested
        for key, value in self.header_mapping.items():
            if key in update and update[key] not in value:
                new_mapping[key].append(update[key])
            else:
                new_mapping[key].append(value)

        # Basic safety check
        if len(new_mapping) != len(self.header_mapping):
            raise ValueError("Error in the update header mapping process.")

        # Replace the old mapping by the new one
        self.header_mapping = new_mapping

    def get_file_content(self, filename):
        """
        Open the requested file and returns the content.
        For convinience, filename can be either the full file path or:

            -'network': Will get the content of the network file given in the constructor
            -'equipment': Will get the content of the equipment file given in the constructor
            -'load': Will get the content of the load file given in the constructor
        """
        # Shortcut mapping
        # if filename == "network":
        #     filename = os.path.join(self.data_folder_path, self.network_filename)
        # elif filename == "equipment":
        #     filename = os.path.join(self.data_folder_path, self.equipment_filename)
        # elif filename == "load":
        #     filename = os.path.join(self.data_folder_path, self.load_filename)

        if filename == "network":
            filename =  self.network_filename
        elif filename == "equipment":
            filename =  self.equipment_filename
        elif filename == "load":
            filename = self.load_filename

        # Open the file and get the content
        try:
            with open(filename, "r") as f:
                content_ = f.readlines()
        except:
            logger.warning("Unable to open file {name}".format(name=filename))
            content_ = []
            pass

        self.content = iter(content_)

    def phase_mapping(self, CYME_value):
        """
        Maps the CYME phase value format to a list of ABC phases:

        +------------+--------------+
        | CYME value | Return value |
        +============+==============+
        |     0      |     [None]   |
        +------------+--------------+
        |     1      |     ['A']    |
        +------------+--------------+
        |     2      |     ['B']    |
        +------------+--------------+
        |     3      |     ['C']    |
        +------------+--------------+
        |     4      |  ['A','B']   |
        +------------+--------------+
        |     5      |  ['A','C']   |
        +------------+--------------+
        |     6      |  ['B','C']   |
        +------------+--------------+
        |     7      | ['A','B','C']|
        +------------+--------------+

        .. note::

            If the value provided is not an integer in [0,7], the function assumes that it receives a string like 'ABC'. In this case, it splits the string in a list of phases ['A','B','C'].
        """
        if CYME_value == 0:
            return [None]
        elif CYME_value == 1:
            return ["A"]
        elif CYME_value == 2:
            return ["B"]
        elif CYME_value == 3:
            return ["C"]
        elif CYME_value == 4:
            return ["A", "B"]
        elif CYME_value == 5:
            return ["A", "C"]
        elif CYME_value == 6:
            return ["B", "C"]
        elif CYME_value == 7:
            return ["A", "B", "C"]
        else:
            return list(CYME_value)

    def phase_to_num(self, phase):
        """
        Maps phase in 'A', 'B', 'C' format in 1, 2, 3 format.

        **Mapping:**

        +--------+-------+
        | letter | digit |
        +========+=======+
        |   'A'  |   1   |
        +--------+-------+
        |   'B'  |   2   |
        +--------+-------+
        |   'C'  |   3   |
        +--------+-------+
        """
        if phase == "A" or phase == "a":
            return "1"
        elif phase == "B" or phase == "b":
            return "2"
        elif phase == "C" or phase == "c":
            return "3"
        else:
            return phase

    def load_value_type_mapping(self, load_type, value1, value2):
        """
        CYME customer loads provide two values v1 and v2 as well as a load value type:
        This function takes these as inputs and outputs P and Q of the load.

        :param load_type: CYME load type
        :type load_type: int or str (see table below)
        :param value1: Value 1
        :type value1: float
        :param value2: Value 2
        :type value2: float
        :returns: P and Q
        :rtype: KW and KVAR

        **Mapping:**

        +-----------+------------+-----------------+------------------------------------------+
        | type code | type value |        P        |                 Q                        |
        +===========+============+=================+==========================================+
        |    0      |  KW_KVAR   | :math:`v_1`     | :math:`v_2`                              |
        +-----------+------------+-----------------+------------------------------------------+
        |    1      |  KVA_PF    | :math:`v_1 v_2` | :math:`v_1 \\sqrt{1-v_2^2}`              |
        +-----------+------------+-----------------+------------------------------------------+
        |    2      |  KW_PF     | :math:`v_1`     | :math:`\\frac{v_1}{v_2} \\sqrt{1-v_2^2}` |
        +-----------+------------+-----------------+------------------------------------------+
        |    3      |  AMP_PF    |      ??         |                  ??                      |
        +-----------+------------+-----------------+------------------------------------------+
        """
        if not isinstance(value1, float):
            try:
                value1 = float(value1)
            except:
                raise ValueError(
                    "Value1={} could not be converted to float in load_value_type_mapping.".format(
                        value1
                    )
                )

        if not isinstance(value2, float):
            try:
                value2 = float(value2)
            except:
                raise ValueError(
                    "Value2={} could not be converted to float in load_value_type_mapping.".format(
                        value2
                    )
                )

        if isinstance(load_type, string_types):
            if load_type == "0" or load_type.lower() == "kw_kvar":
                return value1, value2
            if load_type == "1" or load_type.lower() == "kva_pf":
                return value1 * value2, value1 * np.sqrt(1 - value2 ** 2)
            if load_type == "2" or load_type.lower() == "kw_pf":
                return value1, value1 / value2 * np.sqrt(1 - value2 ** 2)
            if load_type == "3" or load_type.lower() == "amp_pf":
                raise NotImplementedError("AMP_PF load type not implemented yet.")

        elif isinstance(load_type, int):
            if load_type == 0:
                return value1, value2
            if load_type == 1:
                return value1 * value2, value1 * np.sqrt(1 - value2 ** 2)
            if load_type == 2:
                return value1, value1 / value2 * np.sqrt(1 - value2 ** 2)
            if load_type == 3:
                raise NotImplementedError("AMP_PF load type not implemented yet.")

        else:
            raise ValueError(
                "load_value_type_mapping expects a string or integer for load_type. {} was provided.".format(
                    type(load_type)
                )
            )

    def capacitors_connection_mapping(self, conn):
        """
        Maps the capacitors connection in CYME (CAP_CONN) to DiTTo connection_type.

        :param conn: Connection in CYME
        :type conn: integer or string
        :returns: Connection in DiTTo
        :rtype: str

        **Mapping:**

        +---------------+-----------------------+
        | CYME CAP_CONN | DiTTo connection_type |
        +===============+=======================+
        |   0 or 'Y'    |           'Y'         |
        +---------------+-----------------------+
        |   1 or 'YNG'  |           'Y'         |
        +---------------+-----------------------+
        |   2 or 'D'    |           'D'         |
        +---------------+-----------------------+
        """
        if not isinstance(conn, (string_types, int)):
            raise ValueError(
                "capacitors_connection_mapping only accepts int or string. {} was provided.".format(
                    type(conn)
                )
            )

        if conn == 0 or conn == "0" or conn == "Y":
            return "Y"
        elif conn == 1 or conn == "1" or conn == "YNG":
            return "Y"
        elif conn == 2 or conn == "2" or conn == "D":
            return "D"
        else:
            return conn

    def connection_configuration_mapping(self, value):
        """
        Map the connection configuration from CYME to DiTTo.

        **Mapping:**

        +----------+----------------+------------+
        |   Value  |       CYME     |  DiTTo     |
        +==========+================+============+
        | 0 or '0' |       'Yg'     |   'Y'      |
        +----------+----------------+------------+
        | 1 or '1' |       'Y'      |   'Y'      |
        +----------+----------------+------------+
        | 2 or '2' |     'Delta'    |   'D'      |
        +----------+----------------+------------+
        | 3 or '3' |  'Open Delta'  |   'D'      |
        +----------+----------------+------------+
        | 4 or '4' | 'Closed Delta' |   'D'      |
        +----------+----------------+------------+
        | 5 or '5' |      'Zg'      |   'Z'      |
        +----------+----------------+------------+
        | 6 or '6' |      'CT'      | NOT MAPPED |
        +----------+----------------+------------+
        | 7 or '7' |      'Dg'      | NOT MAPPED |
        +----------+----------------+------------+
        """
        if isinstance(value, int):
            if value in [0, 1]:
                return "Y"
            if value in [2, 3, 4]:
                return "D"
            if value == 5:
                return "Z"
            if value in [6, 7]:
                raise NotImplementedError(
                    "Connection {} not implemented.".format(value)
                )

        elif isinstance(value, string_types):
            if (
                value == "0"
                or value.lower() == "yg"
                or value == "1"
                or value.lower() == "y"
            ):
                return "Y"
            if (
                value == "2"
                or value.lower() == "delta"
                or value == "3"
                or value.lower() == "open delta"
                or value == "4"
                or value.lower() == "closed delta"
            ):
                return "D"
            if value == "5" or value.lower() == "zg":
                return "Z"
            if (
                value == "6"
                or value.lower() == "ct"
                or value == "7"
                or value.lower() == "dg"
            ):
                raise NotImplementedError(
                    "Connection {} not implemented.".format(value)
                )

        else:
            raise ValueError(
                "connection_configuration_mapping expects an integer or a string. {} was provided.".format(
                    type(value)
                )
            )

    def transformer_connection_configuration_mapping(self, value, winding):
        """
        Map the connection configuration for transformer (2 windings) objects from CYME to DiTTo.

        :param value: CYME value (either string or id)
        :type value: int or str
        :param winding: Number of the winding (0 or 1)
        :type winding: int
        :returns: DiTTo connection configuration for the requested winding
        :rtype: str

        **Mapping:**

        +----------+----------------+------------+
        |   Value  |       CYME     |  DiTTo     |
        +----------+----------------+-----+------+
        |          |                | 1st | 2nd  |
        +==========+================+=====+======+
        | 0 or '0' |      'Y_Y'     | 'Y' | 'Y'  |
        +----------+----------------+-----+------+
        | 1 or '1' |      'D_Y'     | 'D' | 'Y'  |
        +----------+----------------+-----+------+
        | 2 or '2' |      'Y_D'     | 'Y' | 'D'  |
        +----------+----------------+-----+------+
        | 3 or '3' |    'YNG_YNG'   | 'Y' | 'Y'  |
        +----------+----------------+-----+------+
        | 4 or '4' |      'D_D'     | 'D' | 'D'  |
        +----------+----------------+-----+------+
        | 5 or '5' |     'DO_DO'    | 'D' | 'D'  |
        +----------+----------------+-----+------+
        | 6 or '6' |     'YO_DO'    | 'Y' | 'D'  |
        +----------+----------------+-----+------+
        | 7 or '7' |     'D_YNG'    | 'D' | 'Y'  |
        +----------+----------------+-----+------+
        | 8 or '8' |     'YNG_D'    | 'Y' | 'D'  |
        +----------+----------------+-----+------+
        | 9 or '9' |     'Y_YNG'    | 'Y' | 'Y'  |
        +----------+----------------+-----+------+
        |10 or '10'|     'YNG_Y'    | 'Y' | 'Y'  |
        +----------+----------------+-----+------+
        |11 or '11'|     'Yg_Zg'    | 'Y' | 'Z'  |
        +----------+----------------+-----+------+
        |12 or '12'|     'D_Zg'     | 'D' | 'Z'  |
        +----------+----------------+-----+------+
        """
        if winding not in [0, 1]:
            raise ValueError(
                "transformer_connection_configuration_mapping expects an integer 0 or 1 for winding arg. {} was provided.".format(
                    winding
                )
            )

        res = (None, None)

        if isinstance(value, int):
            if value == 0 or value == 3 or value == 9 or value == 10:
                res = ("Y", "Y")
            if value == 1 or value == 7:
                res = ("D", "Y")
            if value == 2 or value == 6 or value == 8:
                res = ("Y", "D")
            if value == 4 or value == 5:
                res = ("D", "D")
            if value == 11:
                res = ("Y", "Z")
            if value == 12:
                res = ("D", "Z")

        elif isinstance(value, string_types):
            if value == "0" or value.lower() == "y_y":
                res = ("Y", "Y")
            if value == "1" or value.lower() == "d_y":
                res = ("D", "Y")
            if value == "2" or value.lower() == "y_d":
                res = ("Y", "D")
            if value == "3" or value.lower() == "yng_yng":
                res = ("Y", "Y")
            if value == "4" or value.lower() == "d_d":
                res = ("D", "D")
            if value == "5" or value.lower() == "do_do":
                res = ("D", "D")
            if value == "6" or value.lower() == "yo_do":
                res = ("Y", "D")
            if value == "7" or value.lower() == "d_yng":
                res = ("D", "Y")
            if value == "8" or value.lower() == "yng_d":
                res = ("Y", "D")
            if value == "9" or value.lower() == "y_yng":
                res = ("Y", "Y")
            if value == "10" or value.lower() == "yng_y":
                res = ("Y", "Y")
            if value == "11" or value.lower() == "yg_zg":
                res = ("Y", "Z")
            if value == "12" or value.lower() == "d_zg":
                res = ("D", "Z")

        else:
            raise ValueError(
                "transformer_connection_configuration_mapping expects an integer or a string. {} was provided.".format(
                    type(value)
                )
            )

        return res[winding]

    def check_object_in_line(self, line, obj):
        """
        Check if the header corresponding to object is in the given line.

        :param line: Text line from CYME ASCII file
        :type line: str
        :param obj: Object of interest that exists in the mapping
        :type obj: str
        :returns: True if the header is in line. False otherwise.
        :rtype: bool
        """
        # Safety checks
        if not isinstance(line, string_types):
            raise ValueError(
                "check_object_in_line expects a string for both line and object. A {type} instance was provided for line.".format(
                    type=type(line)
                )
            )

        if not isinstance(obj, string_types):
            raise ValueError(
                "check_object_in_line expects a string for both line and object. A {type} instance was provided for object.".format(
                    type=type(obj)
                )
            )

        if not obj in self.header_mapping:
            raise ValueError(
                "{obj} is not a valid object name for the object<->header mapping.{mapp}".format(
                    obj=obj, mapp=self.header_mapping
                )
            )

        return np.any([x in line for x in self.header_mapping[obj]])

    # Lusha
    # read network file and store everthing in different list
    def parse_network_file(self):
        self.get_file_content("network")

        self.file_network_header = []
        self.file_network_section = []
        self.file_network_line_overhead = []
        self.file_network_line_overhead_byphase = []
        self.file_network_line_underground = []
        self.file_network_switch = []
        self.file_network_breaker = []
        self.file_network_fuse = []
        self.file_network_recloser = []
        self.file_network_sectionalizer = []


        self.file_network_trans = []

        self.file_network_node = []
        self.file_network_headnode = []
        self.file_network_source = []
        self.file_network_source_eqv = []
        self.file_network_regulator = []
        self.file_network_capacitor = []




        # self.file_network_subnet = []
        # self.file_network_subconn = []

        is_header = False
        is_section = False
        is_line_overhead = False
        is_line_overhead_byphase = False
        is_line_underground = False
        is_switch = False
        is_breaker = False
        is_fuse = False
        is_recloser = False
        is_sectionalizer = False
        is_trans = False
        is_regulator = False
        is_node = False
        is_capacitor = False
        is_headnodes = False
        is_source = False
        is_source_equivalent = False

        for line in self.content:

            #if line.lower().startswith('[general]'):
            #     is_header = True
            # if line.lower().startswith('[imperial]'):
            #     is_header = True

            # header part
            if "cyme_version" in line.lower() or "[si]" in line.lower() or "[imperial]" in line.lower():
                is_header = True
            if "[SECTION]" in line:
                is_section = True
            if "overheadline setting" in line.lower() or  "overhead_unbalanced_line_settings" in line.lower() or "overhead_line_settings" in line.lower() or "overhead_byphase_settings" in line.lower():
                is_line_overhead = True
            if "overhead byphase setting" in line.lower():
                is_line_overhead_byphase = True
            if "undergroundline setting" in line.lower () or "underground_line_settings" in line.lower():
                is_line_underground = True
            if "switch setting" in line.lower():
                is_switch = True
            if "fuse setting" in line.lower():
                is_fuse = True
            if "breaker setting" in line.lower():
                is_breaker = True
            if "sectionalizer setting" in line.lower():
                is_sectionalizer = True
            if "recloser setting" in line.lower():
                is_recloser = True
            if "transformer setting" in line.lower() or "auto_transformer_settings" in line.lower() or "grounding_transformer_settings" in line.lower() or "three_winding_auto_transformer_settings" in line.lower() \
                or "three_winding_transformer_settings" in line.lower() or "transformer_settings" in line.lower() or "phase_shifter_transformer_settings" in line.lower():
                is_trans = True
            if "regulator setting" in line.lower():
                is_regulator = True
            if "[NODE]" in line:
                is_node = True
            if "serie_capacitor_settings" in line.lower() or "shunt capacitor setting" in line.lower():
                is_capacitor = True
            if "[HEADNODES]" in line:
                is_headnodes = True
            if "[SOURCE]" in line:
                is_source = True
            if "[SOURCE EQUIVALENT]" in line:
                is_source_equivalent = True


            # store header
            if is_header:
                if len(line.strip())>0:
                    self.file_network_header.append(line)
                else:
                    is_header = False
                    continue

            if is_node:
                if len(line.strip())>0:
                    self.file_network_node.append(line)
                else:
                    is_node = False
                    continue

            if is_headnodes:
                if len(line.strip())>0:
                    self.file_network_headnode.append(line)
                else:
                    is_headnodes = False
                    continue

            if is_source:
                if len(line.strip())>0:
                    self.file_network_source.append(line)
                else:
                    is_source = False
                    continue

            if is_source_equivalent:
                if len(line.strip())>0:
                    self.file_network_source_eqv.append(line)
                else:
                    is_source_equivalent = False
                    continue


            if is_line_overhead:
                if len(line.strip())>0:
                    self.file_network_line_overhead.append(line)
                else:
                    is_line_overhead = False
                    continue

            if is_line_overhead_byphase:
                if len(line.strip())>0:
                    self.file_network_line_overhead_byphase.append(line)
                else:
                    is_line_overhead_byphase = False
                    continue

            if is_line_underground:
                if len(line.strip())>0:
                    self.file_network_line_underground.append(line)
                else:
                    is_line_underground = False
                    continue

            if is_switch:
                if len(line.strip())>0:
                    self.file_network_switch.append(line)
                else:
                    is_switch = False
                    continue

            if is_fuse:
                if len(line.strip())>0:
                    self.file_network_fuse.append(line)
                else:
                    is_fuse = False
                    continue

            if is_breaker:
                if len(line.strip())>0:
                    self.file_network_breaker.append(line)
                else:
                    is_breaker = False
                    continue

            if is_recloser:
                if len(line.strip())>0:
                    self.file_network_recloser.append(line)
                else:
                    is_recloser = False
                    continue

            if is_sectionalizer:
                if len(line.strip())>0:
                    self.file_network_sectionalizer.append(line)
                else:
                    is_sectionalizer = False
                    continue

            if is_section:
                if len(line.strip())>0:
                    self.file_network_section.append(line)
                else:
                    is_section = False
                    continue

            if is_regulator:
                if len(line.strip())>0:
                    self.file_network_regulator.append(line)
                else:
                    is_regulator = False
                    continue

            if is_trans:
                if len(line.strip())>0:
                    self.file_network_trans.append(line)
                else:
                    is_trans = False
                    continue

            if is_capacitor:
                if len(line.strip())>0:
                    self.file_network_capacitor.append(line)
                else:
                    is_capacitor = False
                    continue

        print("done with reading network.txt file\n")


    def parse_equipment_file(self):
        self.get_file_content("equipment")

        self.file_equipment_cable = []
        self.file_equipment_cable_concentric_neutral = []
        self.file_equipment_cable_insulation = []
        self.file_equipment_cable_conductor = []
        self.file_equipment_conductor = []
        self.file_equipment_spacing = []
        self.file_equipment_line = []
        self.file_equipment_line_unbalanced = []
        self.file_equipment_IM = []
        self.file_equipment_SM = []
        self.file_equipment_IG = []
        self.file_equipment_SG = []
        self.file_equipment_ECG = []
        self.file_equipment_regulator = []
        self.file_equipment_switch = []
        self.file_equipment_breaker = []
        self.file_equipment_fuse = []
        self.file_equipment_recloser = []
        self.file_equipment_sectionalizer = []
        self.file_equipment_substation = []
        self.file_equipment_transformer = []
        self.file_equipment_capacitor = []

        is_cable = False
        is_cable_concentric_neutral = False
        is_cable_insulation = False
        is_cable_conductor = False
        is_conductor = False
        is_spacing  = False
        is_line = False
        is_line_unbalanced = False
        is_IM = False
        is_SM = False
        is_IG = False
        is_SG = False
        is_ECG = False
        is_regulator = False
        is_switch = False
        is_breaker = False
        is_fuse = False
        is_recloser = False
        is_sectionalizer = False
        is_substation = False
        is_transformer = False
        is_capacitor = False


        for line in self.content:
            # header part
            # if "cyme_version" in line.lower() or "[si]" in line.lower() or "[imperial]" in line.lower():
            #     is_header = True
            # if "[SECTION]" in line:
            #     is_section = True

            # header part
            if "cyme_version" in line.lower() or "[si]" in line.lower() or "[imperial]" in line.lower():
                is_header = True
            if "[cable]" in line.lower():
                is_cable = True
            if "[cable concentric neutral]" in line.lower():
                is_cable_concentric_neutral = True
            if "[cable insulation]" in line.lower():
                is_cable_insulation = True
            if "[cable conductor]" in line.lower():
                is_cable_conductor = True
            if "[conductor]" in line.lower():
                is_conductor = True
            if "[spacing" in line.lower():
                is_spacing = True
            if "[line]" in line.lower():
                is_line = True
            if "[line unbalanced]" in line.lower():
                is_line_unbalanced = True
            if "[induction motor]" in line.lower():
                is_IM = True
            if "[synchronous motor]" in line.lower():
                is_SM = True
            if "[induction generator]" in line.lower():
                is_IG = True
            if "[synchronous generator]" in line.lower():
                is_SG = True
            if "[electronic converter generator]" in line.lower():
                is_ECG = True
            if "[regulator]" in line.lower():
                is_regulator = True
            if "[switch]" in line.lower():
                is_switch = True
            if "[breaker]" in line.lower():
                is_breaker = True
            if "[recloser]" in line.lower():
                is_recloser = True
            if "[fuse]" in line.lower():
                is_fuse = True
            if "[sectionalizer]" in line.lower():
                is_sectionalizer = True
            if "[substation]" in line.lower():
                is_substation = True
            if "[transformer]" in line.lower():
                is_transformer = True
            if "[shunt capacitor]" in line.lower():
                is_capacitor = True





            if is_cable:
                if len(line.strip()) > 0:
                    self.file_equipment_cable.append(line)
                else:
                    is_cable = False
                    continue

            if is_cable_concentric_neutral:
                if len(line.strip()) > 0:
                    self.file_equipment_cable_concentric_neutral.append(line)
                else:
                    is_cable_concentric_neutral = False
                    continue


            if is_cable_insulation:
                if len(line.strip()) > 0:
                    self.file_equipment_cable_insulation.append(line)
                else:
                    is_cable_insulation = False
                    continue


            if is_cable_conductor:
                if len(line.strip()) > 0:
                    self.file_equipment_cable_conductor.append(line)
                else:
                    is_cable_conductor = False
                    continue


            if is_conductor:
                if len(line.strip()) > 0:
                    self.file_equipment_conductor.append(line)
                else:
                    is_conductor = False
                    continue


            if is_spacing:
                if len(line.strip()) > 0:
                    self.file_equipment_spacing.append(line)
                else:
                    is_spacing = False
                    continue

            if is_line:
                if len(line.strip()) > 0:
                    self.file_equipment_line.append(line)
                else:
                    is_line = False
                    continue

            if is_line_unbalanced:
                if len(line.strip()) > 0:
                    self.file_equipment_line_unbalanced.append(line)
                else:
                    is_line_unbalanced = False
                    continue

            if is_IM:
                if len(line.strip()) > 0:
                    self.file_equipment_IM.append(line)
                else:
                    is_IM = False
                    continue

            if is_SM:
                if len(line.strip()) > 0:
                    self.file_equipment_SM.append(line)
                else:
                    is_SM = False
                    continue

            if is_IG:
                if len(line.strip()) > 0:
                    self.file_equipment_IG.append(line)
                else:
                    is_IG = False
                    continue

            if is_SG:
                if len(line.strip()) > 0:
                    self.file_equipment_SG.append(line)
                else:
                    is_SG = False
                    continue

            if is_ECG:
                if len(line.strip()) > 0:
                    self.file_equipment_ECG.append(line)
                else:
                    is_ECG = False
                    continue

            if is_regulator:
                if len(line.strip()) > 0:
                    self.file_equipment_regulator.append(line)
                else:
                    is_regulator = False
                    continue

            if is_switch:
                if len(line.strip()) > 0:
                    self.file_equipment_switch.append(line)
                else:
                    is_switch = False
                    continue

            if is_breaker:
                if len(line.strip()) > 0:
                    self.file_equipment_breaker.append(line)
                else:
                    is_breaker = False
                    continue


            if is_fuse:
                if len(line.strip()) > 0:
                    self.file_equipment_fuse.append(line)
                else:
                    is_fuse = False
                    continue


            if is_recloser:
                if len(line.strip()) > 0:
                    self.file_equipment_recloser.append(line)
                else:
                    is_recloser = False
                    continue

            if is_sectionalizer:
                if len(line.strip()) > 0:
                    self.file_equipment_sectionalizer.append(line)
                else:
                    is_sectionalizer = False
                    continue

            if is_substation:
                if len(line.strip()) > 0:
                    self.file_equipment_substation.append(line)
                else:
                    is_substation = False
                    continue

            if is_transformer:
                if len(line.strip()) > 0:
                    self.file_equipment_transformer.append(line)
                else:
                    is_transformer = False
                    continue

            if is_capacitor:
                if len(line.strip()) > 0:
                    self.file_equipment_capacitor.append(line)
                else:
                    is_capacitor = False
                    continue




    def parser_helper(self, line, obj_list, attribute_list, mapping, *args, **kwargs):
        """
        .. warning:: This is a helper function for the parsers. Do not use directly.

        Takes as input the list of objects we want to parse as well as the list of attributes we want to extract.
        Also takes the default positions of the attributes (mapping).
        The function returns a list of dictionaries, where each dictionary contains the values of the desired attributes of a CYME object.
        """
        if isinstance(attribute_list, list):
            attribute_list = np.array(attribute_list)

        if not isinstance(attribute_list, np.ndarray):
            raise ValueError("Could not cast attribute list to Numpy array.")

        if args and isinstance(args[0], dict):
            additional_information = args[0]
        else:
            additional_information = {}

        # This is in the case of multiple Format= lines
        if (
            kwargs and "additional_attributes_list" in kwargs
        ):  # Currently assume only one set of additional attributes, but can be modified to allow for multiple attribute lists
            additional_attributes = kwargs["additional_attributes_list"]
        else:
            additional_attributes = []

        result = {}

        # Check the presence of headers in the given line
        checks = [self.check_object_in_line(line, obj) for obj in obj_list]

        # If we have a least one
        if any(checks):
            # Get the next line
            try:
                next_line = next(self.content)
            except:
                return

            # If the next line provides the format, then grab it
            if "format" in next_line.lower():
                try:
                    # Lusha
                    #print("original mapping: " + str(list(mapping)))
                    #print("attribute list: " + str(list(attribute_list)))

                    mapping = {}
                    arg_list = next_line.split("=")[1]
                    arg_list = arg_list.split(",")
                    # Put everything in lower case
                    arg_list = map(lambda x: x.lower().strip("\r\n"), arg_list)
                    arg_list = map(lambda x: x.strip("\n"), arg_list)
                    arg_list = map(lambda x: x.strip("\r"), arg_list)

                    # We want the attributes in the attribute list
                    for idx, arg in enumerate(arg_list):
                        temp = np.argwhere(arg == attribute_list).flatten()
                        if len(temp) == 1:
                            idx2 = temp[0]
                            mapping[attribute_list[idx2]] = idx
                except:
                    pass

                # Lusha
                #print("new mapping: "+ str(list(mapping)))
                next_line = next(self.content)

            # At this point, we should have the mapping for the parameters of interest
            # while next_line[0] not in ['[','',' ','\n','\r\n']:
            while len(next_line) > 2:
                if "=" not in next_line.lower():

                    data = next_line.split(",")

                    ID = data[0].strip()

                    if len(data) > 1:

                        while ID in result:
                            ID += "*"
                        result[ID] = {}

                        for k in attribute_list:
                            try:
                                result[ID][k] = data[mapping[k]]
                            except:
                                pass

                        result[ID].update(additional_information)
                elif additional_attributes is not None and additional_attributes != []:
                    try:
                        mapping = {}
                        arg_list = next_line.split("=")[1]
                        arg_list = arg_list.split(",")
                        # Put everything in lower case
                        arg_list = map(lambda x: x.lower().strip("\r\n"), arg_list)
                        arg_list = map(lambda x: x.strip("\n"), arg_list)
                        arg_list = map(lambda x: x.strip("\r"), arg_list)

                        if isinstance(additional_attributes, list):
                            additional_attributes = np.array(additional_attributes)

                        if not isinstance(additional_attributes, np.ndarray):
                            raise ValueError(
                                "Could not cast attribute list to Numpy array."
                            )

                        # We want the attributes in the attribute list
                        for idx, arg in enumerate(arg_list):
                            temp = np.argwhere(arg == additional_attributes).flatten()
                            if len(temp) == 1:
                                idx2 = temp[0]
                                mapping[additional_attributes[idx2]] = idx
                        attribute_list = additional_attributes
                        additional_attributes = []
                    except:
                        logger.warning(
                            "Attempted to apply additional attributes but failed"
                        )
                        pass

                try:
                    next_line = next(self.content)
                except StopIteration:
                    break

        return result

    def parse(self, model=None, **kwargs):
        """
        Parse the CYME model to DiTTo.

        :param model: DiTTo model
        :type model: DiTTo model
        :param verbose: Set the verbose mode. Optional. Default=True
        :type verbose: bool
        """
        if "verbose" in kwargs and isinstance(kwargs["verbose"], bool):
            self.verbose = kwargs["verbose"]
        else:
            self.verbose = False

        #Lusha
        # read network file and store different part
        if self.verbose:
            logger.info("Loading Network File...")
        self.parse_network_file()

        # read equipment file
        if self.verbose:
            logger.info("Loading Equipment File...")
        self.parse_equipment_file()

        if self.verbose:
            logger.info("Parsing the header...")
        self.parse_header()

        logger.info("Parsing the sections...")
        #self.parse_sections(model)
        # Lusha
        self.parse_sections()
        #print("Done section")


        # Lusha
        # Parse headnodes for feeders
        # The variable self.network_type is set in the parse_sections() function.
        # i.e. parse_sections
        logger.info("Parsing the Headnodes...")
        self.parse_head_nodes()
        print("Done headnode")

        # Call parse method of abtract reader
        #super(Reader, self).parse(model, **kwargs)
        super(Reader, self).parse(**kwargs)
        print("Done Line, Transformer, Regulator, Capacitor, Node, Load")

        logger.info("Parsing the sources...")
        #self.parse_sources(model)
        # Lusha
        # Parse source after Line, Node
        self.parse_sources()


        #logger.info("Parsing the network equivalents...")
        #self.parse_network_equivalent(model)
        #self.parse_network_equivalent()
        #print("Done Equivalent")




        #logger.info("Parsing the subnetwork connections...")
        #self.parse_subnetwork_connections()


        # if self.network_type == "substation":
        #     logger.info("Parsing the subnetwork connections...")
        #     self.parse_subnetwork_connections(model)
        # else:
        #     logger.info("Parsing the Headnodes...")
        #     #self.parse_head_nodes(model)
        #     self.parse_head_nodes(model)

        print("Done all feeder subnetwork or headnode")

        # Lusha

        #self.fix_section_overlaps(model)
        #self.fix_section_overlaps()
        print("Done Fix Section Overlap")

        print("Done all feeder fix section overlap")

        # Lusha
        for feedername in self.feeder_models.keys():
            model = self.feeder_models[feedername]

            if model.network_type == "substation":
                continue
            print("In feeder: " + feedername)
            model.set_names()
            modifier = system_structure_modifier(model)
            modifier.set_nominal_voltages_recur()
            modifier.set_nominal_voltages_recur_line()
            print("Done modifier for feeder "+ feedername)


    def parse_header(self):
        """
        Parse the information available in the header.
        Here, we are interested in the version of CYME used in the provided files, as well as the unit system used.
        Since the reader was developed using the documentation for CYME v.8.0, give a warning if the version if different.
        The user is then responsible to check the differences betweeen the two versions.
        """
        print("In parsing_header")

        cyme_version = None
        self.use_SI = None

        # Open any file. For example the network file
        #self.get_file_content("network")
        #for line in self.content:
        for line in self.file_network_header:
            # Lusha
            if "cyme_version" in line.lower():
                try:
                    cyme_version = line.split("=")[1].strip()
                except:
                    pass
                if cyme_version is not None:
                    logger.info("---| Cyme_version={v} |---".format(v=cyme_version))
                    if "." in cyme_version:
                        try:
                            a, b = cyme_version.split(".")
                        except:
                            pass
                        if a != 8 and b != 0:
                            logger.warning(
                                "Warning. The current CYME--->DiTTo reader was developed with documentation of CYME 8.0. Your version is {}. You might want to check the differences between the two.".format(
                                    cyme_version
                                )
                            )

            if "[si]" in line.lower():
                self.use_SI = True
                logger.debug("Unit system used = S.I")

            if "[imperial]" in line.lower():
                self.use_SI = False
                logger.debug("Unit system used = Imperial")

        self.cyme_version = cyme_version

        # if self.use_SI is None:
        #     raise ValueError(
        #         "Could not find [SI] or [IMPERIAL] unit system information. Unable to parse."
        #     )

    def parse_subnetwork_connections(self, model=None):
        """Parse the subnetwork connections.
        These specify the interconnection points for a substation
        """
        model.set_names()
        self.get_file_content("network")
        mapp_subnetwork_connections = {"nodeid": 1}
        self.subnetwork_connections = {}
        for line in self.content:
            self.subnetwork_connections.update(
                self.parser_helper(
                    line,
                    ["subnetwork_connections"],
                    ["nodeid"],
                    mapp_subnetwork_connections,
                )
            )

        for key in self.subnetwork_connections:
            model[
                self.subnetwork_connections[key]["nodeid"]
            ].is_substation_connection = True

    def parse_head_nodes(self, model=None):
        print("Inside parse_head_nodes")
        """ This parses the [HEADNODES] objects and is used to build Feeder_metadata DiTTo objects which define the feeder names and feeder headnodes"""
        # Open the network file
        #self.get_file_content("network")
        # Lusha
        # source headnode to feeder, for source equivalent use
        self.headnode_feeder_mapping = {}
        # source headnode to substation, for source use
        self.headnode_sub_mapping = {}
        # substation to feeders, for source use
        self.sub_feeder_mapping = {}
        # feeder to substation
        self.feeder_sub_mapping = {}
        # feeder to headnodes
        self.feeder_headnode_mapping = {}

        # flag to show whether feeders in the sub is assigned with sources
        #self.sub_source_flag = {}

        mapp = {
            "nodeid": 0,
            "networkid": 1,
            "structureid": 3
        }  # These correspond to the head node name and the feeder name
        headnodes = {}

        try:
            self.content = iter(self.file_network_headnode)
            # Lusha
            #for line in self.file_network_headnode:
            line = next(self.content)
            headnodes.update(
                self.parser_helper(line, ["headnodes"], ["nodeid", "networkid","structureid"], mapp)
            )
        except:
            pass

        for sid, headnode in headnodes.items():
            # Lusha
            # get new mapping for headnode-substation, substation-feeder
            subname = headnode["structureid"].strip().lower()
            feedername = headnode["networkid"].strip().lower()

            # Lusha
            # if no subname exist, set it the same as feedername
            if subname == "":
                subname = "Sub_"+feedername

            # initiate source_flag before parse_source
            # if subname not in self.sub_source_flag.keys():
            #     self.sub_source_flag[subname] = 0

            if subname not in self.sub_feeder_mapping.keys():
                self.sub_feeder_mapping[subname] = []

            if feedername != subname:
                self.sub_feeder_mapping[subname].append(feedername)
                self.feeder_headnode_mapping[feedername] = headnode["nodeid"]
                self.headnode_feeder_mapping[headnode["nodeid"]] = feedername
                self.feeder_sub_mapping[feedername] = subname

                try:
                    model = self.feeder_models[feedername]
                except:
                    print("Cannot find model in parse_head_nodes")

                feeder_metadata = Feeder_metadata(model)
                feeder_metadata.name = headnode["networkid"].strip().lower()
                feeder_metadata.headnode = headnode["nodeid"].strip().lower()

            else:
                self.headnode_sub_mapping[headnode["nodeid"]] = subname



    def parse_sources(self, model=None):
        print("Inside parse_source")
        """Parse the sources."""
        # Open the network file
        #self.get_file_content("network")

        #mapp = {"sourceid": 0, "nodeid": 2, "networkid": 3, "desiredvoltage": 4}
        # Lusha
        mapp = {"sourceid": 0, "nodeid": 2, "networkid": 3, "operatingvoltagea": 4}
        mapp_source_equivalent = {
            "nodeid": 0,
            "voltage": 1,
            "operatingangle1": 2,
            "operatingangle2": 3,
            "operatingangle3": 4,
            "positivesequenceresistance": 5,
            "positivesequencereactance": 6,
            "zerosequenceresistance": 7,
            "zerosequencereactance": 8,
            "configuration": 9,
            #Lusha
            "operatingvoltage1":10,
            "operatingvoltage2": 11,
            "operatingvoltage3": 12,

        }
        mapp_sub = {"id": 0, "mva": 1, "kvll": 6, "conn": 14}

        sources = {}
        subs = {}
        source_equivalents = {}

        try:
            # iterate source
            self.content = iter(self.file_network_source)
            line = next(self.content)
            #for line in self.content:
            sources.update(
                self.parser_helper(
                    line,
                    ["source"],
                    # ["sourceid", "nodeid", "networkid", "desiredvoltage"],
                    # Lusha
                    # parse OperatingVoltageA
                    ["sourceid", "nodeid", "networkid", "operatingvoltagea"],
                    mapp,
                )
            )
        except:
            pass

        try:
            self.content = iter(self.file_network_source_eqv)
            line = next(self.content)
            source_equivalents.update(
                self.parser_helper(
                    line,
                    ["source_equivalent"],
                    [
                        "nodeid",
                        "voltage",
                        "operatingangle1",
                        "operatingangle2",
                        "operatingangle3",
                        "usesecondlevelimpedance", # TODO: add logic to look for this parameter and add secondlevel r & x in case it's selected
                        "positivesequenceresistance",
                        "positivesequencereactance",
                        "zerosequencereactance",
                        "zerosequenceresistance",
                        "configuration",
                        "basemva",
                        "loadmodelname",
                        "firstlevelr1",
                        "firstlevelx1",
                        "firstlevelr0",
                        "firstlevelx0",
                        # Lusha
                        "operatingvoltage1",
                        "operatingvoltage2",
                        "operatingvoltage3"
                    ],
                    mapp_source_equivalent,
                )
            )
        except:
            pass

        try:
            #self.get_file_content("equipment")
            self.content = iter(self.file_equipment_substation)
            line = next(self.content)
            #for line in self.content:
            subs.update(
                self.parser_helper(
                    line, ["substation"], ["id", "mva", "kvll", "conn"], mapp_sub
                )
            )
        except:
            pass

        # store source equivalent
        for sid, source_equivalent_data in source_equivalents.items():

            # if source_equivalent_data["loadmodelname"].lower() != "default":
            #     # Lusha
            #     # if no loadmodelname, then it is default
            #     if source_equivalent_data["loadmodelname"].lower() != '':
            #         continue  # Want to only use the default source equivalent configuration

            # Lusha
            # only use summer data BGE
            # for PHI it is all default
            # source for summer

            # if source_equivalent_data["loadmodelname"].lower() == "default" or \
            #         source_equivalent_data["loadmodelname"].lower() == "winter":
            #       continue

            if source_equivalent_data["loadmodelname"].lower() == "default" or \
                    source_equivalent_data["loadmodelname"].lower() == "":


                # Lusha
                # feeder headnode, usually in source equivalent
                #print(source_equivalent_data["nodeid"])
                if source_equivalent_data["nodeid"] in self.headnode_feeder_mapping.keys():
                    feedername =self.headnode_feeder_mapping[source_equivalent_data["nodeid"]]
                    feeders =[feedername]
                # substation headnode, in both source equivalent and source
                elif source_equivalent_data["nodeid"] in self.headnode_sub_mapping.keys():
                    subname = self.headnode_sub_mapping[source_equivalent_data["nodeid"]]
                    feeders = self.sub_feeder_mapping[subname]
                    continue
                else:
                    raise ValueError("No Source or SourceEq found for Headnode " + str(source_equivalent_data["nodeid"]) + "!")


                # already assigned sources to feeders in sub
                # if self.sub_source_flag[subname] == 1:
                #     continue

                # for k, v in self.section_phase_mapping.items():
                #     if v["fromnodeid"] == source_equivalent_data["nodeid"]:
                #         sectionID = k
                #         _from = v["fromnodeid"]
                #         _to = v["tonodeid"]
                #         phases = list(v["phase"])
                #     if (
                #         v["tonodeid"] == source_equivalent_data["nodeid"]
                #     ):  # In case the edge is connected backwards
                #         sectionID = k
                #         _from = v["tonodeid"]
                #         _to = v["fromnodeid"]
                #         phases = list(v["phase"])

                # Lusha
                for feedername in feeders:
                    try:
                        # Lusha
                        headnode = self.feeder_headnode_mapping[feedername]
                        model = self.feeder_models[feedername]
                        # if feeder already assigned source, skip
                        if model.assigned_source == 1:
                            continue
                        api_source = PowerSource(model)
                        model.source = api_source
                    except:
                        pass

                    #api_source.name = _from + "_src"
                    api_source.name = headnode + "_src"

                    try:
                        # Lusha
                        if float(source_equivalent_data["voltage"]) != 0:
                            api_source.nominal_voltage = (
                                float(source_equivalent_data["voltage"]) * 10 ** 3
                            )
                        else:
                            api_source.nominal_voltage = (
                                    float(source_equivalent_data["operatingvoltage1"]) * 10 ** 3 * math.sqrt(3)
                            )
                    except:
                        pass

                    try:
                        api_source.phases = phases # didn't assign this
                    except:
                        pass

                    api_source.is_sourcebus = True

                    try:
                        api_source.rated_power = 10 ** 3 * float(
                            source_equivalent_data["mva"]
                        )  # Modified from source cases where substations can be used.
                    except:
                        pass

                    # TODO: connection_type

                    try:
                        api_source.phase_angle = source_equivalent_data["operatingangle1"]
                    except:
                        pass

                    # try:
                    if "positivesequenceresistance" in source_equivalent_data:
                        api_source.positive_sequence_impedance = complex(
                            float(source_equivalent_data["positivesequenceresistance"]),
                            float(source_equivalent_data["positivesequencereactance"]),
                        )
                    else:
                        api_source.positive_sequence_impedance = complex(
                            float(source_equivalent_data["firstlevelr1"]),
                            float(source_equivalent_data["firstlevelx1"]),
                        )

                    # except:
                    # pass

                    if "zerosequenceresistance" in source_equivalent_data:
                        api_source.zero_sequence_impedance = complex(
                            float(source_equivalent_data["zerosequenceresistance"]),
                            float(source_equivalent_data["zerosequencereactance"]),
                        )
                    else:
                        api_source.zero_sequence_impedance = complex(
                            float(source_equivalent_data["firstlevelr0"]),
                            float(source_equivalent_data["firstlevelx0"]),
                        )

                    try:
                        #Lusha
                        #api_source.connecting_element = _from
                        api_source.connecting_element = headnode
                    except:
                        pass
                    # Lusha
                    # mark the feeder model with source
                    model.assigned_source = 1

                #self.sub_source_flag[subname] = 1

        # store source
        for sid, sdata in sources.items():

            source_equivalent_data = None

            if "nodeid" in sdata and sdata["nodeid"] in source_equivalents:
                source_equivalent_data = source_equivalents[sdata["nodeid"]]

            if sid in subs:
                # Lusha
                if sdata["nodeid"] not in self.headnode_sub_mapping.keys():
                    continue
                subname = self.headnode_sub_mapping[sdata["nodeid"]]
                feeders = self.sub_feeder_mapping[subname]

                # already assigned sources to feeders in sub
                # if self.sub_source_flag[subname] == 1:
                #     continue

                # Find the section
                # for k, v in self.section_phase_mapping.items():
                #     if v["fromnodeid"] == sdata["nodeid"]:
                #         sectionID = k
                #         _from = v["fromnodeid"]
                #         _to = v["tonodeid"]
                #         phases = list(v["phase"])
                #     if v["tonodeid"] == sdata["nodeid"]: #If it's backwards
                #         sectionID = k
                #         _to = v["fromnodeid"]
                #         _from = v["tonodeid"]
                #         phases = list(v["phase"])

                # Lusha
                # for each feeder in the substation, assign a new source
                # connect the new source to the exsiting feeder headnode
                for feedername in feeders:
                    try:
                        # Lusha
                        headnode = self.feeder_headnode_mapping[feedername]
                        model = self.feeder_models[feedername]
                        if model.assigned_source == 1:
                            continue
                        api_source = PowerSource(model)
                        model.source = api_source
                    except:
                        pass

                    # Lusha
                    #api_source.name = _from + "_src"
                    api_source.name = headnode + "_src"

                    try:
                        # Lusha
                        # if "desiredvoltage" in sdata:
                        #     api_source.nominal_voltage = (
                        #         float(sdata["desiredvoltage"]) * 10 ** 3
                        #     )
                        if "operatingvoltagea" in sdata:
                            api_source.nominal_voltage = (
                                float(sdata["operatingvoltagea"]) * 10 ** 3
                            )
                        else:
                            api_source.nominal_voltage = (
                                float(source_equivalent_data["voltage"]) * 10 ** 3
                            )
                        model.source_voltage = api_source.nominal_voltage
                    except:
                        pass


                    try:
                        api_source.phases = phases
                    except:
                        pass

                    api_source.is_sourcebus = True

                    try:
                        api_source.rated_power = 10 ** 3 * float(subs[sid]["mva"])
                    except:
                        pass

                    # TODO: connection_type

                    try:
                        api_source.phase_angle = source_equivalent_data[
                            "operatingangle1"
                        ]
                    except:
                        pass

                    try:
                        if "positivesequenceresistance" in source_equivalent_data:
                            api_source.positive_sequence_impedance = complex(
                                float(source_equivalent_data["positivesequenceresistance"]),
                                float(source_equivalent_data["positivesequencereactance"]),
                            )
                        else:
                            api_source.positive_sequence_impedance = complex(
                                float(source_equivalent_data["firstlevelr1"]),
                                float(source_equivalent_data["firstlevelx1"]),
                            )
                    except:
                        pass

                    try:
                        if "zerosequenceresistance" in source_equivalent_data:
                            api_source.zero_sequence_impedance = complex(
                                float(source_equivalent_data["zerosequenceresistance"]),
                                float(source_equivalent_data["zerosequencereactance"]),
                            )
                        else:
                            api_source.zero_sequence_impedance = complex(
                                float(source_equivalent_data["firstlevelr0"]),
                                float(source_equivalent_data["firstlevelx0"]),
                            )
                    except:
                        pass

                    try:
                        api_source.zero_sequence_impedance = complex(
                            source_equivalent_data["zerosequenceresistance"],
                            source_equivalent_data["zerosequencereactance"],
                        )
                    except:
                        pass

                    try:
                        #Lusha
                        #api_source.connecting_element = _from
                        # connect the source to the feeder headnode
                        api_source.connecting_element = headnode
                    except:
                        pass

                    # try:
                    #     api_transformer=PowerTransformer(model)
                    # except:
                    #     pass

                    # try:
                    #     api_transformer.is_substation=1
                    # except:
                    #     pass

                    # try:
                    #     api_transformer.name=sid
                    # except:
                    #     pass

                    # try:
                    #     api_transformer.rated_power=10**3*float(subs[sid]['mva'])
                    # except:
                    #     pass

                    # try:
                    #     api_transformer.from_element=_from
                    # except:
                    #     pass

                    # try:
                    #     api_transformer.to_element=_to
                    # except:
                    #     pass

                    # for w in range(2):
                    #     try:
                    #         api_winding=Winding(model)
                    #     except:
                    #         pass

                    #     try:
                    #         api_winding.connection_type=self.transformer_connection_configuration_mapping(subs[sid]['conn'])
                    #     except:
                    #         pass

                    #     try:
                    #         api_winding.nominal_voltage=10**3*float(subs[sid]['kvll'])
                    #     except:
                    #         pass

                    #     try:
                    #         api_winding.rated_power=10**6*float(subs[sid]['mva'])
                    #     except:
                    #         pass

                    #     for p in phases:
                    #         try:
                    #             api_phase_winding=PhaseWinding(model)
                    #         except:
                    #             pass

                    #         try:
                    #             api_phase_winding.phase=self.phase_mapping(p)
                    #         except:
                    #             pass

                    #         api_winding.phase_windings.append(api_phase_winding)

                    #     api_transformer.windings.append(api_winding)
                    # Lusha
                    model.assigned_source = 1
                # self.sub_source_flag[subname] = 1
        '''
        if len(sources.items()) == 0:
            for sid, source_equivalent_data in source_equivalents.items():
                if source_equivalent_data["loadmodelname"].lower() != "default":
                    continue  # Want to only use the default source equivalent configuration

                # Lusha
                subname = self.headnode_sub_mapping[source_equivalent_data["nodeid"]]
                feeders = self.sub_feeder_mapping[subname]

                # already assigned sources to feeders in sub
                if self.sub_source_flag[subname] == 1:
                    continue



                for k, v in self.section_phase_mapping.items():
                    if v["fromnodeid"] == source_equivalent_data["nodeid"]:
                        sectionID = k
                        _from = v["fromnodeid"]
                        _to = v["tonodeid"]
                        phases = list(v["phase"])
                    if (
                        v["tonodeid"] == source_equivalent_data["nodeid"]
                    ):  # In case the edge is connected backwards
                        sectionID = k
                        _from = v["tonodeid"]
                        _to = v["fromnodeid"]
                        phases = list(v["phase"])

                # Lusha
                for feedername in feeders:
                    try:
                        # Lusha
                        headnode = self.feeder_headnode_mapping[feedername]
                        model = self.feeder_models[feedername]
                        api_source = PowerSource(model)
                    except:
                        pass

                    #api_source.name = _from + "_src"
                    api_source.name = headnode + "_src"

                    try:
                        api_source.nominal_voltage = (
                            float(source_equivalent_data["voltage"]) * 10 ** 3
                        )
                    except:
                        pass

                    try:
                        api_source.phases = phases
                    except:
                        pass

                    api_source.is_sourcebus = True

                    try:
                        api_source.rated_power = 10 ** 3 * float(
                            source_equivalent_data["mva"]
                        )  # Modified from source cases where substations can be used.
                    except:
                        pass

                    # TODO: connection_type

                    try:
                        api_source.phase_angle = source_equivalent_data["operatingangle1"]
                    except:
                        pass

                    # try:
                    if "positivesequenceresistance" in source_equivalent_data:
                        api_source.positive_sequence_impedance = complex(
                            float(source_equivalent_data["positivesequenceresistance"]),
                            float(source_equivalent_data["positivesequencereactance"]),
                        )
                    else:
                        api_source.positive_sequence_impedance = complex(
                            float(source_equivalent_data["firstlevelr1"]),
                            float(source_equivalent_data["firstlevelx1"]),
                        )

                    # except:
                    # pass

                    if "zerosequenceresistance" in source_equivalent_data:
                        api_source.zero_sequence_impedance = complex(
                            float(source_equivalent_data["zerosequenceresistance"]),
                            float(source_equivalent_data["zerosequencereactance"]),
                        )
                    else:
                        api_source.zero_sequence_impedance = complex(
                            float(source_equivalent_data["firstlevelr0"]),
                            float(source_equivalent_data["firstlevelx0"]),
                        )

                    try:
                        #Lusha
                        #api_source.connecting_element = _from
                        api_source.connecting_element = headnode
                    except:
                        pass

        else:
            for sid, sdata in sources.items():

                source_equivalent_data = None

                if "nodeid" in sdata and sdata["nodeid"] in source_equivalents:
                    source_equivalent_data = source_equivalents[sdata["nodeid"]]

                if sid in subs:
                    # Lusha
                    subname = self.headnode_sub_mapping[sdata["nodeid"]]
                    feeders = self.sub_feeder_mapping[subname]

                    # already assigned sources to feeders in sub
                    if self.sub_source_flag[subname] == 1:
                        continue

                    # Find the section
                    for k, v in self.section_phase_mapping.items():
                        if v["fromnodeid"] == sdata["nodeid"]:
                            sectionID = k
                            _from = v["fromnodeid"]
                            _to = v["tonodeid"]
                            phases = list(v["phase"])
                        if v["tonodeid"] == sdata["nodeid"]: #If it's backwards
                            sectionID = k
                            _to = v["fromnodeid"]
                            _from = v["tonodeid"]
                            phases = list(v["phase"])

                    # Lusha
                    # for each feeder in the substation, assign a new source
                    # connect the new source to the exsiting feeder headnode
                    for feedername in feeders:
                        try:
                            # Lusha
                            headnode = self.feeder_headnode_mapping[feedername]
                            model = self.feeder_models[feedername]
                            api_source = PowerSource(model)
                        except:
                            pass

                        # Lusha
                        #api_source.name = _from + "_src"
                        api_source.name = headnode + "_src"

                        try:
                            if "desiredvoltage" in sdata:
                                api_source.nominal_voltage = (
                                    float(sdata["desiredvoltage"]) * 10 ** 3
                                )
                            else:
                                api_source.nominal_voltage = (
                                    float(source_equivalent_data["voltage"]) * 10 ** 3
                                )
                        except:
                            pass

                        try:
                            api_source.phases = phases
                        except:
                            pass

                        api_source.is_sourcebus = True

                        try:
                            api_source.rated_power = 10 ** 3 * float(subs[sid]["mva"])
                        except:
                            pass

                        # TODO: connection_type

                        try:
                            api_source.phase_angle = source_equivalent_data[
                                "operatingangle1"
                            ]
                        except:
                            pass

                        # try:
                        if "positivesequenceresistance" in source_equivalent_data:
                            api_source.positive_sequence_impedance = complex(
                                float(source_equivalent_data["positivesequenceresistance"]),
                                float(source_equivalent_data["positivesequencereactance"]),
                            )
                        else:
                            api_source.positive_sequence_impedance = complex(
                                float(source_equivalent_data["firstlevelr1"]),
                                float(source_equivalent_data["firstlevelx1"]),
                            )
                        # except:
                        # pass
                        if "zerosequenceresistance" in source_equivalent_data:
                            api_source.zero_sequence_impedance = complex(
                                float(source_equivalent_data["zerosequenceresistance"]),
                                float(source_equivalent_data["zerosequencereactance"]),
                            )
                        else:
                            api_source.zero_sequence_impedance = complex(
                                float(source_equivalent_data["firstlevelr0"]),
                                float(source_equivalent_data["firstlevelx0"]),
                            )


                        try:
                            api_source.zero_sequence_impedance = complex(
                                source_equivalent_data["zerosequenceresistance"],
                                source_equivalent_data["zerosequencereactance"],
                            )
                        except:
                            pass

                        try:
                            #Lusha
                            #api_source.connecting_element = _from
                            # connect the source to the feeder headnode
                            api_source.connecting_element = headnode
                        except:
                            pass

                        # try:
                        #     api_transformer=PowerTransformer(model)
                        # except:
                        #     pass

                        # try:
                        #     api_transformer.is_substation=1
                        # except:
                        #     pass

                        # try:
                        #     api_transformer.name=sid
                        # except:
                        #     pass

                        # try:
                        #     api_transformer.rated_power=10**3*float(subs[sid]['mva'])
                        # except:
                        #     pass

                        # try:
                        #     api_transformer.from_element=_from
                        # except:
                        #     pass

                        # try:
                        #     api_transformer.to_element=_to
                        # except:
                        #     pass

                        # for w in range(2):
                        #     try:
                        #         api_winding=Winding(model)
                        #     except:
                        #         pass

                        #     try:
                        #         api_winding.connection_type=self.transformer_connection_configuration_mapping(subs[sid]['conn'])
                        #     except:
                        #         pass

                        #     try:
                        #         api_winding.nominal_voltage=10**3*float(subs[sid]['kvll'])
                        #     except:
                        #         pass

                        #     try:
                        #         api_winding.rated_power=10**6*float(subs[sid]['mva'])
                        #     except:
                        #         pass

                        #     for p in phases:
                        #         try:
                        #             api_phase_winding=PhaseWinding(model)
                        #         except:
                        #             pass

                        #         try:
                        #             api_phase_winding.phase=self.phase_mapping(p)
                        #         except:
                        #             pass

                        #         api_winding.phase_windings.append(api_phase_winding)

                        #     api_transformer.windings.append(api_winding)

                    self.sub_source_flag[subname] = 1
        '''

    def parse_nodes(self, model=None):
        print("Inside parse_nodes")
        """
        Parse the nodes from CYME to DiTTo.

        :param model: DiTTo model
        :type model: DiTTo model
        """
        self._nodes = []

        try:
            # Open the network file
            #self.get_file_content("network")
            self.content = iter(self.file_network_node)
            # Default mapp (positions if all fields are present in the format)
            mapp = {
                "nodeid": 0,
                "ratedvoltage": 48,
                "coordx": 2,
                "coordy": 3,
                "coordx1": 2,
                "coordy1": 3,
                "coordx2": 4,
                "coordy2": 5,
            }
        except:
            pass

        nodes = {}
        node_connectors = {}

        kwargs = {
            "additional_attributes_list": [
                "nodeid",
                "coordx1",
                "coordy1",
                "coordx2",
                "coordy2",
                "ratedvoltage",
            ]
        }  # In case there are buses included in the node list with x1, y1, x2, y2 positions
        #for line in self.content:
        line = next(self.content)
        nodes.update(
            self.parser_helper(
                line,
                ["node"],
                ["nodeid", "coordx", "coordy", "ratedvoltage"],
                mapp,
                **kwargs
            )
        )
        #self.get_file_content("network")
        #for line in self.content:
        try:
            self.content = iter(self.file_network_node)
            line = next(self.content)
            node_connectors.update(
                self.parser_helper(
                    line, ["node_connector"], ["nodeid", "coordx", "coordy"], mapp
                )
            )
        except:
            pass

        for ID, node in nodes.items():
            # Lusha
            try:
                feeders = self.node_feeder_mapping[node["nodeid"]]
                # if len(feeders) > 1:
                #     print(node["nodeid"])
            except:
                print("No feeder found for node: " + str(node["nodeid"]))
                continue

            # add node to each feeder that contains it
            for feedername in feeders:
                model = self.feeder_models[feedername]
                # Create a new DiTTo node object
                api_node = Node(model)

                try:
                    api_node.feeder_name = feedername
                except:
                    print("no feedername for node "+ str(ID))
                    pass

                try:
                    api_node.substation_name = self.feeder_sub_mapping[feedername]
                except:
                    api_node.substation_name = api_node.feeder_name
                    pass

                # Set the name
                try:
                    api_node.name = ID
                except:
                    pass

                # Set the coordinates
                try:
                    if "coordx" in node:
                        position = Position(model)
                        position.long = float(node["coordx"])
                        position.lat = float(node["coordy"])
                        position.elevation = 0
                        api_node.positions.append(position)
                    elif "coordx1" in node:
                        api_node.positions = []
                        position1 = Position(model)
                        position1.long = float(node["coordx1"])
                        position1.lat = float(node["coordy1"])
                        position1.elevation = 0
                        api_node.positions.append(position1)
                        if ID in node_connectors:
                            ID_inc = ID
                            while ID_inc in node_connectors:
                                values = node_connectors[ID_inc]
                                position_i = Position(model)
                                position_i.long = float(values["coordx"])
                                position_i.lat = float(values["coordy"])
                                position_i.elevation = 0
                                api_node.positions.append(position_i)
                                ID_inc += "*"
                        position2 = Position(model)
                        position2.long = float(node["coordx2"])
                        position2.lat = float(node["coordy2"])
                        position2.elevation = 0
                        api_node.positions.append(position2)
                except:
                    pass

                # Set the nominal voltage
                try:
                    api_node.nominal_voltage = float(node["ratedvoltage"])
                except:
                    pass

                # Add the node to the list
                self._nodes.append(api_node)

        return 1

    def configure_wire(
        self,
        model,
        conductor_data,
        spacing_data,
        phase,
        is_switch,
        is_fuse,
        is_open,
        is_network_protector,
        is_breaker,
        is_recloser,
        is_sectionalizer,
    ):
        """Helper function that creates a DiTTo wire object and configures it."""
        # Instanciate the wire DiTTo object
        api_wire = Wire(model)

        # Set the phase of the wire
        try:
            api_wire.phase = phase
        except:
            pass

        try:
            api_wire.nameclass = conductor_data["id"]
        except:
            pass

        # Set the flags
        api_wire.is_switch = is_switch
        api_wire.is_open = is_open
        api_wire.is_fuse = is_fuse
        api_wire.is_network_protector = is_network_protector
        api_wire.is_breaker = is_breaker
        api_wire.is_recloser = is_recloser
        api_wire.is_sectionalizer = is_sectionalizer

        # Set the diameter of the wire
        try:
            api_wire.diameter = float(conductor_data["diameter"])
        except:
            pass

        # Set the nameclass
        try:
            api.wire.nameclass = conductor_data["nameclass"]
        except:
            pass

        # Set the GMR of the wire
        try:
            api_wire.gmr = float(conductor_data["gmr"])
        except:
            pass

        # Set the ampacity of the wire
        try:
            api_wire.ampacity = float(conductor_data["amps"])
        except:
            api_wire.ampacity = 10000
            pass

        # Set the interupting current of the wire if it is a network protectors, a fuse, a sectionalizer, a breaker, or a recloser
        if (
            is_network_protector
            or is_fuse
            or is_sectionalizer
            or is_breaker
            or is_recloser
        ):
            try:
                api_wire.interrupting_rating = float(
                    conductor_data["interruptingrating"]
                )
            except:
                pass

        # Set the emergency ampacity of the wire
        try:
            api_wire.emergency_ampacity = float(conductor_data["withstandrating"])
        except:
            pass

        # Set the X spacing
        x_map = {
            "A": "posofcond1_x",
            "B": "posofcond2_x",
            "C": "posofcond3_x",
            "N": "posofneutralcond_x",
            "N2": "posofneutralcond_n2_x",
        }
        try:
            api_wire.X = spacing_data[x_map[phase]]
        except:
            pass

        # Set the Y spacing
        y_map = {
            "A": "posofcond1_y",
            "B": "posofcond2_y",
            "C": "posofcond3_y",
            "N": "posofneutralcond_y",
            "N2": "posofneutralcond_n2_y",
        }
        try:
            api_wire.Y = spacing[y_map[phase]]
        except:
            pass

        return api_wire

    def parse_sections(self, model=None):
        print("Inside parse_section")
        """
        This function is responsible for parsing the sections. It is expecting the following structure:
        ...

        [SECTION]
        FORMAT_section=sectionid,fromnodeid,tonodeid,phase
        FORMAT_Feeder=networkid,headnodeid
        Feeder=feeder_1,head_feeder_1
        section_1_feeder_1,node_1,node_2,ABC
        ...
        ...
        Feeder=feeder_2,head_feeder_2
        section_1_feeder_2,node_1,node_2,ABC
        ...
        ...

        **What is done in this function:**

        - We need to create a clear and fast mapping between feeders and sectionids
        - Same thing, mapping between sectionids and nodes/phases
        - Since we will be using these structures a lot in the reader, we need something fast that does not involve looping like crazy

        **Data structures:**

        1) feeder_section_mapping: dictionary where keys are network_ids and values are lists of section id_s
        2) section_feeder_mapping: dictionary where keys are section ids and values are network_ids
           (to perform the opposite query as 1) without having to look in every lists of section ids until we find the good one...)
        3) section_phase_mapping: dictionary where keys are section ids and values are tuples (node_1, node_2, phase)

        .. warning:: This should be called prior to any other parser because the other parsers rely on these 3 data structures.
        """
        self.feeder_section_mapping = {}
        self.section_feeder_mapping = {}
        self.section_phase_mapping = {}

        self.network_data = {}

        # Lusha
        self.feeder_models = {}
        self.node_feeder_mapping = {}

        format_section = None
        format_feeder = None
        _netID = None

        job_is_done = False

        # Open the network file
        #self.get_file_content("network")
        # Loop over the network file
        #for line in self.content:
        for line in self.file_network_section:

            if line.startswith("["):
                continue

            # First, we grab the format used to define sections
            if "format_section" in line.lower():
                format_section = list(
                    map(
                        lambda x: x.strip(),
                        map(lambda x: x.lower(), line.split("=")[1].split(",")),
                    )
                )

            # Then, we grab the format used to define feeders
            elif (
                "format_feeder" in line.lower()
                or "format_substation" in line.lower()
                or "format_generalnetwork" in line.lower()
            ):
                format_feeder = list(
                    map(
                        lambda x: x.strip(),
                        map(lambda x: x.lower(), line.split("=")[1].split(",")),
                    )
                )

            # If we have a new feeder declaration
            elif len(line) >= 7 and (
                line[:7].lower() == "feeder="
                or line[:11].lower() == "substation="
                or line[:11].lower() == "substation="
                or line[:15].lower() == "generalnetwork="
            ):
                if (
                    line[:7].lower() == "feeder="
                    or line[:15].lower() == "generalnetwork="
                ):
                    # Lusha
                    model = Store()
                    model.network_type = "feeder"
                    model.assigned_source = 0
                    #self.network_type = "feeder"
                if line[:11].lower() == "substation=":
                    # Lusha
                    model = Store()
                    model.network_type = "substation"
                    #self.network_type = "substation"


                # We should have a format for sections and feeders,
                # otherwise, raise an error...
                if format_section is None:
                    raise ValueError("No format for sections.")

                if format_feeder is None:
                    raise ValueError("No format for feeders.")

                # Get the feeder data (everything after the '=' symbol)
                feeder_data = line.split("=")[1].split(",")

                # Check that the data obtained have the same length as the format provided
                # otherwise, raise an error...
                if len(feeder_data) != len(format_feeder):
                    raise ValueError(
                        "Feeder/substation data length {a} does not match feeder format length {b}.".format(
                            a=len(feeder_data), b=len(format_feeder)
                        )
                    )

                # Check that we have a networkid in the format
                # otherwise, raise an error...
                if "networkid" not in format_feeder:
                    raise ValueError(
                        "Cannot find the networkid in format: "
                        + str(format_feeder)
                    )

                # Check that we have a sectionid in the format
                # otherwise, raise an error...
                if "sectionid" not in format_section:
                    raise ValueError(
                        "Cannot find the sectionid in format: "
                        + str(format_section)
                    )

                # We should be able to get the networkid from the feeder data.
                _netID = feeder_data[format_feeder.index("networkid")].lower()

                # First, we store all the feeder data in the network_data structure
                self.network_data[_netID] = {}
                for key, value in zip(format_feeder, feeder_data):
                    self.network_data[_netID][key] = value


                # Then, we create a new entry in feeder_section_mapping
                self.feeder_section_mapping[_netID] = []

                # Lusha
                self.feeder_models[_netID] = model



            # Otherwise, we should have a new section...
            else:
                # If we have no networkid at this point, raise an error
                # Note: If CYME allows sections to be define without
                # a network, remove this safety check
                #
                if _netID is None:
                    raise ValueError(
                        "No network ID available when reading line \n" + line
                    )
                # Extract the data for this section
                section_data = list(map(lambda x: x.strip(), line.split(",")))

                # Check length coherence...
                if len(section_data) != len(format_section):
                    raise ValueError(
                        "Section data length {a} does not match section format length {b}.".format(
                            a=len(section_data), b=len(format_section)
                        )
                    )

                # Grab the sectionid
                _sectionID = section_data[
                    format_section.index("sectionid")
                ].lower()

                # Create a new entry in section_phase_mapping
                self.section_phase_mapping[_sectionID] = {}

                # Populate this new entry
                for key, value in zip(format_section, section_data):
                    self.section_phase_mapping[_sectionID][key] = value

                # And finally, add a new entry to section_feeder_mapping
                self.section_feeder_mapping[_sectionID] = _netID

                # Lusha
                self.feeder_section_mapping[_netID].append(_sectionID)



    def parse_lines(self, model=None):
        """
        Parse the lines from CYME to DiTTo.

        :param model: DiTTo model
        :type model: DiTTo model
        """
        # Default mapp (positions if all fields are present in the format)
        # These numbers come from the CYME documentation (position of the fields)
        mapp_overhead = {
            "sectionid": 0,
            "linecableid": 5,
            "length": 6,
            "coordx": 8,
            "coordy": 9,
        }
        mapp_overhead_byphase = {
            "sectionid": 0,
            "devicenumber": 1,
            "condid_a": 5,
            "condid_b": 6,
            "condid_c": 7,
            "condid_n1": 8,
            "condid_n2": 9,
            "spacingid": 10,
            "length": 11,
            "coordx": 14,
            "coordy": 15,
        }
        mapp_underground = {
            "sectionid": 0,
            "linecableid": 5,
            "length": 6,
            "amps": 8,
            "coordx": 14,
            "coordy": 15,
        }
        mapp_switch = {
            "sectionid": 0,
            "eqid": 2,
            "coordx": 7,
            "coordy": 8,
            "closedphase": 9,
        }
        mapp_sectionalizer = {"sectionid": 0, "eqid": 2, "coordx": 7, "coordy": 8}
        mapp_line = {
            "id": 0,
            "phasecondid": 1,
            "neutralcondid": 2,
            "spacingid": 3,
            "amps": 11,
            "r1": 5,
            "r0": 6,
            "x1": 7,
            "x0": 8,
            "b1": 9,
            "b0": 10,
        }
        mapp_section = {"sectionid": 0, "fromnodeid": 1, "tonodeid": 2, "phase": 3}
        mapp_line_unbalanced = {
            "id": 0,
            "condid_a": 1,
            "condid_b": 2,
            "condid_c": 3,
            "condid_n1": 4,
            "condid_n2": 5,
            "spacingid": 6,
            "ra": 8,
            "rb": 9,
            "rc": 10,
            "xa": 11,
            "xb": 12,
            "xc": 13,
            "ba": 14,
            "bb": 15,
            "bc": 16,
            "mutualresistanceab": 36,
            "mutualresistancebc": 37,
            "mutualresistanceca": 38,
            "mutualreactanceab": 39,
            "mutualreactancebc": 40,
            "mutualreactanceca": 41,
        }
        mapp_spacing = {
            "id": 0,
            "posofcond1_x": 5,
            "posofcond1_y": 6,
            "posofcond2_x": 7,
            "posofcond2_y": 8,
            "posofcond3_x": 9,
            "posofcond3_y": 10,
            "posofneutralcond_x": 11,
            "posofneutralcond_y": 12,
            "posofneutralcond_n2_x": 13,
            "posofneutralcond_n2_y": 14,
        }
        mapp_conductor = {
            "id": 0,
            "diameter": 1,
            "gmr": 2,
            "amps": 5,
            "withstandrating": 15,
        }
        mapp_cable = {"id": 0, "r1": 1, "r0": 2, "x1": 3, "x0": 4, "amps": 7}
        mapp_concentric_neutral_cable = {
            "id": 0,
            "r1": 1,
            "r0": 2,
            "x1": 3,
            "x0": 4,
            "amps": 5,
            "phasecondid": 19,
            "neutralcondid": 20,
        }

        mapp_network_protectors = {
            "id": 0,
            "amps": 1,
            "kvll": 6,
            "interruptingrating": 8,
        }

        mapp_sectionalizers = {"id": 0, "amps": 1, "kvll": 6, "interruptingrating": 20}

        mapp_switch_eq = {"id": 0, "amps": 1, "kvll": 6}

        # Instanciate the lists for storing objects
        self.overhead_lines = []
        self.underground_lines = []
        self.sections = []
        # self.lines=[]
        self.lines_unbalanced = []
        # self.spacings=[]
        # self.conductors=[]
        self.overhead_by_phase = []

        self.balanced_lines = {}
        self.unbalanced_lines = {}
        self.settings = {}
        self.spacings = {}
        self.conductors = {}
        self.concentric_neutral_cable = {}
        self.cables = {}

        self.network_protectors = {}
        self.breakers = {}
        self.fuses = {}
        self.reclosers = {}
        self.sectionalizers = {}
        self.switches = {}

        # Instanciate the list in which we store the DiTTo line objects
        self._lines = []

        self.section_phase = {}

        mapp_closed_phase = {
            0: "none",
            1: "A",
            2: "B",
            3: "C",
            4: "AB",
            5: "AC",
            6: "BC",
            7: "ABC",
            "0": "none",
            "1": "A",
            "2": "B",
            "3": "C",
            "4": "AB",
            "5": "AC",
            "6": "BC",
            "7": "ABC",
            "none": "none",
            "NONE": "none",
            "A": "A",
            "B": "B",
            "C": "C",
            "AB": "AB",
            "AC": "AC",
            "BC": "BC",
            "ABC": "ABC",
        }

        #####################################################
        #                                                   #
        #                   NETWORK FILE                    #
        #                                                   #
        #####################################################
        #
        # Open the network file
        #self.get_file_content("network")

        # Loop over the network file
        # loop over overhead line
        try:
            self.content = iter(self.file_network_line_overhead)
            line = next(self.content)
            #print(line)
            #########################################
            #                                       #
            #      OVERHEAD UNBALANCED LINES        #
            #                                       #
            #########################################
            #
            self.settings = self.update_dict(
                self.settings,
                self.parser_helper(
                    line,
                    ["overhead_unbalanced_line_settings"],
                    ["sectionid", "coordx", "coordy", "linecableid", "length"],
                    mapp_overhead,
                    {"type": "overhead_unbalanced"},
                ),
            )

            #########################################
            #                                       #
            #        OVERHEAD BALANCED LINES        #
            #                                       #
            #########################################
            #
            self.settings = self.update_dict(
                self.settings,
                self.parser_helper(
                    line,
                    ["overhead_line_settings"],
                    ["sectionid", "coordx", "coordy", "linecableid", "length"],
                    mapp_overhead,
                    {"type": "overhead_balanced"},
                ),
            )
        except:
            pass

        # loop over overhead by phase line
        try:
            self.content = iter(self.file_network_line_overhead_byphase)
            line = next(self.content)

            #print(line)
            #########################################
            #                                       #
            #     OVERHEAD BY PHASE SETTINGS        #
            #                                       #
            #########################################
            #
            self.settings = self.update_dict(
                self.settings,
                self.parser_helper(
                    line,
                    ["overhead_byphase_settings"],
                    [
                        "sectionid",
                        "devicenumber",
                        "condid_a",
                        "condid_b",
                        "condid_c",
                        "condid_n",
                        "condid_n1",
                        "condid_n2",
                        "spacingid",
                        "length",
                        "coordx",
                        "coordy",
                    ],
                    mapp_overhead_byphase,
                    {"type": "overhead_unbalanced"},
                ),
            )
        except:
            pass

        # loop over underground line
        try:
            self.content = iter(self.file_network_line_underground)
            line = next(self.content)

            #print(line)
            #########################################
            #                                       #
            #          UNDERGROUND LINES            #
            #                                       #
            #########################################
            #
            self.settings = self.update_dict(
                self.settings,
                self.parser_helper(
                    line,
                    ["underground_line_settings"],
                    ["sectionid", "coordx", "coordy", "linecableid", "length", "amps"],
                    mapp_underground,
                    {"type": "underground"},
                ),
            )
        except:
            pass



        # loop over switch
        try:
            self.content = iter(self.file_network_switch)
            line = next(self.content)
            #print(line)

            #########################################
            #                                       #
            #                SWITCH.                #
            #                                       #
            #########################################
            #
            self.settings = self.update_dict(
                self.settings,
                self.parser_helper(
                    line,
                    ["switch_settings"],
                    ["sectionid", "coordx", "coordy", "eqid", "closedphase"],
                    mapp_switch,
                    {"type": "switch"},
                ),
            )
        except:
            pass

        # loop over sectionalizer
        try:
            self.content = iter(self.file_network_sectionalizer)
            line = next(self.content)
            #print(line)
            #########################################
            #                                       #
            #             SECTIONALIZER.            #
            #                                       #
            #########################################
            #
            self.settings = self.update_dict(
                self.settings,
                self.parser_helper(
                    line,
                    ["sectionalizer_settings"],
                    ["sectionid", "coordx", "coordy", "eqid", "closedphase"],
                    mapp_sectionalizer,
                    {"type": "sectionalizer"},
                ),
            )
        except:
            pass

        # loop over fuse
        try:
            self.content = iter(self.file_network_fuse)
            line = next(self.content)
            #print(line)
            #########################################
            #                                       #
            #                 FUSES.                #
            #                                       #
            #########################################
            #
            self.settings = self.update_dict(
                self.settings,
                self.parser_helper(
                    line,
                    ["fuse_settings"],
                    ["sectionid", "coordx", "coordy", "eqid"],
                    mapp_switch,  # Same as switches
                    {"type": "fuse"},
                ),
            )
        except:
            pass

        # loop over recloser
        try:
            self.content = iter(self.file_network_recloser)
            line = next(self.content)
            #print(line)
            #########################################
            #                                       #
            #              RECLOSERS.               #
            #                                       #
            #########################################
            #
            self.settings = self.update_dict(
                self.settings,
                self.parser_helper(
                    line,
                    ["recloser_settings"],
                    ["sectionid", "coordx", "coordy", "eqid"],
                    mapp_switch,  # Same as switches
                    {"type": "recloser"},
                ),
            )
        except:
            pass


        # loop over breaker
        try:
            self.content = iter(self.file_network_breaker)
            line = next(self.content)
            #print(line)
            #########################################
            #                                       #
            #               BREAKER.                #
            #                                       #
            #########################################
            #
            self.settings = self.update_dict(
                self.settings,
                self.parser_helper(
                    line,
                    ["breaker_settings"],
                    ["sectionid", "coordx", "coordy", "eqid", "closedphase"],
                    mapp_switch,  # Same as switches
                    {"type": "breaker"},
                ),
            )
        except:
            pass

        # loop over network protector
        # self.content = iter(self.file_network_protector)
        # line = next(self.content)
        # while line:
        #     print(line)
        #     #########################################
        #     #                                       #
        #     #         NETWORK PROTECTORS.           #
        #     #                                       #
        #     #########################################
        #     #
        #     self.settings = self.update_dict(
        #         self.settings,
        #         self.parser_helper(
        #             line,
        #             ["network_protector_settings"],
        #             ["sectionid", "coordx", "coordy", "eqid", "closedphase"],
        #             mapp_switch,  # Same as switches
        #             {"type": "network_protector"},
        #         ),
        #     )
        #

        try:
            # loop over section
            self.content = iter(self.file_network_section)
            line = next(self.content)
            #print(line)
            #########################################
            #                                       #
            #              SECTIONS.                #
            #                                       #
            #########################################
            #
            self.settings = self.update_dict(
                self.settings,
                self.parser_helper(
                    line,
                    ["section"],
                    ["sectionid", "fromnodeid", "tonodeid", "phase"],
                    mapp_section,
                ),
            )
        except:
            pass

        #####################################################
        #                                                   #
        #                 EQUIPMENT FILE                    #
        #                                                   #
        #####################################################
        #
        # Open the equipment file
        #self.get_file_content("equipment")

        # Loop over the equipment file
        #for line in self.content:
            #print(line)
        try:
            self.content = iter(self.file_equipment_line)
            line = next(self.content)
            #print(line)
            #########################################
            #                                       #
            #                 LINES.                #
            #                                       #
            #########################################
            #
            self.balanced_lines.update(
                self.parser_helper(
                    line,
                    ["line"],
                    [
                        "id",
                        "phasecondid",
                        "neutralcondid",
                        "spacingid",
                        "amps",
                        "r1",
                        "r0",
                        "x1",
                        "x0",
                        "b1",
                        "b0",
                    ],
                    mapp_line,
                    {"type": "balanced_line"},
                )
            )
        except:
            pass

        try:
            self.content = iter(self.file_equipment_line_unbalanced)
            line = next(self.content)
            #print(line)
            #########################################
            #                                       #
            #          UNBALANCED LINES.            #
            #                                       #
            #########################################
            #
            self.unbalanced_lines.update(
                self.parser_helper(
                    line,
                    ["unbalanced_line"],
                    [
                        "id",
                        "condid_a",
                        "condid_b",
                        "condid_c",
                        "condid_n",
                        "condid_n1",
                        "condid_n2",
                        "spacingid",
                        "ra",
                        "rb",
                        "rc",
                        "xa",
                        "xb",
                        "xc",
                        "ba",
                        "bb",
                        "bc",
                        "mutualresistanceab",
                        "mutualresistancebc",
                        "mutualresistanceca",
                        "mutualreactanceab",
                        "mutualreactancebc",
                        "mutualreactanceca",
                    ],
                    mapp_line_unbalanced,
                    {"type": "unbalanced_line"},
                )
            )
        except:
            pass

        try:
            self.content = iter(self.file_equipment_spacing)
            line = next(self.content)
            #print(line)
            #########################################
            #                                       #
            #             SPACING TABLE             #
            #                                       #
            #########################################
            #
            self.spacings.update(
                self.parser_helper(
                    line,
                    ["spacing_table"],
                    [
                        "id",
                        "posofcond1_x",
                        "posofcond1_y",
                        "posofcond2_x",
                        "posofcond2_y",
                        "posofcond3_x",
                        "posofcond3_y",
                        "posofneutralcond_x",
                        "posofneutralcond_y",
                        "posofneutralcond_n2_x",
                        "posofneutralcond_n2_y",
                    ],
                    mapp_spacing,
                )
            )
        except:
            pass

        try:
            self.content = iter(self.file_equipment_conductor)
            line = next(self.content)
            #print(line)
            #########################################
            #                                       #
            #              CONDUCTOR                #
            #                                       #
            #########################################
            #
            self.conductors.update(
                self.parser_helper(
                    line,
                    ["conductor"],
                    ["id", "diameter", "gmr", "r25", "amps", "withstandrating"],
                    mapp_conductor,
                )
            )
        except:
            pass

        try:
            self.content = iter(self.file_equipment_cable_concentric_neutral)
            line = next(self.content)
            #print(line)
            #########################################
            #                                       #
            #       CONCENTRIC NEUTRAL CABLE        #
            #                                       #
            #########################################
            #
            self.concentric_neutral_cable.update(
                self.parser_helper(
                    line,
                    ["concentric_neutral_cable"],
                    [
                        "id",
                        "r1",
                        "r0",
                        "x1",
                        "x0",
                        "amps",
                        "phasecondid",
                        "neutralcondid",
                    ],
                    mapp_concentric_neutral_cable,
                )
            )
        except:
            pass

        try:
            self.content = iter(self.file_equipment_cable)
            line = next(self.content)
            #print(line)
            #########################################
            #                                       #
            #                 CABLE                 #
            #                                       #
            #########################################
            #
            self.cables.update(
                self.parser_helper(
                    line,
                    ["cable"],
                    ["id", "r1", "r0", "x1", "x0", "amps"],
                    mapp_concentric_neutral_cable,
                )
            )
        except:
            pass

        try:
            self.content = iter(self.file_equipment_switch)
            line = next(self.content)
            #########################################
            #                                       #
            #               SWITCHES                #
            #                                       #
            #########################################
            #
            self.switches.update(
                self.parser_helper(
                    line, ["switch"], ["id", "amps", "kvll"], mapp_switch_eq
                )
            )
        except:
            pass

        try:
            self.content = iter(self.file_equipment_fuse)
            line = next(self.content)
            #print(line)
            #########################################
            #                                       #
            #                 FUSES                 #
            #                                       #
            #########################################
            #
            self.fuses.update(
                self.parser_helper(
                    line,
                    ["fuse"],
                    ["id", "amps", "kvll", "interruptingrating"],
                    mapp_network_protectors,  # Same as network protectors
                )
            )
        except:
            pass

        try:
            self.content = iter(self.file_equipment_recloser)
            line = next(self.content)
            #print(line)
            #########################################
            #                                       #
            #             RECLOSERS                 #
            #                                       #
            #########################################
            #
            self.reclosers.update(
                self.parser_helper(
                    line,
                    ["recloser"],
                    ["id", "amps", "kvll", "interruptingrating"],
                    mapp_network_protectors,  # Same as network protectors
                )
            )
        except:
            pass

        try:
            self.content = iter(self.file_equipment_sectionalizer)
            line = next(self.content)
            #print(line)
            #########################################
            #                                       #
            #          SECTIONALIZERS               #
            #                                       #
            #########################################
            #
            self.sectionalizers.update(
                self.parser_helper(
                    line,
                    ["sectionalizer"],
                    ["id", "amps", "kvll", "interruptingrating"],
                    mapp_sectionalizers,
                )
            )
        except:
            pass

        try:
            self.content = iter(self.file_equipment_breaker)
            line = next(self.content)
            #print(line)
            #########################################
            #                                       #
            #               BREAKERS                #
            #                                       #
            #########################################
            #
            self.breakers.update(
                self.parser_helper(
                    line,
                    ["breaker"],
                    ["id", "amps", "kvll", "interruptingrating"],
                    mapp_network_protectors,  # Same as network protectors
                )
            )
        except:
            pass


        # #########################################
        # #                                       #
        # #         NETWORK PROTECTORS            #
        # #                                       #
        # #########################################
        # #
        # self.network_protectors.update(
        #     self.parser_helper(
        #         line,
        #         ["network_protector"],
        #         ["id", "amps", "kvll", "interruptingrating"],
        #         mapp_network_protectors,
        #     )
        # )

        #####################################################
        #                                                   #
        #       JOIN LISTS AND CREATE DITTO OBJECTS         #
        #                                                   #
        #####################################################
        #
        # At this point, we should have all the line data in multiple list of dictionaries.
        # We have then to put everything back together using the foreign keys
        #

        # Lusha
        missing_line = open('missing_line.txt','w')

        section_dict = {}
        # Loop over the sections
        for sectionID, settings in self.settings.items():

            sectionID = sectionID.strip("*").lower()
            #print(sectionID)

            # TODO: CLEAN THIS...
            if (
                "fromnodeid" in settings and (
                    "load" in settings["fromnodeid"].lower()
                    or "load" in settings["tonodeid"].lower()
                )
            ):
                continue

            new_line = {}

            # Lusha
            # check whether sectionID (line) already exisits
            if sectionID in section_dict.keys():
                # print(sectionID)
                # print(section_dict[sectionID])
                # print(settings["type"])
                continue

            # Set the name
            try:
                new_line["name"] = sectionID
            except:
                pass

            # Set the from_element (info is in the section)
            try:
                new_line["from_element"] = self.section_phase_mapping[sectionID][
                    "fromnodeid"
                ]
            except:
                pass

            # Set the to_element (info is in the section)
            try:
                new_line["to_element"] = self.section_phase_mapping[sectionID][
                    "tonodeid"
                ]
            except:
                pass

            # Set the connection index for the from_element (info is in the section)
            try:
                new_line["from_element_connection_index"] = int(
                    self.section_phase_mapping[sectionID]["fromnodeindex"]
                )
            except:
                pass

            # Set the connection index for the from_element (info is in the section)
            try:
                new_line["to_element_connection_index"] = int(
                    self.section_phase_mapping[sectionID]["tonodeindex"]
                )
            except:
                pass

            try:
                phases = list(self.section_phase_mapping[sectionID]["phase"])
            except:
                pass

            # Set the length
            try:
                new_line["length"] = float(settings["length"])
            except:
                # Lusha
                new_line["length"] = 0.0001
                #pass

            try:
                feeder_name = self.section_feeder_mapping[sectionID]
                new_line["feeder_name"] = feeder_name
            except:
                pass

            try:
                new_line["substation_name"] = self.feeder_sub_mapping[feeder_name]
            except:
                #print("feeder name:" + feeder_name)
                new_line["substation_name"]=feeder_name

            # Lusha
            # set node_feeder map
            # one node can be mapped to multiple feeders
            # initiate mapping for the node if not there
            if new_line["from_element"] not in self.node_feeder_mapping.keys():
                self.node_feeder_mapping[new_line["from_element"]] = []
            if new_line["to_element"] not in self.node_feeder_mapping.keys():
                self.node_feeder_mapping[new_line["to_element"]] = []
            # store the feedername if not there
            if new_line["feeder_name"] not in self.node_feeder_mapping[new_line["from_element"]]:
                self.node_feeder_mapping[new_line["from_element"]].append(new_line["feeder_name"])
            if new_line["feeder_name"] not in self.node_feeder_mapping[new_line["to_element"]]:
                self.node_feeder_mapping[new_line["to_element"]].append(new_line["feeder_name"])

            # Set the position
            try:
                # Lusha
                model = self.feeder_models[new_line["feeder_name"]]

                position = Position(model)
                position.long = float(settings["coordx"])
                position.lat = float(settings["coordy"])
                position.elevation = 0
                new_line["position"] = position
            except:
                pass

            # Set the line type
            new_line["is_switch"] = False
            new_line["is_fuse"] = False
            new_line["is_recloser"] = False
            new_line["is_breaker"] = False
            new_line["is_sectionalizer"] = False
            new_line["is_network_protector"] = False

            # Set the nameclass of the line as the equipment ID
            if "eqid" in settings:
                new_line["nameclass"] = settings["eqid"]

            if "type" in settings:

                # Overhead lines
                if "overhead" in settings["type"]:
                    new_line["line_type"] = "overhead"

                # Underground lines
                elif "underground" in settings["type"]:
                    new_line["line_type"] = "underground"

                # Switch
                elif "switch" in settings["type"]:
                    new_line["is_switch"] = True
                    new_line["wires"] = []
                    total_closed = 0

                    # Get and map the closed phases
                    if "closedphase" in settings:
                        closedphase = mapp_closed_phase[settings["closedphase"]]
                    else:
                        closedphase = (
                            "ABC"  # If no info, then everything is closed by default...
                        )

                    # Get the sectionalizer equipment data
                    if "eqid" in settings and settings["eqid"] in self.switches:
                        switch_data = self.switches[settings["eqid"]]
                    else:
                        switch_data = {}

                    # Pass the nameclass to the wires
                    if "nameclass" in new_line:
                        switch_data["nameclass"] = new_line["nameclass"]

                    try:
                        new_line["nominal_voltage"] = float(switch_data["kvll"]) * 1000
                    except:
                        pass

                    # Create the wires
                    for p in phases + ["N"]:
                        if p in closedphase and closedphase.lower() != "none":
                            total_closed += 1
                            api_wire = self.configure_wire(
                                model,
                                switch_data,
                                {},
                                p,
                                True,
                                False,
                                False,
                                False,
                                False,
                                False,
                                False,
                            )
                        elif p == "N" and total_closed >= 1:
                            api_wire = self.configure_wire(
                                model,
                                switch_data,
                                {},
                                p,
                                True,
                                False,
                                False,
                                False,
                                False,
                                False,
                                False,
                            )
                        else:
                            api_wire = self.configure_wire(
                                model,
                                switch_data,
                                {},
                                p,
                                True,
                                False,
                                True,
                                False,
                                False,
                                False,
                                False,
                            )
                        new_line["wires"].append(api_wire)

                    new_line["linecableid"] = "default_"+"_".join(phases)
                    settings["type"] = "default_connection"
                    new_line["nameclass"] = new_line["linecableid"]
                    new_line["line_type"] = "default_connection"
                    new_line["amps"] = float(10000)

                    # api_line = Line(model)
                    # for k, v in new_line.items():
                    #     setattr(api_line, k, v)
                    # if not sectionID in self.section_duplicates:
                    #     self.section_duplicates[sectionID] = []
                    # self.section_duplicates[sectionID].append(api_line)
                    # continue

                # Sectionalizer
                elif "sectionalizer" in settings["type"]:
                    new_line["is_sectionalizer"] = True
                    new_line["wires"] = []
                    total_closed = 0

                    # Get and map the closed phases
                    if "closedphase" in settings:
                        closedphase = mapp_closed_phase[settings["closedphase"]]
                    else:
                        closedphase = (
                            "ABC"  # If no info, then everything is closed by default...
                        )

                    # Get the sectionalizer equipment data
                    if "eqid" in settings and settings["eqid"] in self.sectionalizers:
                        sectionalizer_data = self.sectionalizers[settings["eqid"]]
                    else:
                        sectionalizer_data = {}

                    # Pass the nameclass to the wires
                    if "nameclass" in new_line:
                        sectionalizer_data["nameclass"] = new_line["nameclass"]

                    try:
                        new_line["nominal_voltage"] = (
                            float(sectionalizer_data["kvll"]) * 1000
                        )
                    except:
                        pass

                    # Create the wires
                    for p in phases + ["N"]:
                        if p in closedphase and closedphase.lower() != "none":
                            total_closed += 1
                            api_wire = self.configure_wire(
                                model,
                                sectionalizer_data,
                                {},
                                p,
                                False,
                                False,
                                False,
                                False,
                                False,
                                False,
                                True,
                            )
                        elif p == "N" and total_closed >= 1:
                            api_wire = self.configure_wire(
                                model,
                                sectionalizer_data,
                                {},
                                p,
                                False,
                                False,
                                False,
                                False,
                                False,
                                False,
                                True,
                            )
                        else:
                            api_wire = self.configure_wire(
                                model,
                                sectionalizer_data,
                                {},
                                p,
                                False,
                                False,
                                True,
                                False,
                                False,
                                False,
                                True,
                            )
                        new_line["wires"].append(api_wire)

                    new_line["linecableid"] = "default_"+"_".join(phases)
                    settings["type"] = "default_connection"
                    new_line["nameclass"] = new_line["linecableid"]
                    new_line["line_type"] = "default_connection"
                    new_line["amps"] = float(10000)

                    # api_line = Line(model)
                    # for k, v in new_line.items():
                    #     setattr(api_line, k, v)
                    #
                    # if not sectionID in self.section_duplicates:
                    #     self.section_duplicates[sectionID] = []
                    # self.section_duplicates[sectionID].append(api_line)
                    #
                    # continue

                # Fuse
                elif "fuse" in settings["type"]:
                    new_line["is_fuse"] = True
                    new_line["wires"] = []
                    total_closed = 0

                    # Get and map the closed phases
                    if "closedphase" in settings:
                        closedphase = mapp_closed_phase[settings["closedphase"]]
                    else:
                        closedphase = (
                            "ABC"  # If no info, then everything is closed by default...
                        )

                    # Get the fuse equipment data
                    if "eqid" in settings and settings["eqid"] in self.fuses:
                        fuse_data = self.fuses[settings["eqid"]]
                    else:
                        fuse_data = {}

                    # Pass the nameclass to the wires
                    if "nameclass" in new_line:
                        fuse_data["nameclass"] = new_line["nameclass"]

                    try:
                        new_line["nominal_voltage"] = float(fuse_data["kvll"]) * 1000
                    except:
                        pass

                    # Create the wires
                    for p in phases + ["N"]:
                        if p in closedphase and closedphase.lower() != "none":
                            total_closed += 1
                            api_wire = self.configure_wire(
                                model,
                                fuse_data,
                                {},
                                p,
                                False,
                                True,
                                False,
                                False,
                                False,
                                False,
                                False,
                            )
                        elif p == "N" and total_closed >= 1:
                            api_wire = self.configure_wire(
                                model,
                                fuse_data,
                                {},
                                p,
                                False,
                                True,
                                False,
                                False,
                                False,
                                False,
                                False,
                            )
                        else:
                            api_wire = self.configure_wire(
                                model,
                                fuse_data,
                                {},
                                p,
                                False,
                                True,
                                True,
                                False,
                                False,
                                False,
                                False,
                            )

                        new_line["wires"].append(api_wire)

                    new_line["linecableid"] = "default_"+"_".join(phases)
                    settings["type"] = "default_connection"
                    new_line["nameclass"] = new_line["linecableid"]
                    new_line["line_type"] = "default_connection"
                    new_line["amps"] = float(10000)


                    # api_line = Line(model)
                    # for k, v in new_line.items():
                    #     setattr(api_line, k, v)
                    # if not sectionID in self.section_duplicates:
                    #     self.section_duplicates[sectionID] = []
                    # self.section_duplicates[sectionID].append(api_line)
                    # continue

                # recloser
                elif "recloser" in settings["type"]:
                    new_line["is_recloser"] = True
                    new_line["wires"] = []
                    total_closed = 0

                    # Get and map the closed phases
                    if "closedphase" in settings:
                        closedphase = mapp_closed_phase[settings["closedphase"]]
                    else:
                        closedphase = (
                            "ABC"  # If no info, then everything is closed by default...
                        )

                    # Get the recloser equipment data
                    if "eqid" in settings and settings["eqid"] in self.reclosers:
                        recloser_data = self.reclosers[settings["eqid"]]
                    else:
                        recloser_data = {}

                    # Pass the nameclass to the wires
                    if "nameclass" in new_line:
                        recloser_data["nameclass"] = new_line["nameclass"]

                    try:
                        new_line["nominal_voltage"] = (
                            float(recloser_data["kvll"]) * 1000
                        )
                    except:
                        pass

                    # Create the wires
                    for p in phases + ["N"]:
                        if p in closedphase and closedphase.lower() != "none":
                            total_closed += 1
                            api_wire = self.configure_wire(
                                model,
                                recloser_data,
                                {},
                                p,
                                False,
                                False,
                                False,
                                False,
                                False,
                                True,
                                False,
                            )
                        elif p == "N" and total_closed >= 1:
                            api_wire = self.configure_wire(
                                model,
                                recloser_data,
                                {},
                                p,
                                False,
                                False,
                                False,
                                False,
                                False,
                                True,
                                False,
                            )
                        else:
                            api_wire = self.configure_wire(
                                model,
                                recloser_data,
                                {},
                                p,
                                False,
                                False,
                                True,
                                False,
                                False,
                                True,
                                False,
                            )
                        new_line["wires"].append(api_wire)

                    new_line["linecableid"] = "default_"+"_".join(phases)
                    settings["type"] = "default_connection"
                    new_line["nameclass"] = new_line["linecableid"]
                    new_line["line_type"] = "default_connection"
                    new_line["amps"] = float(10000)


                    # api_line = Line(model)
                    # for k, v in new_line.items():
                    #     setattr(api_line, k, v)
                    #
                    # if not sectionID in self.section_duplicates:
                    #     self.section_duplicates[sectionID] = []
                    # self.section_duplicates[sectionID].append(api_line)
                    # continue

                # breaker
                elif "breaker" in settings["type"]:
                    new_line["is_breaker"] = True
                    new_line["wires"] = []
                    total_closed = 0

                    # Get and map the closed phases
                    if "closedphase" in settings:
                        closedphase = mapp_closed_phase[settings["closedphase"]]
                    else:
                        closedphase = (
                            "ABC"  # If no info, then everything is closed by default...
                        )

                    # Get the breaker equipment data
                    if "eqid" in settings and settings["eqid"] in self.breakers:
                        breaker_data = self.breakers[settings["eqid"]]
                    else:
                        breaker_data = {}

                    # Pass the nameclass to the wires
                    if "nameclass" in new_line:
                        breaker_data["nameclass"] = new_line["nameclass"]

                    try:
                        new_line["nominal_voltage"] = float(breaker_data["kvll"]) * 1000
                    except:
                        pass

                    # Create the wires
                    for p in phases + ["N"]:
                        if p in closedphase and closedphase.lower() != "none":
                            total_closed += 1
                            api_wire = self.configure_wire(
                                model,
                                breaker_data,
                                {},
                                p,
                                False,
                                False,
                                False,
                                False,
                                True,
                                False,
                                False,
                            )
                        elif p == "N" and total_closed >= 1:
                            api_wire = self.configure_wire(
                                model,
                                breaker_data,
                                {},
                                p,
                                False,
                                False,
                                False,
                                False,
                                True,
                                False,
                                False,
                            )
                        else:
                            api_wire = self.configure_wire(
                                model,
                                breaker_data,
                                {},
                                p,
                                False,
                                False,
                                True,
                                False,
                                True,
                                False,
                                False,
                            )

                        new_line["wires"].append(api_wire)

                    new_line["linecableid"] = "default_"+"_".join(phases)
                    settings["type"] = "default_connection"
                    new_line["nameclass"] = new_line["linecableid"]
                    new_line["line_type"] = "default_connection"
                    new_line["amps"] = float(10000)


                    # api_line = Line(model)
                    # for k, v in new_line.items():
                    #     setattr(api_line, k, v)
                    #
                    # if not sectionID in self.section_duplicates:
                    #     self.section_duplicates[sectionID] = []
                    # self.section_duplicates[sectionID].append(api_line)
                    # continue

                # Network Protectors
                elif "network_protector" in settings["type"]:
                    new_line["is_network_protector"] = True
                    new_line["wires"] = []
                    total_closed = 0

                    # Get and map the closed phases
                    if "closedphase" in settings:
                        closedphase = mapp_closed_phase[settings["closedphase"]]
                    else:
                        closedphase = (
                            "ABC"  # If no info, then everything is closed by default...
                        )

                    # Get the network protector equipment data
                    if (
                        "eqid" in settings
                        and settings["eqid"] in self.network_protectors
                    ):
                        network_protector_data = self.network_protectors[
                            settings["eqid"]
                        ]
                    else:
                        network_protector_data = {}

                    # Pass the nameclass to the wires
                    if "nameclass" in new_line:
                        network_protector_data["nameclass"] = new_line["nameclass"]

                    try:
                        new_line["nominal_voltage"] = (
                            float(network_protector_data["kvll"]) * 1000
                        )
                    except:
                        pass

                    # Create the wires
                    for p in phases + ["N"]:
                        if p in closedphase and closedphase.lower() != "none":
                            total_closed += 1
                            api_wire = self.configure_wire(
                                model,
                                network_protector_data,
                                {},
                                p,
                                False,
                                False,
                                False,
                                True,
                                False,
                                False,
                                False,
                            )
                        elif p == "N" and total_closed >= 1:
                            api_wire = self.configure_wire(
                                model,
                                network_protector_data,
                                {},
                                p,
                                False,
                                False,
                                False,
                                True,
                                False,
                                False,
                                False,
                            )
                        else:
                            api_wire = self.configure_wire(
                                model,
                                network_protector_data,
                                {},
                                p,
                                False,
                                False,
                                True,
                                True,
                                False,
                                False,
                                False,
                            )
                        new_line["wires"].append(api_wire)

                    new_line["linecableid"] = "default_"+"_".join(phases)
                    settings["type"] = "default_connection"
                    new_line["nameclass"] = new_line["linecableid"]
                    new_line["line_type"] = "default_connection"
                    new_line["amps"] = float(10000)

                    # Create the line object
                    # api_line = Line(model)
                    # for k, v in new_line.items():
                    #     setattr(api_line, k, v)
                    # if not sectionID in self.section_duplicates:
                    #     self.section_duplicates[sectionID] = []
                    # self.section_duplicates[sectionID].append(api_line)
                    # continue

            # for switch, breaker, fuse, etc
            try:
                if new_line["line_type"] == "default_connection":
                    # impedance_matrix = None
                    # # In this case, we build the impedance matrix from Z+ and Z0 in the following way:
                    # #         __________________________
                    # #        | Z0+2*Z+  Z0-Z+   Z0-Z+   |
                    # # Z= 1/3 | Z0-Z+    Z0+2*Z+ Z0-Z+   |
                    # #        | Z0-Z+    Z0-Z+   Z0+2*Z+ |
                    # #         --------------------------
                    try:
                        coeff = 10 ** -3
                        r0 = 0.00001
                        x0 = 0.00001
                        r1 = 0.00001
                        x1 = 0.00001
                        # One phase line
                        if len(phases) == 1:

                            impedance_matrix = [
                                [
                                    1.0
                                    / 3.0
                                    * coeff
                                    * complex(
                                        float(r0), float(x0)
                                    )
                                ]
                            ]

                        # Two phase line
                        elif len(phases) == 2:

                            a = (
                                    1.0
                                    / 3.0
                                    * coeff
                                    * complex(
                                2 * float(r1) + float(r0),
                                2 * float(x1) + float(x0),
                            )
                            )
                            b = (
                                    1.0
                                    / 3.0
                                    * coeff
                                    * complex(
                                float(r0) - float(r1),
                                float(x0) - float(x1),
                            )
                            )
                            impedance_matrix = [[a, b], [b, a]]

                        # Three phase line
                        else:

                            a = (
                                    1.0
                                    / 3.0
                                    * coeff
                                    * complex(
                                2 * float(r1) + float(r0),
                                2 * float(x1) + float(x0),
                            )
                            )
                            b = (
                                    1.0
                                    / 3.0
                                    * coeff
                                    * complex(
                                float(r0) - float(r1),
                                float(x0) - float(x1),
                            )
                            )
                            impedance_matrix = [[a, b, b], [b, a, b], [b, b, a]]
                    except:
                        pass

                    try:
                        new_line["impedance_matrix"] = impedance_matrix
                    except:
                        pass

                    api_line = Line(model)
                    for k, v in new_line.items():
                        setattr(api_line, k, v)

                    # Append the line DiTTo object to the list of DiTTo lines
                    self._lines.append(api_line)
                    if not sectionID in self.section_duplicates:
                        self.section_duplicates[sectionID] = []
                    self.section_duplicates[sectionID].append(api_line)

                    section_dict[sectionID] = settings["type"]

                    continue
            except:
                pass

            line_data = None
            # If we have a linecableid for the current section
            if "linecableid" in settings:
                # And if we have line data with the matching ID
                if settings["linecableid"] in self.balanced_lines:
                    # Cache the line data
                    line_data = self.balanced_lines[settings["linecableid"]]
                    line_data["type"] = "balanced_line"
                elif settings["linecableid"] in self.unbalanced_lines:
                    # Cache the line data
                    line_data = self.unbalanced_lines[settings["linecableid"]]
                    line_data["type"] = "unbalanced_line"
                elif settings["linecableid"] in self.concentric_neutral_cable:
                    # Cache the line data
                    line_data = self.concentric_neutral_cable[settings["linecableid"]]
                    line_data["type"] = "balanced_line"
                elif settings["linecableid"] in self.cables:
                    logger.debug("cables {}".format(sectionID))
                    line_data = self.cables[settings["linecableid"]]
                    line_data["type"] = "balanced_line"
                if line_data == None:
                    #print("linecableid:" + settings["linecableid"])
                    #print("WARNING:: Skipping Line {} !".format(sectionID))
                    print("WARNING:: Issue with Line {} !".format(sectionID))
                    print("No linecable " + settings["linecableid"] +" Use balanced_lines[DEFAULT] instead !")
                    line_data = self.balanced_lines["DEFAULT"]
                    line_data["type"] = "balanced_line"
                    #missing_line.write('Section ID:' + sectionID + ' Cable ID:'+settings["linecableid"]+'\n')

                    # Lusha
                    # add cable information in equipment.txt: 1P1/0ACSR_13.8KV, 1P4/0CU_13.8KV, 3P#2ALP_4.33KV
                    # add cable 23256_CED


            # We might have a device number instead if we are dealing with BY PHASE settings
            #
            # TODO: Decide if I should remove this or not...
            elif "devicenumber" in settings:
                # if self.balanced_lines.has_key(settings['devicenumber']):
                #       #Cache the line data
                #       line_data=self.balanced_lines[settings['devicenumber']]
                # elif self.unbalanced_lines.has_key(settings['devicenumber']):
                #       #Cache the line data
                #       line_data=self.unbalanced_lines[settings['devicenumber']]
                try:
                    if settings["devicenumber"] in self.concentric_neutral_cable:
                        line_data = self.concentric_neutral_cable[settings["devicenumber"]]
                        line_data["type"] = "balanced_line"
                except:
                    pass

                # Lusha
                # configuration for unblanced by phase overhead lines
                if line_data is None:
                    try:
                        line_data = {}
                        condID_a = settings["condid_a"]
                        condID_b = settings["condid_b"]
                        condID_c = settings["condid_c"]
                        condID_n1 = settings["condid_n1"]
                        condID_n2 = settings["condid_n2"]
                        spacingid = settings["spacingid"]
                        length = settings["length"]

                        # ["id", "diameter", "gmr", "r25", "amps", "withstandrating"],
                        if condID_a != "NONE":
                            try:
                                self.conductors[condID_a]
                            except:
                                condID_a = "DEFAULT"
                            condID_a_diameter = self.conductors[condID_a]['diameter']
                            condID_a_r25 = self.conductors[condID_a]['r25']
                            condID_a_gmr = self.conductors[condID_a]['gmr']
                            line_data['condid_a'] = condID_a
                            line_data['ra'] = condID_a_r25
                            line_data['xa'] = 0.12134*math.log10(float(condID_a_diameter)/float(condID_a_gmr))

                        if condID_b != "NONE":
                            try:
                                self.conductors[condID_b]
                            except:
                                condID_b = "DEFAULT"
                            condID_b_diameter = self.conductors[condID_b]['diameter']
                            condID_b_r25 = self.conductors[condID_b]['r25']
                            condID_b_gmr = self.conductors[condID_b]['gmr']
                            line_data['condid_b'] = condID_b
                            line_data['rb'] = condID_b_r25
                            line_data['xb'] = 0.12134*math.log10(float(condID_b_diameter)/float(condID_b_gmr))

                        if condID_c != "NONE":
                            try:
                                self.conductors[condID_c]
                            except:
                                condID_c = "DEFAULT"
                            condID_c_diameter = self.conductors[condID_c]['diameter']
                            condID_c_r25 = self.conductors[condID_c]['r25']
                            condID_c_gmr = self.conductors[condID_c]['gmr']
                            line_data['condid_c'] = condID_c
                            line_data['rc'] = condID_c_r25
                            line_data['xc'] = 0.12134*math.log10(float(condID_c_diameter)/float(condID_c_gmr))

                        if condID_n1 != "NONE":
                            try:
                                self.conductors[condID_n1]
                            except:
                                condID_n1 = "DEFAULT"
                            condID_n1_diameter = self.conductors[condID_n1]['diameter']
                            condID_n1_r25 = self.conductors[condID_n1]['r25']
                            condID_n1_gmr = self.conductors[condID_n1]['gmr']
                            line_data['condid_n1'] = condID_n1


                        if condID_n2 != "NONE":
                            try:
                                self.conductors[condID_n2]
                            except:
                                condID_n2 = "DEFAULT"
                            condID_n2_diameter = self.conductors[condID_n2]['diameter']
                            condID_n2_r25 = self.conductors[condID_n2]['r25']
                            condID_n2_gmr = self.conductors[condID_n2]['gmr']
                            line_data['condid_n2'] = condID_n2

                        if condID_a != "NONE" and condID_b != "NONE":
                            line_data["mutualresistanceab"] =0
                            line_data["mutualreactanceab"] = 0
                        if condID_b != "NONE" and condID_c != "NONE":
                            line_data["mutualresistancebc"] =0
                            line_data["mutualreactancebc"] = 0
                        if condID_c != "NONE" and condID_a != "NONE":
                            line_data["mutualresistanceca"] =0
                            line_data["mutualreactanceca"] = 0

                        line_data['id'] = settings["devicenumber"]
                        line_data['spacingid'] = spacingid
                        line_data['type'] = 'unbalanced_line'
                    except:
                        pass
                # Lusha
                # use ConductorID and spaceID to calculate
                # remove this part to solve no GMR issue
                # elif (
                #     "condid_a" in settings
                #     and "condid_b" in settings
                #     and "condid_c" in settings
                #     and "spacingid" in settings
                # ):
                #     if "condid_n" in settings or "condid_n1" in settings:
                #         line_data = {"type": "unbalanced_spacing_conf"}


                # if line_data == None:
                #     print("Device number:" + settings["devicenumber"])
                #     print("WARNING:: Skipping Line {} !".format(sectionID))
                #     missing_line.write('Section ID:' + sectionID + ' Device Number:'+settings["devicenumber"]+'\n')


            if line_data is None:
                # Lusha
                # for section line without specific overhead/underground type, generate a simple one
                # 2024/09 remove this to avoid duplicate line for transformer  and load section
                logger.info("section without line information" + str(sectionID))
                # new_line["linecableid"] = "default_"+"_".join(phases)
                # settings["type"] = "default_connection"
                # new_line["nameclass"] = new_line["linecableid"]
                # new_line["line_type"] = "default_connection"
                # new_line["amps"] = float(10000)
                #
                # impedance_matrix = None
                # # In this case, we build the impedance matrix from Z+ and Z0 in the following way:
                # #         __________________________
                # #        | Z0+2*Z+  Z0-Z+   Z0-Z+   |
                # # Z= 1/3 | Z0-Z+    Z0+2*Z+ Z0-Z+   |
                # #        | Z0-Z+    Z0-Z+   Z0+2*Z+ |
                # #         --------------------------
                # try:
                #     coeff = 10 ** -3
                #     r0 = 0.00001
                #     x0 = 0.00001
                #     r1 = 0.00001
                #     x1 = 0.00001
                #     # One phase line
                #     if len(phases) == 1:
                #
                #         impedance_matrix = [
                #             [
                #                 1.0
                #                 / 3.0
                #                 * coeff
                #                 * complex(
                #                     float(r0), float(x0)
                #                 )
                #             ]
                #         ]
                #
                #     # Two phase line
                #     elif len(phases) == 2:
                #
                #         a = (
                #             1.0
                #             / 3.0
                #             * coeff
                #             * complex(
                #                 2 * float(r1) + float(r0),
                #                 2 * float(x1) + float(x0),
                #             )
                #         )
                #         b = (
                #             1.0
                #             / 3.0
                #             * coeff
                #             * complex(
                #                 float(r0) - float(r1),
                #                 float(x0) - float(x1),
                #             )
                #         )
                #         impedance_matrix = [[a, b], [b, a]]
                #
                #     # Three phase line
                #     else:
                #
                #         a = (
                #             1.0
                #             / 3.0
                #             * coeff
                #             * complex(
                #                 2 * float(r1) + float(r0),
                #                 2 * float(x1) + float(x0),
                #             )
                #         )
                #         b = (
                #             1.0
                #             / 3.0
                #             * coeff
                #             * complex(
                #                 float(r0) - float(r1),
                #                 float(x0) - float(x1),
                #             )
                #         )
                #         impedance_matrix = [[a, b, b], [b, a, b], [b, b, a]]
                # except:
                #     pass
                #
                # new_line["impedance_matrix"] = impedance_matrix
                #
                # # In the balanced case, we should have two conductor IDs: One for the phases and one for the neutral
                # # Handle the Phase conductors first:
                #
                # conductor_data = {}
                # spacing_data = {}
                #
                # # Loop over the phases and create the wires
                # new_line["wires"] = []
                # for phase in phases:
                #     api_wire = self.configure_wire(
                #         model,
                #         conductor_data,
                #         spacing_data,
                #         phase,
                #         False,
                #         False,
                #         False,
                #         False,
                #         False,
                #         False,
                #         False,
                #     )
                #     new_line["wires"].append(api_wire)
                #
                # # Handle the neutral conductor
                #
                # conductor_data = {}
                #
                # # In addition, we might have some information on the spacings
                # spacing_data = {}
                #
                # api_wire = self.configure_wire(
                #     model,
                #     conductor_data,
                #     spacing_data,
                #     "N",
                #     False,
                #     False,
                #     False,
                #     False,
                #     False,
                #     False,
                #     False,
                # )
                # new_line["wires"].append(api_wire)
                #
                # if not "phase" in settings.keys():
                #     logger.warning("WARNING:: Skipping Line {} !".format(sectionID))
                # # print("WARNING:: Skipping Line {} !".format(sectionID))
                # #missing_line.write('Section ID:' + sectionID  + '\n')
            else:
                # Lusha
                # add linecode for each line
                new_line["linecableid"] = new_line["name"]
                # Lusha
                try:
                    new_line["amps"] = float(line_data["amps"])
                except:
                    new_line["amps"] = float(10000)

                impedance_matrix = None

                # We now face two different case:
                #
                # Case 1: The line is balanced
                try:
                    line_data["type"]
                except:
                    print("no line type for line " + new_line["name"])
                if line_data["type"] == "balanced_line":
                    # In this case, we build the impedance matrix from Z+ and Z0 in the following way:
                    #         __________________________
                    #        | Z0+2*Z+  Z0-Z+   Z0-Z+   |
                    # Z= 1/3 | Z0-Z+    Z0+2*Z+ Z0-Z+   |
                    #        | Z0-Z+    Z0-Z+   Z0+2*Z+ |
                    #         --------------------------
                    try:
                        coeff = 10 ** -3

                        # One phase line
                        if len(phases) == 1:

                            impedance_matrix = [
                                [
                                    1.0
                                    / 3.0
                                    * coeff
                                    * complex(
                                        float(line_data["r0"]), float(line_data["x0"])
                                    )
                                ]
                            ]

                        # Two phase line
                        elif len(phases) == 2:

                            a = (
                                1.0
                                / 3.0
                                * coeff
                                * complex(
                                    2 * float(line_data["r1"]) + float(line_data["r0"]),
                                    2 * float(line_data["x1"]) + float(line_data["x0"]),
                                )
                            )
                            b = (
                                1.0
                                / 3.0
                                * coeff
                                * complex(
                                    float(line_data["r0"]) - float(line_data["r1"]),
                                    float(line_data["x0"]) - float(line_data["x1"]),
                                )
                            )
                            impedance_matrix = [[a, b], [b, a]]

                        # Three phase line
                        else:

                            a = (
                                1.0
                                / 3.0
                                * coeff
                                * complex(
                                    2 * float(line_data["r1"]) + float(line_data["r0"]),
                                    2 * float(line_data["x1"]) + float(line_data["x0"]),
                                )
                            )
                            b = (
                                1.0
                                / 3.0
                                * coeff
                                * complex(
                                    float(line_data["r0"]) - float(line_data["r1"]),
                                    float(line_data["x0"]) - float(line_data["x1"]),
                                )
                            )
                            impedance_matrix = [[a, b, b], [b, a, b], [b, b, a]]
                    except:
                        pass

                    # In the balanced case, we should have two conductor IDs: One for the phases and one for the neutral
                    # Handle the Phase conductors first:
                    if (
                        "phasecondid" in line_data
                        and line_data["phasecondid"] in self.conductors
                    ):
                        conductor_data = self.conductors[line_data["phasecondid"]]
                    else:
                        conductor_data = {}

                    # In addition, we might have some information on the spacings
                    if (
                        "spacingid" in line_data
                        and line_data["spacingid"] in self.spacings
                    ):
                        spacing_data = self.spacings[line_data["spacingid"]]
                    else:
                        spacing_data = {}

                    if conductor_data == {} and "linecableid" in line_data:
                        conductor_data = self.conductors[line_data["linecableid"]]

                    # Loop over the phases and create the wires
                    new_line["wires"] = []
                    for phase in phases:
                        api_wire = self.configure_wire(
                            model,
                            conductor_data,
                            spacing_data,
                            phase,
                            False,
                            False,
                            False,
                            False,
                            False,
                            False,
                            False,
                        )
                        new_line["wires"].append(api_wire)

                    # Handle the neutral conductor
                    if (
                        "neutralcondid" in line_data
                        and line_data["neutralcondid"] in self.conductors
                    ):
                        conductor_data = self.conductors[line_data["neutralcondid"]]
                    else:
                        conductor_data = {}

                    # In addition, we might have some information on the spacings
                    if (
                        "spacingid" in line_data
                        and line_data["spacingid"] in self.spacings
                    ):
                        spacing_data = self.spacings[line_data["spacingid"]]
                    else:
                        spacing_data = {}

                    api_wire = self.configure_wire(
                        model,
                        conductor_data,
                        spacing_data,
                        "N",
                        False,
                        False,
                        False,
                        False,
                        False,
                        False,
                        False,
                    )
                    new_line["wires"].append(api_wire)

                # Case 2: The line is unbalanced
                #
                elif line_data["type"] == "unbalanced_line":
                    coeff = 10 ** -3
                    # In this case, we should have all the information for the impedance matrix (mutual terms)
                    #
                    try:
                        # One phase line
                        if len(phases) == 1:

                            p = phases[0].lower()
                            impedance_matrix = [
                                [
                                    coeff
                                    * complex(
                                        float(line_data["r{}".format(p)]),
                                        coeff * float(line_data["x{}".format(p)]),
                                    )
                                ]
                            ]

                        # Two phase line
                        elif len(phases) == 2:

                            p1 = phases[0].lower()
                            p2 = phases[1].lower()
                            p1, p2 = sorted([p1, p2])
                            if p1 == "a" and p2 == "c":
                                impedance_matrix = [
                                    [
                                        coeff
                                        * complex(
                                            float(line_data["ra"]),
                                            float(line_data["xa"]),
                                        ),
                                        coeff
                                        * complex(
                                            float(line_data["mutualresistanceca"]),
                                            float(line_data["mutualreactanceca"]),
                                        ),
                                    ],
                                    [
                                        coeff
                                        * complex(
                                            float(line_data["mutualresistanceca"]),
                                            float(line_data["mutualreactanceca"]),
                                        ),
                                        coeff
                                        * complex(
                                            float(line_data["rc"]),
                                            float(line_data["xc"]),
                                        ),
                                    ],
                                ]
                            else:
                                impedance_matrix = [
                                    [
                                        coeff
                                        * complex(
                                            float(line_data["r{}".format(p1)]),
                                            float(line_data["x{}".format(p1)]),
                                        ),
                                        coeff
                                        * complex(
                                            float(
                                                line_data[
                                                    "mutualresistance{p1}{p2}".format(
                                                        p1=p1, p2=p2
                                                    )
                                                ]
                                            ),
                                            float(
                                                line_data[
                                                    "mutualreactance{p1}{p2}".format(
                                                        p1=p1, p2=p2
                                                    )
                                                ]
                                            ),
                                        ),
                                    ],
                                    [
                                        coeff
                                        * complex(
                                            float(
                                                line_data[
                                                    "mutualresistance{p1}{p2}".format(
                                                        p1=p1, p2=p2
                                                    )
                                                ]
                                            ),
                                            float(
                                                line_data[
                                                    "mutualreactance{p1}{p2}".format(
                                                        p1=p1, p2=p2
                                                    )
                                                ]
                                            ),
                                        ),
                                        coeff
                                        * complex(
                                            float(line_data["r{}".format(p2)]),
                                            float(line_data["x{}".format(p2)]),
                                        ),
                                    ],
                                ]

                        # Three phase line
                        else:

                            impedance_matrix = [
                                [
                                    coeff
                                    * complex(
                                        float(line_data["ra"]), float(line_data["xa"])
                                    ),
                                    coeff
                                    * complex(
                                        float(line_data["mutualresistanceab"]),
                                        float(line_data["mutualreactanceab"]),
                                    ),
                                    coeff
                                    * complex(
                                        float(line_data["mutualresistanceca"]),
                                        float(line_data["mutualreactanceca"]),
                                    ),
                                ],
                                [
                                    coeff
                                    * complex(
                                        float(line_data["mutualresistanceab"]),
                                        float(line_data["mutualreactanceab"]),
                                    ),
                                    coeff
                                    * complex(
                                        float(line_data["rb"]), float(line_data["xb"])
                                    ),
                                    coeff
                                    * complex(
                                        float(line_data["mutualresistancebc"]),
                                        float(line_data["mutualreactancebc"]),
                                    ),
                                ],
                                [
                                    coeff
                                    * complex(
                                        float(line_data["mutualresistanceca"]),
                                        float(line_data["mutualreactanceca"]),
                                    ),
                                    coeff
                                    * complex(
                                        float(line_data["mutualresistancebc"]),
                                        float(line_data["mutualreactancebc"]),
                                    ),
                                    coeff
                                    * complex(
                                        float(line_data["rc"]), float(line_data["xc"])
                                    ),
                                ],
                            ]
                    except:
                        pass

                    # In the unbalanced case, we should have conductor IDs for the phases and neutral
                    # Handle the Phase conductors first:
                    # Loop over the phases and create the wires
                    new_line["wires"] = []
                    for phase in phases:
                        if (
                            "condid_{}".format(phase.lower()) in line_data
                            and line_data["condid_{}".format(phase.lower())].lower()
                            != "none"
                            and line_data["condid_{}".format(phase.lower())]
                            in self.conductors
                        ):
                            conductor_data = self.conductors[
                                line_data["condid_{}".format(phase.lower())]
                            ]
                        else:
                            conductor_data = {}

                        # In addition, we might have some information on the spacings
                        if (
                            "spacingid" in line_data
                            and line_data["spacingid"].lower() != "none"
                            and line_data["spacingid"] in self.spacings
                        ):
                            spacing_data = self.spacings[line_data["spacingid"]]
                        else:
                            spacing_data = {}

                        api_wire = self.configure_wire(
                            model,
                            conductor_data,
                            spacing_data,
                            phase,
                            False,
                            False,
                            False,
                            False,
                            False,
                            False,
                            False,
                        )
                        new_line["wires"].append(api_wire)

                    # Handle the neutral conductors
                    # We might have one or two neutral conductors
                    # If we have valid condid_n1 and condid_n2 ==> create 2 wires
                    # If we have only condid_n1 or condid_n alone ==> create 1 wire only
                    #
                    # In addition, we might have some information on the spacings
                    if (
                        "spacingid" in line_data
                        and line_data["spacingid"].lower() != "none"
                        and line_data["spacingid"] in self.spacings
                    ):
                        spacing_data = self.spacings[line_data["spacingid"]]
                    else:
                        spacing_data = {}

                    if (
                        "condid_n1" in line_data
                        and line_data["condid_n1"].lower() != "none"
                        and line_data["condid_n1"] in self.conductors
                        and "condid_n2" in line_data
                        and line_data["condid_n2"].lower() != "none"
                        and line_data["condid_n2"] in self.conductors
                    ):

                        conductor_n1_data = self.conductors[line_data["condid_n1"]]
                        conductor_n2_data = self.conductors[line_data["condid_n2"]]

                        api_wire_n1 = self.configure_wire(
                            model,
                            conductor_n1_data,
                            spacing_data,
                            "N1",
                            False,
                            False,
                            False,
                            False,
                            False,
                            False,
                            False,
                        )
                        api_wire_n2 = self.configure_wire(
                            model,
                            conductor_n2_data,
                            spacing_data,
                            "N2",
                            False,
                            False,
                            False,
                            False,
                            False,
                            False,
                            False,
                        )
                        new_line["wires"].append(api_wire_n1)
                        new_line["wires"].append(api_wire_n2)

                    elif (
                        "condid_n" in line_data
                        and line_data["condid_n"].lower() != "none"
                        and line_data["condid_n"] in self.conductors
                    ):
                        conductor_data = self.conductors[line_data["condid_n"]]
                        api_wire = self.configure_wire(
                            model,
                            conductor_data,
                            spacing_data,
                            "N",
                            False,
                            False,
                            False,
                            False,
                            False,
                            False,
                            False,
                        )
                        new_line["wires"].append(api_wire)

                    else:
                        if (
                            "condid_n1" in line_data
                            and line_data["condid_n1"].lower() != "none"
                            and line_data["condid_n1"] in self.conductors
                        ):
                            conductor_data = self.conductors[line_data["condid_n1"]]
                            api_wire = self.configure_wire(
                                model,
                                conductor_data,
                                spacing_data,
                                "N",
                                False,
                                False,
                                False,
                                False,
                                False,
                                False,
                                False,
                            )
                            new_line["wires"].append(api_wire)

                elif line_data["type"] == "unbalanced_spacing_conf":

                    # IMPEDANCE MATRIX FROM SPACINGS
                    #
                    # First, we have to get the wires' positions:
                    if settings["spacingid"] in self.spacings:
                        # Get the spacing data
                        spacing_data = self.spacings[settings["spacingid"]]
                        pos = []

                        for i, p in enumerate(phases):
                            pos.append([None, None])
                            for j, k in enumerate(["x", "y"]):
                                if (
                                    "posofcond{i}_{k}".format(i=i + 1, k=k)
                                    in spacing_data
                                ):
                                    try:
                                        pos[-1][j] = float(
                                            spacing_data[
                                                "posofcond{i}_{k}".format(i=i + 1, k=k)
                                            ]
                                        )
                                    except:
                                        pass

                        pos.append([None, None])

                        if (
                            "posofneutralcond_x" in spacing_data
                            and "posofneutralcond_y" in spacing_data
                        ):
                            try:
                                pos[-1][0] = float(spacing_data["posofneutralcond_x"])
                                pos[-1][1] = float(spacing_data["posofneutralcond_y"])
                            except:
                                pass

                        pos.append([None, None])

                        if (
                            "posofneutralcond_n2_x" in spacing_data
                            and spacing_data["posofneutralcond_n2_x"] != ""
                            and "posofneutralcond_n2_y" in spacing_data
                            and spacing_data["posofneutralcond_n2_y"] != ""
                        ):
                            try:
                                pos[-1][0] = float(
                                    spacing_data["posofneutralcond_n2_x"]
                                )
                                pos[-1][1] = float(
                                    spacing_data["posofneutralcond_n2_y"]
                                )
                            except:
                                pass

                        valid_cond = []
                        ph_list = ["a", "b", "c", "n1", "n2"]
                        for idd, po in enumerate(pos):
                            if po != [None, None]:
                                valid_cond.append(idd)
                        distance_matrix = []
                        for i, ii in enumerate(valid_cond):
                            distance_matrix.append([])
                            for j, jj in enumerate(valid_cond):
                                distance_matrix[-1].append(
                                    3.28084 * self.distance(pos[ii], pos[jj])
                                )  # 0.0328084
                        distance_matrix = np.array(distance_matrix)

                        gmr_list = []
                        resistance_list = []

                        perform_kron_reduction = False

                        # Get GMR and resistance of valid conductor
                        for idx, p in enumerate(phases):
                            if (
                                "condid_{}".format(p.lower()) in settings
                                and settings["condid_{}".format(p.lower())]
                                in self.conductors
                            ):
                                gmr_list.append(
                                    0.0328084
                                    * float(
                                        self.conductors[
                                            settings["condid_{}".format(p.lower())]
                                        ]["gmr"]
                                    )
                                )
                                resistance_list.append(
                                    1.0
                                    / 0.621371
                                    * float(
                                        self.conductors[
                                            settings["condid_{}".format(p.lower())]
                                        ]["r25"]
                                    )
                                )
                            else:
                                logger.warning(
                                    "Could not find conductor {name}. Using DEFAULT...".format(
                                        name="condid_{}".format(p.lower())
                                    )
                                )
                                gmr_list.append(
                                    0.0328084 * float(self.conductors["DEFAULT"]["gmr"])
                                )
                                resistance_list.append(
                                    1.0
                                    / 0.621371
                                    * float(self.conductors["DEFAULT"]["r25"])
                                )
                                # gmr_list.append(None)
                                # resistance_list.append(None)
                        if "condid_n" in settings:
                            if settings["condid_n"] in self.conductors:
                                gmr_list.append(
                                    0.0328084
                                    * float(
                                        self.conductors[settings["condid_n"]]["gmr"]
                                    )
                                )
                                resistance_list.append(
                                    1.0
                                    / 0.621371
                                    * float(
                                        self.conductors[settings["condid_n"]]["r25"]
                                    )
                                )
                            else:
                                logger.warning(
                                    "Could not find neutral conductor {name}. Using DEFAULT...".format(
                                        name=settings["condid_n"]
                                    )
                                )
                                gmr_list.append(
                                    0.0328084 * float(self.conductors["DEFAULT"]["gmr"])
                                )
                                resistance_list.append(
                                    1.0
                                    / 0.621371
                                    * float(self.conductors["DEFAULT"]["r25"])
                                )
                        elif (
                            "condid_n1" in settings
                            and settings["condid_n1"] is not None
                            and settings["condid_n1"].lower() != "none"
                        ):
                            if settings["condid_n1"] in self.conductors:
                                gmr_list.append(
                                    0.0328084
                                    * float(
                                        self.conductors[settings["condid_n1"]]["gmr"]
                                    )
                                )
                                resistance_list.append(
                                    1.0
                                    / 0.621371
                                    * float(
                                        self.conductors[settings["condid_n1"]]["r25"]
                                    )
                                )
                            else:
                                logger.warning(
                                    "Could not find neutral conductor {name}. Using DEFAULT...".format(
                                        name=settings["condid_n1"]
                                    )
                                )
                                gmr_list.append(
                                    0.0328084 * float(self.conductors["DEFAULT"]["gmr"])
                                )
                                resistance_list.append(
                                    1.0
                                    / 0.621371
                                    * float(self.conductors["DEFAULT"]["r25"])
                                )
                        else:
                            gmr_list.append(None)
                            resistance_list.append(None)
                            perform_kron_reduction = False

                        gmr_list = np.array(gmr_list)
                        resistance_list = np.array(resistance_list)
                        idx_to_remove = np.argwhere(gmr_list == None).flatten()
                        idx_to_keep = [
                            idx
                            for idx in range(len(distance_matrix))
                            if idx not in idx_to_remove
                        ]
                        try:
                            distance_matrix = distance_matrix[idx_to_keep, :][
                                :, idx_to_keep
                            ]
                        except IndexError:
                            # It can happen that a one phase line is defined with a spacing table where no position are defined.
                            # This is uncommon but raises an IndexError here.
                            # To avoid that, use a dummy distance matrix
                            distance_matrix = np.array([[1]])
                            pass

                        primitive_imp_matrix = self.get_primitive_impedance_matrix(
                            distance_matrix, gmr_list, resistance_list
                        )

                        if perform_kron_reduction:
                            phase_imp_matrix = (
                                1.0
                                / 1609.34
                                * self.kron_reduction(primitive_imp_matrix)
                            )
                        else:
                            phase_imp_matrix = 1.0 / 1609.34 * primitive_imp_matrix

                        impedance_matrix = phase_imp_matrix.tolist()

                    new_line["wires"] = []

                    for phase in phases:
                        if (
                            "condid_{}".format(phase.lower()) in settings
                            and settings["condid_{}".format(phase.lower())]
                            in self.conductors
                        ):
                            conductor_data = self.conductors[
                                settings["condid_{}".format(phase.lower())]
                            ]
                        else:
                            conductor_data = {}

                        # In addition, we might have some information on the spacings
                        if (
                            "spacingid" in settings
                            and settings["spacingid"] in self.spacings
                        ):
                            spacing_data = self.spacings[settings["spacingid"]]
                        else:
                            spacing_data = {}

                        api_wire = self.configure_wire(
                            model,
                            conductor_data,
                            spacing_data,
                            phase,
                            False,
                            False,
                            False,
                            False,
                            False,
                            False,
                            False,
                        )
                        new_line["wires"].append(api_wire)

                    # Handle the neutral conductors
                    if (
                        "condid_n" in settings
                        and settings["condid_n"] is not None
                        and settings["condid_n"] != ""
                        and settings["condid_n"] != "NONE"
                        and settings["condid_n"] in self.conductors
                    ):
                        conductor_data = self.conductors[settings["condid_n"]]
                    elif (
                        "condid_n1" in settings
                        and settings["condid_n1"] is not None
                        and settings["condid_n1"] != ""
                        and settings["condid_n1"] != "NONE"
                        and settings["condid_n1"] in self.conductors
                    ):
                        conductor_data = self.conductors[settings["condid_n1"]]
                    else:
                        conductor_data = {}

                    # In addition, we might have some information on the spacings
                    if (
                        "spacingid" in settings
                        and settings["spacingid"] in self.spacings
                    ):
                        spacing_data = self.spacings[settings["spacingid"]]
                    else:
                        spacing_data = {}

                    if len(conductor_data) != 0:
                        api_wire = self.configure_wire(
                            model,
                            conductor_data,
                            spacing_data,
                            "N",
                            False,
                            False,
                            False,
                            False,
                            False,
                            False,
                            False,
                        )
                        new_line["wires"].append(api_wire)

                try:
                    new_line["impedance_matrix"] = impedance_matrix
                except:
                    pass


                # Lusha
                # only for lines not sections
                api_line = Line(model)
                for k, v in new_line.items():
                    setattr(api_line, k, v)

                # Append the line DiTTo object to the list of DiTTo lines
                self._lines.append(api_line)
                if not sectionID in self.section_duplicates:
                    self.section_duplicates[sectionID] = []
                self.section_duplicates[sectionID].append(api_line)

                section_dict[sectionID] = settings["type"]

        missing_line.close()
        return 1

    def parse_capacitors(self, model=None):
        print("Inside parse_capacitors")
        """Parse the capacitors from CYME to DiTTo."""
        # Instanciate the list in which we store the DiTTo capacitor objects
        self._capacitors = []

        mapp_serie_capacitor_settings = {
            "sectionid": 0,
            "eqid": 2,
            "coordx": 7,
            "coordy": 8,
        }
        mapp_shunt_capacitor_settings = {
            "sectionid": 0,
            "shuntcapacitorid": 39,
            "connection": 6,
            "fixedkvara": 7,
            "fixedkvarb": 8,
            "fixedkvarc": 9,
            "switchedkvara": 13,
            "switchedkvarb": 14,
            "switchedkvarc": 15,
            "kv": 24,
            "controllingphase": 35,
        }
        mapp_serie_capacitor = {"id": 0, "reactance": 6}
        mapp_shunt_capacitor = {"id": 0, "kvar": 1, "kv": 2, "type": 6}
        self.settings = {}
        self.capacitors = {}

        #####################################################
        #                                                   #
        #                   NETWORK FILE                    #
        #                                                   #
        #####################################################
        #
        # Open the network file
        #self.get_file_content("network")

        # Loop over the network file
        #for line in self.content:

        try:
            self.content = iter(self.file_network_capacitor)
            line = next(self.content)
            #########################################
            #                                       #
            #             SERIE CAPACITOR           #
            #                                       #
            #########################################
            #
            self.settings.update(
                self.parser_helper(
                    line,
                    ["serie_capacitor_settings"],
                    ["sectionid", "eqid", "coordx", "coordy"],
                    mapp_serie_capacitor_settings,
                    {"type": "serie"},
                )
            )

            #########################################
            #                                       #
            #             SHUNT CAPACITOR           #
            #                                       #
            #########################################
            #
            self.settings.update(
                self.parser_helper(
                    line,
                    ["shunt_capacitor_settings"],
                    [
                        "sectionid",
                        "shuntcapacitorid",
                        "connection",
                        "fixedkvara",
                        "fixedkvarb",
                        "fixedkvarc",
                        "switchedkvara",
                        "switchedkvarb",
                        "switchedkvarc",
                        "kv",
                        "controllingphase",
                    ],
                    mapp_shunt_capacitor_settings,
                    {"type": "shunt"},
                )
            )
        except:
            pass
        #####################################################
        #                                                   #
        #                 EQUIPMENT FILE                    #
        #                                                   #
        #####################################################
        #
        # Open the equipment file
        #self.get_file_content("equipment")

        # Loop over the equipment file
        #for line in self.content:
        try:
            self.content = iter(self.file_equipment_capacitor)
            line = next(self.content)
            #########################################
            #                                       #
            #        SERIE CAPACITOR                #
            #                                       #
            #########################################
            #
            self.capacitors.update(
                self.parser_helper(
                    line, ["serie_capacitor"], ["id", "reactance"], mapp_serie_capacitor
                )
            )

            #########################################
            #                                       #
            #        SHUNT CAPACITOR                #
            #                                       #
            #########################################
            #
            self.capacitors.update(
                self.parser_helper(
                    line,
                    ["shunt_capacitor"],
                    ["id", "kvar", "kv", "type"],
                    mapp_shunt_capacitor,
                )
            )
        except:
            pass

        for sectionID, settings in self.settings.items():

            sectionID = sectionID.strip("*").lower()

            feedername = self.section_feeder_mapping[sectionID]
            model = self.feeder_models[feedername]

            # Instanciate Capacitor DiTTo objects
            try:
                api_capacitor = Capacitor(model)
            except:
                raise ValueError(
                    "Unable to instanciate capacitor {id}".format(id=scap["sectionid"])
                )

            # Set the name
            try:
                api_capacitor.name = "Cap_" + sectionID
            except:
                pass

            # Set the connecting element (info is in the section)
            try:
                api_capacitor.connecting_element = self.section_phase_mapping[
                    sectionID
                ]["fromnodeid"]
            except:
                pass

            # PT phase
            # (Only works with shunt capacitors)
            try:
                api_capacitor.pt_phase = self.phase_mapping(
                    settings["controllingphase"]
                )
            except:
                pass

            try:
                api_capacitor.feeder_name = self.section_feeder_mapping[sectionID]
            except:
                pass

            try:
                api_capacitor.substation_name = self.feeder_sub_mapping[api_capacitor.feeder_name]
            except:
                api_capacitor.substation_name = api_capacitor.feeder_name

            # Connection_type
            # (Only works with shunt capacitors)
            try:
                api_capacitor.connection_type = self.capacitors_connection_mapping(
                    settings["connection"]
                )
            except:
                pass

            # Position
            try:
                position = Position(model)
                position.long = float(settings["coordx"])
                position.lat = float(settings["coordy"])
                position.elevation = 0
                api_capacitor.position.append(position)
            except:
                pass

            # Get the device number
            if "eqid" in settings:
                dev_num = settings["eqid"]
            elif "shuntcapacitorid" in settings:
                dev_num = settings["shuntcapacitorid"]
            else:
                dev_num = None

            capacitor_data = None
            if dev_num is not None:
                if dev_num in self.capacitors:
                    capacitor_data = self.capacitors[dev_num]

                    # Reactance
                    try:
                        api_capacitor.reactance = float(capacitor_data["reactance"])
                    except:
                        pass

                    # KV
                    try:
                        api_capacitor.nominal_voltage = (
                            float(capacitor_data["kv"]) * 10 ** 3
                        )  # DiTTo in volt
                    except:
                        pass

            # Map the phases to DiTTo phase format
            phases = self.section_phase_mapping[sectionID]["phase"]

            # Rated KV
            #
            # Note: Rated KV is line-to-neutral for Wye-grounded configuration,
            # and line-to-line for delta configuration
            #
            # If the capacitor is one phase, we have a line-to-neutral,
            # and line-to-line if it is 3 phase
            #
            if "kv" in settings:
                try:
                    if api_capacitor.connection_type == "Y" or len(phases) == 1:
                        api_capacitor.nominal_voltage = (
                            float(settings["kv"]) * 10 ** 3
                        )  # DiTTo in var
                    if api_capacitor.connection_type == "D" or len(phases) == 3:
                        api_capacitor.nominal_voltage = (
                            float(settings["kv"]) * 10 ** 3 * math.sqrt(3)
                        )  # DiTTo in var
                except:
                    pass

            if (
                api_capacitor.pt_phase is not None
                and api_capacitor.pt_phase not in phases
            ):
                raise ValueError(
                    "Capacitor {name} is monitoring phase {p} which is not in the section {id} phase list {lis}.".format(
                        name=api_capacitor.name,
                        p=api_capacitor.pt_phase,
                        id=scap["sectionid"],
                        lis=phases,
                    )
                )

            # For each phase...
            for p in phases:

                # Instanciate a PhaseCapacitor DiTTo object
                try:
                    api_phaseCapacitor = PhaseCapacitor(model)
                except:
                    raise ValueError(
                        "Unable to instanciate PhaseCapacitor DiTTo object."
                    )

                # Set the phase
                try:
                    api_phaseCapacitor.phase = p
                except:
                    pass

                # Set var value
                if (
                    "fixedkvara" in settings
                    and "fixedkvarb" in settings
                    and "fixedkvarc" in settings
                    and max(
                        float(settings["fixedkvara"]),
                        max(
                            float(settings["fixedkvarb"]), float(settings["fixedkvarc"])
                        ),
                    )
                    > 0
                ):
                    try:
                        if p == "A":
                            api_phaseCapacitor.var = (
                                float(settings["fixedkvara"]) * 10 ** 3
                            )  # Ditto in var
                        if p == "B":
                            api_phaseCapacitor.var = (
                                float(settings["fixedkvarb"]) * 10 ** 3
                            )  # Ditto in var
                        if p == "C":
                            api_phaseCapacitor.var = (
                                float(settings["fixedkvarc"]) * 10 ** 3
                            )  # Ditto in var
                    except:
                        pass
                elif (
                    "switchedkvara" in settings
                    and "switchedkvarb" in settings
                    and "switchedkvarc" in settings
                    and max(
                        float(settings["switchedkvara"]),
                        max(
                            float(settings["switchedkvarb"]),
                            float(settings["switchedkvarc"]),
                        ),
                    )
                    > 0
                ):
                    try:
                        if p == "A":
                            api_phaseCapacitor.var = (
                                float(settings["switchedkvara"]) * 10 ** 3
                            )  # Ditto in var
                        if p == "B":
                            api_phaseCapacitor.var = (
                                float(settings["switchedkvarb"]) * 10 ** 3
                            )  # Ditto in var
                        if p == "C":
                            api_phaseCapacitor.var = (
                                float(settings["switchedkvarc"]) * 10 ** 3
                            )  # Ditto in var
                    except:
                        pass

                elif capacitor_data is not None:
                    try:
                        api_phaseCapacitor.var = (
                            float(capacitor_data["kvar"]) * 10 ** 3
                        )  # DiTTo in var
                    except:
                        pass

                # Append the phase capacitor object to the capacitor
                api_capacitor.phase_capacitors.append(api_phaseCapacitor)

            self._capacitors.append(api_capacitor)
            if not sectionID in self.section_duplicates:
                self.section_duplicates[sectionID] = []
            self.section_duplicates[sectionID].append(api_capacitor)

        return 1

    def parse_transformers(self, model=None):
        print("Inside parse_transformers")
        """Parse the transformers from CYME to DiTTo. Since substation transformer can have LTCs attached, when parsing a transformer, we may also create a regulator. LTCs are represented as regulators."""
        # Instanciate the list in which we store the DiTTo transformer objects
        self._transformers = []

        mapp_auto_transformer_settings = {
            "sectionid": 0,
            "eqid": 2,
            "coordx": 7,
            "coordy": 8,
            "connection_configuration": 9,
            "tap": 25,
        }
        mapp_auto_transformer = {
            "id": 0,
            "kva": 3,
            "connection_configuration": 18,
            "noloadlosses": 32,
            "isltc": 21,
            "taps": 22,
            "lowerbandwidth": 23,
            "upperbandwidth": 24,
        }
        mapp_grounding_transformer_settings = {
            "sectionid": 0,
            "equipmentid": 6,
            "connectionconfiguration": 10,
            "phase": 13,
        }
        mapp_grounding_transformer = {
            "id": 0,
            "connectionconfiguration": 7,
            "ratedvoltage": 5,
            "ratedcapacity": 6,
        }
        mapp_three_winding_auto_transformer_settings = {
            "sectionid": 0,
            "eqid": 2,
            "coordx": 7,
            "coordy": 8,
            "primaryfixedtapsetting": 10,
            "secondaryfixedtapsetting": 11,
            "tertiaryfixedtapsetting": 12,
            "primarybasevoltage": 13,
            "secondarybasevoltage": 14,
            "tertiarybasevoltage": 15,
        }
        mapp_three_winding_auto_transformer = {
            "id": 0,
            "primaryratedcapacity": 1,
            "primaryvoltage": 6,
            "secondaryratedcapacity": 22,
            "secondaryvoltage": 27,
            "tertiaryratedcapacity": 30,
            "tertiaryvoltage": 35,
            "noloadlosses": 50,
        }
        mapp_three_winding_transformer_settings = {
            "sectionid": 0,
            "eqid": 2,
            "coordx": 7,
            "coordy": 8,
            "primaryfixedtapsetting": 10,
            "secondaryfixedtapsetting": 11,
            "tertiaryfixedtapsetting": 12,
            "primarybasevoltage": 13,
            "secondarybasevoltage": 14,
            "tertiarybasevoltage": 15,
        }
        mapp_three_winding_transformer = {
            "id": 0,
            "primaryratedcapacity": 1,
            "primaryvoltage": 6,
            "secondaryratedcapacity": 24,
            "secondaryvoltage": 29,
            "tertiaryratedcapacity": 33,
            "tertiaryvoltage": 38,
            "noloadlosses": 53,
        }
        mapp_transformer_settings = {
            "sectionid": 0,
            "eqid": 2,
            "coordx": 7,
            "coordy": 8,
            "conn": 9,
            "primtap": 10,
            "secondarytap": 11,
            "primarybasevoltage": 17,
            "secondarybasevoltage": 18,
            "setpoint": 21,
            "maxbuck": 29,
            "maxboost": 30,
            "ct": 31,
            "pt": 32,
            "phaseon": 37,
        }
        mapp_transformer = {
            "id": 0,
            "type": 1,
            "kva": 3,
            "kvllprim": 5,
            "kvllsec": 6,
            "z1": 7,
            "z0": 8,
            "xr": 12,
            "xr0": 13,
            "conn": 18,
            "noloadlosses": 34,
            "isltc": 23,
            "taps": 24,
            "lowerbandwidth": 25,
            "upperbandwidth": 26,
            "phaseshift": 41,
        }
        mapp_phase_shifter_transformer_settings = {
            "sectionid": 0,
            "eqid": 2,
            "coordx": 10,
            "coordy": 11,
        }

        self.auto_transformers = {}
        self.grounding_transformers = {}
        self.three_winding_auto_transformers = {}
        self.three_winding_transformers = {}
        self.settings = {}
        self.transformers = {}

        #####################################################
        #                                                   #
        #                   NETWORK FILE                    #
        #                                                   #
        #####################################################
        #
        # Open the network file
        #self.get_file_content("network")

        # Loop over the network file
        #for line in self.content:

        try:
            self.content = iter(self.file_network_trans)
            line = next(self.content)
            #########################################
            #                                       #
            #             AUTO TRANSFORMER          #
            #                                       #
            #########################################
            #
            self.settings.update(
                self.parser_helper(
                    line,
                    ["auto_transformer_settings"],
                    [
                        "sectionid",
                        "eqid",
                        "coordx",
                        "coordy",
                        "connection_configuration",
                        "tap",
                    ],
                    mapp_auto_transformer_settings,
                    {"type": "auto_transformer"},
                )
            )

            #########################################
            #                                       #
            #         GROUNDING TRANSFORMER         #
            #                                       #
            #########################################
            #
            self.settings.update(
                self.parser_helper(
                    line,
                    ["grounding_transformer_settings"],
                    ["sectionid", "equipmentid", "connectionconfiguration", "phase"],
                    mapp_grounding_transformer_settings,
                    {"type": "grounding_transformer"},
                )
            )

            #########################################
            #                                       #
            #   THREE WINDING AUTO TRANSFORMER      #
            #                                       #
            #########################################
            #
            self.settings.update(
                self.parser_helper(
                    line,
                    ["three_winding_auto_transformer_settings"],
                    [
                        "sectionid",
                        "eqid",
                        "coordx",
                        "coordy",
                        "primaryfixedtapsetting",
                        "secondaryfixedtapsetting",
                        "tertiaryfixedtapsetting",
                        "primarybasevoltage",
                        "secondarybasevoltage",
                        "tertiarybasevoltage",
                    ],
                    mapp_three_winding_auto_transformer_settings,
                    {"type": "three_winding_auto_transformer"},
                )
            )

            #########################################
            #                                       #
            #      THREE WINDING TRANSFORMER        #
            #                                       #
            #########################################
            #
            self.settings.update(
                self.parser_helper(
                    line,
                    ["three_winding_transformer_settings"],
                    [
                        "sectionid",
                        "eqid",
                        "coordx",
                        "coordy",
                        "primaryfixedtapsetting",
                        "secondaryfixedtapsetting",
                        "tertiaryfixedtapsetting",
                        "primarybasevoltage",
                        "secondarybasevoltage",
                        "tertiarybasevoltage",
                    ],
                    mapp_three_winding_transformer_settings,
                    {"type": "three_winding_transformer"},
                )
            )

            #########################################
            #                                       #
            #             TRANSFORMER               #
            #                                       #
            #########################################
            #
            self.settings.update(
                self.parser_helper(
                    line,
                    ["transformer_settings"],
                    [
                        "sectionid",
                        "eqid",
                        "coordx",
                        "coordy",
                        "primaryfixedtapsetting",
                        "secondaryfixedtapsetting",
                        "tertiaryfixedtapsetting",
                        "primarybasevoltage",
                        "secondarybasevoltage",
                        "tertiarybasevoltage",
                        "setpoint",
                        "maxbuck",
                        "maxboost",
                        "ct",
                        "pt",
                    ],
                    mapp_transformer_settings,
                    {"type": "transformer"},
                )
            )

            #########################################
            #                                       #
            #    PHASE SHIFTER TRANSFORMER          #
            #                                       #
            #########################################
            #
            self.settings.update(
                self.parser_helper(
                    line,
                    ["phase_shifter_transformer_settings"],
                    ["sectionid", "eqid", "coordx", "coordy"],
                    mapp_phase_shifter_transformer_settings,
                    {"type": "phase_shifter_transformer"},
                )
            )
        except:
            pass

        #####################################################
        #                                                   #
        #                 EQUIPMENT FILE                    #
        #                                                   #
        #####################################################
        #
        # Open the equipment file
        #self.get_file_content("equipment")

        # Loop over the equipment file
        #for line in self.content:

        try:
            self.content = iter(self.file_equipment_transformer)
            line = next(self.content)
            #########################################
            #                                       #
            #             AUTO TRANSFORMER          #
            #                                       #
            #########################################
            #
            self.auto_transformers.update(
                self.parser_helper(
                    line,
                    ["auto_transformer"],
                    [
                        "id",
                        "kva",
                        "connection_configuration",
                        "noloadlosses",
                        "isltc",
                        "taps",
                        "lowerbandwidth",
                        "upperbandwidth",
                    ],
                    mapp_auto_transformer,
                )
            )

            #########################################
            #                                       #
            #         GROUNDING TRANSFORMER         #
            #                                       #
            #########################################
            #
            self.grounding_transformers.update(
                self.parser_helper(
                    line,
                    ["grounding_transformer"],
                    ["id", "ratedcapacity", "ratedvoltage", "connection_configuration"],
                    mapp_grounding_transformer,
                )
            )

            #########################################
            #                                       #
            #  THREE WINDING AUTO TRANSFORMER       #
            #                                       #
            #########################################
            #
            # LTC controls not yet supported for three-winding transformers
            self.three_winding_auto_transformers.update(
                self.parser_helper(
                    line,
                    ["three_winding_auto_transformer"],
                    [
                        "id",
                        "primaryratedcapacity",
                        "primaryvoltage",
                        "secondaryratedcapacity",
                        "secondaryvoltage",
                        "tertiaryratedcapacity",
                        "tertiaryvoltage",
                        "noloadlosses",
                    ],
                    mapp_three_winding_auto_transformer,
                )
            )

            #########################################
            #                                       #
            #      THREE WINDING TRANSFORMER        #
            #                                       #
            #########################################
            #
            # LTC controls not yet supported for three-winding transformers
            self.three_winding_transformers.update(
                self.parser_helper(
                    line,
                    ["three_winding_transformer"],
                    [
                        "id",
                        "primaryratedcapacity",
                        "primaryvoltage",
                        "secondaryratedcapacity",
                        "secondaryvoltage",
                        "tertiaryratedcapacity",
                        "tertiaryvoltage",
                        "noloadlosses",
                    ],
                    mapp_three_winding_transformer,
                )
            )

            #########################################
            #                                       #
            #             TRANSFORMER               #
            #                                       #
            #########################################
            #
            self.transformers.update(
                self.parser_helper(
                    line,
                    ["transformer"],
                    [
                        "id",
                        "type",
                        "kva",
                        "kvllprim",
                        "kvllsec",
                        "z1",
                        "z0",
                        "xr",
                        "xr0",
                        "conn",
                        "noloadlosses",
                        "phaseshift",
                        "isltc",
                        "taps",
                        "lowerbandwidth",
                        "upperbandwidth",
                    ],
                    mapp_transformer,
                )
            )
        except:
            pass

        for sectionID, settings in self.settings.items():

            sectionID = sectionID.strip("*").lower()

            # Instanciate a PowerTransformer DiTTo object
            try:
                # Lusha
                feedername = self.section_feeder_mapping[sectionID]
                model = self.feeder_models[feedername]

                api_transformer = PowerTransformer(model)
            except:
                raise ValueError("Unable to instanciate PowerTransformer DiTTo object.")

            # Set the name
            try:
                api_transformer.name = "Trans_" + settings["sectionid"]
            except:
                pass

            try:
                feeder_name = self.section_feeder_mapping[sectionID]
                api_transformer.feeder_name = feeder_name
            except:
                pass
            # Lusha
            try:
                api_transformer.substation_name = self.feeder_sub_mapping[feeder_name]
            except:
                api_transformer.substation_name = feeder_name

            try:
                phases = self.section_phase_mapping[sectionID]["phase"]
            except:
                raise ValueError("Empty phases for transformer {}.".format(sectionID))

            # Set from_element
            try:
                api_transformer.from_element = self.section_phase_mapping[sectionID][
                    "fromnodeid"
                ]
            except:
                pass

            # Set to_element
            try:
                api_transformer.to_element = self.section_phase_mapping[sectionID][
                    "tonodeid"
                ]
            except:
                pass

            # Lusha
            # set feedername for fromnode and tonode of transformer
            if api_transformer.from_element not in self.node_feeder_mapping.keys():
                self.node_feeder_mapping[api_transformer.from_element] = []
            if api_transformer.to_element not in self.node_feeder_mapping.keys():
                self.node_feeder_mapping[api_transformer.to_element] = []
            if api_transformer.feeder_name not in self.node_feeder_mapping[api_transformer.from_element]:
                self.node_feeder_mapping[api_transformer.from_element].append(api_transformer.feeder_name)
            if api_transformer.feeder_name not in self.node_feeder_mapping[api_transformer.to_element]:
                self.node_feeder_mapping[api_transformer.to_element].append(api_transformer.feeder_name)


            # Set the connection index for the from_element (info is in the section)
            try:
                api_transformer["from_element_connection_index"] = int(
                    self.section_phase_mapping[sectionID]["fromnodeindex"]
                )
            except:
                pass

            # Set the connection index for the from_element (info is in the section)
            try:
                api_transformer["to_element_connection_index"] = int(
                    self.section_phase_mapping[sectionID]["tonodeindex"]
                )
            except:
                pass

            # Set the position
            try:
                position = Position(model)
                position.long = float(settings["coordx"])
                position.lat = float(settings["coordy"])
                position.elevation = 0
                api_transformer.positions.append(position)
            except:
                pass

            # Handle the three winding transformers
            if settings["type"] in [
                "three_winding_transformer",
                "three_winding_auto_transformer",
            ]:
                # Here we know that we have three windings...
                for w in range(3):

                    # Instanciate a DiTTo Winding object
                    try:
                        api_winding = Winding(model)
                    except:
                        raise ValueError("Unable to instanciate Winding DiTTo object.")

                    # Set the base voltage
                    # We assume that 1st winding is primary, 2nd secondary, and third tertiary
                    try:
                        if w == 0:
                            api_winding.nominal_voltage = (
                                float(settings["primarybasevoltage"]) * 10 ** 3
                            )  # DiTTo in volt
                        if w == 1:
                            api_winding.nominal_voltage = (
                                float(settings["secondarybasevoltage"]) * 10 ** 3
                            )  # DiTTo in volt
                        if w == 2:
                            api_winding.nominal_voltage = (
                                float(settings["tertiarybasevoltage"]) * 10 ** 3
                            )  # DiTTo in volt
                    except:
                        pass

                    # Set the rated power
                    try:
                        if w == 0:
                            api_winding.rated_power = (
                                float(settings["primaryratedcapacity"]) * 10 ** 3
                            )  # DiTTo in volt ampere
                        if w == 1:
                            api_winding.rated_power = (
                                float(settings["secondaryratedcapacity"]) * 10 ** 3
                            )  # DiTTo in volt ampere
                        if w == 2:
                            api_winding.rated_power = (
                                float(settings["tertiaryratedcapacity"]) * 10 ** 3
                            )  # DiTTo in volt ampere
                    except:
                        pass

                    # Create the phase windings
                    for p in phases:

                        # Instanciate a PhaseWinding DiTTo object
                        try:
                            api_phase_winding = PhaseWinding(model)
                        except:
                            raise ValueError(
                                "Unable to instanciate PhaseWinding DiTTo object."
                            )

                        # Set the phase
                        try:
                            api_phase_winding.phase = p
                        except:
                            pass

                        # Set the tap position
                        try:
                            if w == 0:
                                api_phase_winding.tap_position = int(
                                    settings["primaryfixedtapsetting"]
                                )
                            if w == 1:
                                api_phase_winding.tap_position = int(
                                    settings["secondaryfixedtapsetting"]
                                )
                            if w == 2:
                                api_phase_winding.tap_position = int(
                                    settings["tertiaryfixedtapsetting"]
                                )
                        except:
                            pass

                        # Add the phase winding object to the winding
                        api_winding.phase_windings.append(api_phase_winding)

                    # Add the winding object to the transformer
                    api_transformer.windings.append(api_winding)

            # Handle two windings transformers
            if settings["type"] == "transformer":

                if settings["eqid"] in self.transformers:
                    transformer_data = self.transformers[settings["eqid"]]
                else:
                    transformer_data = self.transformers["DEFAULT"]

                # Resistance
                #
                # Note: Imported from Julietta's code
                #
                Z1 = float(transformer_data["z1"])
                Z0 = float(transformer_data["z0"])
                XR = float(transformer_data["xr"])
                XR0 = float(transformer_data["xr0"])
                if XR == 0:
                    R1 = 0
                    X1 = 0
                else:
                    R1 = Z1 / math.sqrt(1 + XR * XR)
                    X1 = Z1 / math.sqrt(1 + 1 / (XR * XR))
                if XR0 == 0:
                    R0 = 0
                    X0 = 0
                else:
                    R0 = Z0 / math.sqrt(1 + XR0 * XR0)
                    X0 = Z0 / math.sqrt(1 + 1 / (XR0 * XR0))
                complex0 = complex(R0, X0)
                complex1 = complex(R1, X1)
                matrix = np.array(
                    [[complex0, 0, 0], [0, complex1, 0], [0, 0, complex1]]
                )
                a = 1 * cmath.exp(2 * math.pi * 1j / 3)
                T = np.array([[1.0, 1.0, 1.0], [1.0, a * a, a], [1.0, a, a * a]])
                T_inv = np.linalg.inv(T)
                Zabc = T * matrix * T_inv

                Z_perc = Zabc.item((0, 0))
                R_perc = Z_perc.real / 2.0 # What's 2 here?
                xhl = Z_perc.imag

                # Check if it's an LTC
                #
                if "isltc" in transformer_data and transformer_data["isltc"]:
                    # Instanciate a Regulator DiTTo object
                    try:
                        api_regulator = Regulator(model)
                    except:
                        raise ValueError(
                            "Unable to instanciate Regulator DiTTo object."
                        )

                    try:
                        api_regulator.name = "Reg_" + settings["sectionid"]
                    except:
                        pass

                    try:
                        api_regulator.feeder_name = self.section_feeder_mapping[sectionID]
                    except:
                        pass

                    try:
                        api_regulator.substation_name = self.feeder_sub_mapping[api_regulator.feeder_name]
                    except:
                        api_regulator.substation_name = api_regulator.feeder_name

                    try:
                        api_regulator.connected_transformer = api_transformer.name
                    except:
                        raise ValueError("Unable to connect LTC to transformer")

                    taps = float(transformer_data["taps"])
                    lowerbandwidth = float(transformer_data["lowerbandwidth"])
                    upperbandwidth = float(transformer_data["upperbandwidth"])
                    minreg_range = int(float(settings["maxbuck"]))
                    maxreg_range = int(float(settings["maxboost"]))
                    setpoint = float(settings["setpoint"])
                    ct = int(float(settings["ct"]))
                    pt = int(float(settings["pt"]))
                    center_bandwidth = upperbandwidth - lowerbandwidth

                    api_regulator.ltc = 1
                    api_regulator.highstep = minreg_range
                    api_regulator.lowstep = maxreg_range
                    api_regulator.pt_ratio = pt
                    api_regulator.ct_ratio = ct
                    api_regulator.setpoint = setpoint
                    api_regulator.center_bandwidth = center_bandwidth
                    api_regulator.bandwidth = (
                        upperbandwidth + lowerbandwidth
                    )  # ie. use the average bandwidth. The upper and lower are typically the same
                    # TODO: Add unit checking. These units are in percentages. Need to be updated to be in Volts for consistency (BUG in cyme writer too)
                    # TODO: Decide whether or not to put parameters in for the regulator range, and what units they should be.

                try:
                    api_transformer.reactances = [float(xhl)]
                except:
                    pass

                # Here we know that we have two windings...
                for w in range(2):

                    # Instanciate a Winding DiTTo object
                    try:
                        api_winding = Winding(model)
                    except:
                        raise ValueError("Unable to instanciate Winding DiTTo object.")

                    # Set the rated power
                    try:
                        if w == 0:
                            api_winding.rated_power = (
                                float(transformer_data["kva"]) * 10 ** 3
                            )  # DiTTo in volt ampere
                        if w == 1:
                            api_winding.rated_power = (
                                float(transformer_data["kva"]) * 10 ** 3
                            )  # DiTTo in volt ampere
                    except:
                        pass

                    # Set the nominal voltage
                    try:
                        if w == 0:
                            # DiTTo in volt
                            api_winding.nominal_voltage = (
                                float(transformer_data["kvllprim"]) * 10 ** 3
                        )  # DiTTo in volt
                        if w == 1:
                            api_winding.nominal_voltage = (
                                float(transformer_data["kvllsec"]) * 10 ** 3
                            )  # DiTTo in volt
                    except:
                        pass

                    # Connection configuration
                    try:
                        api_winding.connection_type = self.transformer_connection_configuration_mapping(
                            transformer_data["conn"], w
                        )
                    except:
                        pass

                    # Resistance
                    try:
                        api_winding.resistance = R_perc
                    except:
                        pass

                    # For each phase...
                    for p in phases:

                        # Instanciate a PhaseWinding DiTTo object
                        try:
                            api_phase_winding = PhaseWinding(model)
                        except:
                            raise ValueError(
                                "Unable to instanciate PhaseWinding DiTTo object."
                            )

                        # Set the phase
                        try:
                            api_phase_winding.phase = p
                        except:
                            pass

                        # Add the phase winding object to the winding
                        api_winding.phase_windings.append(api_phase_winding)

                    # Add the winding object to the transformer
                    api_transformer.windings.append(api_winding)

            # Handle Grounding transformers
            if settings["type"] == "grounding_transformer":

                if settings["equipmentid"] in self.grounding_transformers:
                    transformer_data = self.grounding_transformers[
                        settings["equipmentid"]
                    ]
                else:
                    transformer_data = {}

                # Here we know that we have two windings...
                for w in range(2):

                    # Instanciate a Winding DiTTo object
                    try:
                        api_winding = Winding(model)
                    except:
                        raise ValueError("Unable to instanciate Winding DiTTo object.")

                    # Set the rated power
                    try:
                        if w == 0:
                            api_winding.rated_power = (
                                float(transformer_data["ratedcapacity"]) * 10 ** 3
                            )  # DiTTo in volt ampere
                        if w == 1:
                            api_winding.rated_power = (
                                float(transformer_data["ratedcapacity"]) * 10 ** 3
                            )  # DiTTo in volt ampere
                    except:
                        pass

                    # Set the nominal voltage
                    try:
                        if w == 0:
                            api_winding.nominal_voltage = (
                                float(transformer_data["ratedvoltage"]) * 10 ** 3
                            )  # DiTTo in volt
                        if w == 1:
                            api_winding.nominal_voltage = (
                                float(transformer_data["ratedvoltage"]) * 10 ** 3
                            )  # DiTTo in volt
                    except:
                        pass

                    # Set the connection configuration
                    try:
                        api_winding.connection_type = self.connection_configuration_mapping(
                            transformer_data["conn"]
                        )
                    except:
                        pass

                    # For each phase...
                    for p in phases:

                        # Instanciate a PhaseWinding DiTTo object
                        try:
                            api_phase_winding = PhaseWinding(model)
                        except:
                            raise ValueError(
                                "Unable to instanciate PhaseWinding DiTTo object."
                            )

                        # Set the phase
                        try:
                            api_phase_winding.phase = p
                        except:
                            pass

                        # Add the phase winding object to the winding
                        api_winding.phase_windings.append(api_phase_winding)

                    # Add the winding object to the transformer
                    api_transformer.windings.append(api_winding)

            # Add the transformer object to the list of transformers
            self._transformers.append(api_transformer)
            if not sectionID in self.section_duplicates:
                self.section_duplicates[sectionID] = []
            self.section_duplicates[sectionID].append(api_transformer)

        return 1

    def parse_regulators(self, model=None):
        print("Inside parse_regulators")
        """Parse the regulators from CYME to DiTTo.

        .. note::

        In CYME a regulator does not have to be associated with a transformer (as it is the case for OpenDSS for example).
        In addition, a regulator can monitor multiple phases.
        The parser should create the transformers and create separate regulator objects for different phases.
        """
        # Instanciate the list in which we store the DiTTo regulator objects
        self._regulators = []

        mapp_regulators = {
            "id": 0,
            "type": 1,
            "kva": 2,
            "kva_1": 3,
            "kva_2": 4,
            "kva_3": 5,
            "kva_4": 6,
            "kvln": 7,
            "forwardbandwidth": 11,
            "bandwidth": 11,  # For old CYME version 'forwardbandwidth' is just 'bandwidth'
            "ct": 13,
            "pt": 14,
        }
        mapp_regulator_settings = {
            "sectionid": 0,
            "eqid": 2,
            "coordx": 7,
            "coordy": 8,
            "phaseon": 9,
            "ct": 12,
            "pt": 13,
            "vseta": 16,
            "vsetb": 17,
            "vsetc": 18,
            "bandwidtha": 25,
            "bandwidthb": 26,
            "bandwidthc": 27,
            "tapa": 28,
            "tapb": 29,
            "tapc": 30,
            "conn": 31,
        }

        self.settings = {}
        self.regulators = {}

        #####################################################
        #                                                   #
        #                   NETWORK FILE                    #
        #                                                   #
        #####################################################
        #
        # Open the network file
        #self.get_file_content("network")

        # Loop over the network file
        #for line in self.content:
        try:
            self.content = iter(self.file_network_regulator)
            line = next(self.content)

            self.settings.update(
                self.parser_helper(
                    line,
                    ["regulator_settings"],
                    [
                        "sectionid",
                        "eqid",
                        "coordx",
                        "coordy",
                        "phaseon",
                        "ct",
                        "pt",
                        "vseta",
                        "vsetb",
                        "vsetc",
                        "bandwidtha",
                        "bandwidthb",
                        "bandwidthc",
                        "tapa",
                        "tapb",
                        "tapc",
                        "conn",
                    ],
                    mapp_regulator_settings,
                )
            )
        except:
            pass
        #####################################################
        #                                                   #
        #                 EQUIPMENT FILE                    #
        #                                                   #
        #####################################################
        #
        # Open the network file
        #self.get_file_content("equipment")

        # Loop over the network file
        #for line in self.content:
        try:
            self.content = iter(self.file_equipment_regulator)
            line = next(self.content)
            self.regulators.update(
                self.parser_helper(
                    line,
                    ["regulator"],
                    [
                        "id",
                        "type",
                        "kva",
                        "kva_1",
                        "kva_2",
                        "kva_3",
                        "kva_4",
                        "kvln",
                        "forwardbandwidth",
                        "bandwidth",
                        "ct",
                        "pt",
                    ],
                    mapp_regulators,
                )
            )
        except:
            pass

        for sectionID, settings in self.settings.items():

            sectionID = sectionID.strip("*").lower()

            try:
                phases = self.section_phase_mapping[sectionID]["phase"]
            except:
                raise ValueError("No phase for section {}".format(sectionID))

            try:
                phases_on = self.phase_mapping(settings["phaseon"])
            except:
                raise ValueError(
                    "Unable to get phases for regulator {}".format(sectionID)
                )

            if "eqid" in settings and settings["eqid"] in self.regulators:
                regulator_data = self.regulators[settings["eqid"]]
            else:
                regulator_data = {}

            for p in phases_on:

                if p not in phases:
                    logger.warning(
                        "Regulator {id} monitors phase {p} which is not in the section phases {pp}".format(
                            id=sectionID, p=p, pp=phases
                        )
                    )

                # Instanciate a Regulator DiTTo object
                try:
                    # Lusha
                    feedername = self.section_feeder_mapping[sectionID]
                    model = self.feeder_models[feedername]
                    api_regulator = Regulator(model)
                except:
                    raise ValueError("Unable to instanciate Regulator DiTTo object.")

                try:
                    api_regulator.name = "Reg_" + sectionID + "_" + p
                except:
                    pass

                try:
                    api_regulator.feeder_name = self.section_feeder_mapping[sectionID]
                except:
                    pass

                try:
                    api_regulator.substation_name = self.feeder_sub_mapping[api_regulator.feeder_name]
                except:
                    api_regulator.substation_name=api_regulator.feeder_name
                    pass

                try:
                    api_regulator.from_element = self.section_phase_mapping[sectionID][
                        "fromnodeid"
                    ]
                except:
                    pass

                try:
                    api_regulator.to_element = self.section_phase_mapping[sectionID][
                        "tonodeid"
                    ]
                except:
                    pass

                # Lusha
                if api_regulator.from_element not in self.node_feeder_mapping.keys():
                    self.node_feeder_mapping[api_regulator.from_element] = []
                if api_regulator.to_element not in self.node_feeder_mapping.keys():
                    self.node_feeder_mapping[api_regulator.to_element] = []
                if api_regulator.feeder_name not in self.node_feeder_mapping[api_regulator.from_element]:
                    self.node_feeder_mapping[api_regulator.from_element].append(api_regulator.feeder_name)
                if api_regulator.feeder_name not in self.node_feeder_mapping[api_regulator.to_element]:
                    self.node_feeder_mapping[api_regulator.to_element].append(api_regulator.feeder_name)


                try:
                    api_regulator.pt_phase = p
                except:
                    pass

                try:
                    position = Position(model)
                    position.long = float(reg_set["coordx"])
                    position.lat = float(reg_set["coordy"])
                    position.elevation = 0
                    api_regulator.positions.append(position)
                except:
                    pass

                try:
                    api_regulator.pt_ratio = float(settings["pt"])
                except:
                    pass

                try:
                    api_regulator.ct_prim = float(settings["ct"])
                except:
                    pass

                try:
                    if p == "A":
                        api_regulator.bandcenter = float(settings["vseta"])
                    if p == "B":
                        api_regulator.bandcenter = float(settings["vsetb"])
                    if p == "C":
                        api_regulator.bandcenter = float(settings["vsetc"])
                except:
                    pass

                try:
                    if (
                        p == "A"
                        and "bandwidtha" in settings
                        and settings["bandwidtha"] is not None
                    ):
                        api_regulator.bandwidth = float(settings["bandwidtha"])
                    elif "forwardbandwidth" in regulator_data:
                        api_regulator.bandwidth = float(
                            regulator_data["forwardbandwidth"]
                        )
                    else:
                        api_regulator.bandwidth = float(
                            regulator_data["bandwidth"]
                        )  # For old CYME versions

                    if (
                        p == "B"
                        and "bandwidthb" in settings
                        and settings["bandwidthb"] is not None
                    ):
                        api_regulator.bandwidth = float(settings["bandwidthb"])
                    elif "forwardbandwidth" in regulator_data:
                        api_regulator.bandwidth = float(
                            regulator_data["forwardbandwidth"]
                        )
                    else:
                        api_regulator.bandwidth = float(
                            regulator_data["bandwidth"]
                        )  # For old CYME versions

                    if (
                        p == "C"
                        and "bandwidthc" in settings
                        and settings["bandwidthc"] is not None
                    ):
                        api_regulator.bandwidth = float(settings["bandwidthc"])
                    elif "forwardbandwidth" in regulator_data:
                        api_regulator.bandwidth = float(
                            regulator_data["forwardbandwidth"]
                        )
                    else:
                        api_regulator.bandwidth = float(
                            regulator_data["bandwidth"]
                        )  # For old CYME versions
                except:
                    pass

                for w in range(2):

                    # Instanciate a Winding DiTTo object
                    try:
                        api_winding = Winding(model)
                    except:
                        raise ValueError("Unable to instanciate Winding DiTTo object.")

                    # Set the rated power
                    try:
                        api_winding.rated_power = (
                            float(regulator_data["kva"]) * 10 ** 3
                        )  # DiTTo in volt ampere
                    except:
                        pass

                    # Set the connection type
                    try:
                        api_winding.connection_type = self.connection_configuration_mapping(
                            settings["conn"]
                        )
                    except:
                        pass

                    # Set the nominal voltage
                    try:
                        api_winding.nominal_voltage = float(regulator_data["kvln"])
                    except:
                        pass

                    # Instanciate a PhaseWinding DiTTo object
                    try:
                        api_phase_winding = PhaseWinding(model)
                    except:
                        raise ValueError("Unable to instanciate PhaseWinding object.")

                    # Set the phase
                    try:
                        api_phase_winding.phase = p
                    except:
                        pass

                    # Append the phaseWinding object to the winding
                    api_winding.phase_windings.append(api_phase_winding)

                    # api_transformer.windings.append(api_winding)

                    # Add the winding object to the regulator
                    api_regulator.windings.append(api_winding)

                self._regulators.append(api_regulator)
                if not sectionID in self.section_duplicates:
                    self.section_duplicates[sectionID] = []
                self.section_duplicates[sectionID].append(api_regulator)

        return 1

    def parse_network_equivalent(self, model=None):
        """Parse Network equivalent objects from CYME into DiTTo.
            Network Equivalent objects are elements which have been reduced by cyme (using its network reduction capabilities)
            They encapsulate multiple loads, lines and transformers into one equivalent object
            This function creates load and line objects to represent the network equivalent objects from CYME
        """

        self._network_equivalents = {}
        mapp_section = {"sectionid": 0, "fromnodeid": 1, "tonodeid": 2, "phase": 3}
        mapp_network_equivalents = { 
                "sectionid":0,
                "devicenumber": 2,
                "coordx": 6,
                "coordy": 7,
                'zraa':9,
                'zrab':10, 
                'zrac':11,
                'zrba': 12,
                'zrbb':13,
                'zrbc':14,
                'zrca':15,
                'zrcb':16,
                'zrcc':17,
                'zxaa':18,
                'zxab':19,
                'zxac':20,
                'zxba':21,
                'zxbb': 22,
                'zxbc': 23,
                'zxca':24,
                'zxcb':25,
                'zxcc':26,
                'loadfromkwa': 27,
                'loadfromkwb': 28,
                'loadfromkwc':29,
                'loadfromkvara': 30,
                'loadfromkvarb':31,
                'loadfromkvarc':32,
                'loadtokwa':33,
                'loadtokwb': 34,
                'loadtokwc':35,
                'loadtokvara':36,
                'loadtokvarb':37,
                'loadtokvarc':38,
                'totallengtha':39,
                'totallengthb': 40,
                'totallengthc': 41,
                }
        # Open the network file
        self.get_file_content("network")

        # Loop over the network file
        for line in self.content:
            #########################################
            #                                       #
            #         NETWORK EQUIVALENTS.          #
            #                                       #
            #########################################
            #
            self.settings = self.update_dict(
                self.settings,
                self.parser_helper(
                    line,
                    ["network_equivalent_setting"],
                    ['sectionid', 'devicenumber', 'coordx', 'coordy', 'zraa', 'zrab', 'zrac', 'zrba', 'zrbb', 'zrbc', 'zrca', 'zrcb', 'zrcc', 'zxaa', 'zxab', 'zxac', 'zxba', 'zxbb', 'zxbc', 'zxca', 'zxcb', 'zxcc', 'loadfromkwa', 'loadfromkwb', 'loadfromkwc', 'loadfromkvara', 'loadfromkvarb', 'loadfromkvarc', 'loadtokwa', 'loadtokwb', 'loadtokwc', 'loadtokvara', 'loadtokvarb', 'loadtokvarc', 'totallengtha', 'totallengthb', 'totallengthc'],

                    mapp_network_equivalents,
                    {"type": "network_equivalent"},
                ),
            )

            #########################################
            #                                       #
            #              SECTIONS.                #
            #                                       #
            #########################################
            #
            self.settings = self.update_dict(
                self.settings,
                self.parser_helper(
                    line,
                    ["section"],
                    ["sectionid", "fromnodeid", "tonodeid", "phase"],
                    mapp_section,
                ),
            )

        for sectionID, settings in self.settings.items():

            sectionID = sectionID.strip("*").lower()

            # Lusha
            feedername = self.section_feeder_mapping[sectionID]
            model = self.feeder_models[feedername]

            if 'type' in settings and settings['type'] == 'network_equivalent':


                #### Create Line for Network equivalent  ###

                api_line = Line(model)
                api_line.from_element = self.section_phase_mapping[sectionID][ "fromnodeid" ]
                api_line.to_element = self.section_phase_mapping[sectionID][ "tonodeid" ]
                api_line.name = sectionID+'_ne_line'
                # Set the connection index for the from_element (info is in the section)
                try:
                    api_line.from_element_connection_index = int( self.section_phase_mapping[sectionID]["fromnodeindex"])
                except:
                    pass
    
                # Set the connection index for the from_element (info is in the section)
                try:
                    api_line.to_element_connection_index = int( self.section_phase_mapping[sectionID]["tonodeindex"])
                except:
                    pass

                try:
                    api_line.feeder_name = self.section_feeder_mapping[sectionID]
                except:
                    pass

                try:
                    api_line.substation_name = self.feeder_sub_mapping[api_line.feeder_name]
                except:
                    api_line.substation_name = api_line.feeder_name

                # Set the position
                try:
                    position = Position(model)
                    position.long = float(settings["coordx"])
                    position.lat = float(settings["coordy"])
                    position.elevation = 0
                    api_line.position = position
                except:
                    pass

                # Set the line type
                api_line.is_switch = False
                api_line.is_fuse = False
                api_line.is_recloser = False
                api_line.is_breaker = False
                api_line.is_sectionalizer = False
                api_line.is_network_protector = False
                if "eqid" in settings:
                    api_line.nameclass = settings["eqid"]
                api_line.line_type = 'overhead' #set all network equivalent lines to be overhead by default.


                phases = []
                if float(settings['zraa']) !=0:
                    phases.append('A')
                if float(settings['zrbb']) !=0:
                    phases.append('B')
                if float(settings['zrcc']) !=0:
                    phases.append('C')

                api_line.wires = []
                for phase in phases:
                    api_wire = Wire(model)
                    api_wire.phase = phase
                    api_line.wires.append(api_wire)

                impedance_matrix = []
                for phase1 in phases:
                    impedance_matrix_inner = []
                    for phase2 in phases:
                        resistance_name = 'zr'+phase1.lower() +phase2.lower()
                        reactance_name = 'zx'+phase1.lower() +phase2.lower()
                        impedance_element = complex(float(settings[resistance_name]),float(settings[reactance_name]))
                        impedance_matrix_inner.append(impedance_element)
                    impedance_matrix.append(impedance_matrix_inner)
                api_line.impedance_matrix = impedance_matrix


                max_distance = max(float(settings['totallengtha']), float(settings['totallengthb']),float(settings['totallengthc']))
                api_line.length = max_distance # outputs in SI units

                ### Create load at from node
                total_load_from = 0
                total_load_from_kvar = 0
                for ph in phases:
                    total_load_from += float(settings['loadfromkw'+ph.lower()])
                    total_load_from_kvar += float(settings['loadfromkvar'+ph.lower()])

                if total_load_from > 0 and total_load_from_kvar > 0:
                    api_load_from = Load(model)
                    api_load_from.model=1
                    api_load_from.connecting_element = self.section_phase_mapping[sectionID][ "fromnodeid" ]
                    api_load_from.name = sectionID+'_ne_from_load'
                    # Set the connection index for the from_element (info is in the section)
                
                    api_load_from.phase_loads = []
                    try:
                        api_load_from.feeder_name = self.section_feeder_mapping[sectionID]
                    except:
                        pass


                    for ph in phases:
                        try:
                            api_phase_load_from = PhaseLoad(model)
                        except:
                            raise ValueError(
                                "Unable to instanciate PhaseLoad DiTTo object."
                            )
    
                        try:
                            api_phase_load_from.phase = ph
                        except:
                            pass
    
                        try:
                            api_phase_load_from.p, api_phase_load_from.q = (
                                10 ** 3 * float(settings['loadfromkw'+ph.lower()]),
                                10 ** 3 * float(settings['loadfromkvar'+ph.lower()]),
                            )
                        except:
                            pass
    
                        # TODO : use load_type_data
                        api_phase_load_from.ppercentcurrent = 0
                        api_phase_load_from.qpercentcurrent = 0
                        api_phase_load_from.ppercentpower = 1
                        api_phase_load_from.qpercentpower = 1
                        api_phase_load_from.ppercentimpedance = 0
                        api_phase_load_from.qpercentimpedance = 0
    
                        api_load_from.phase_loads.append(api_phase_load_from)

                ### Create load at from node
                total_load_to = 0
                total_load_to_kvar = 0
                for ph in phases:
                    total_load_to += float(settings['loadtokw'+ph.lower()])
                    total_load_to_kvar += float(settings['loadfromkvar'+ph.lower()])

                if total_load_to > 0 and total_load_to_kvar > 0:
                    api_load_to = Load(model)
                    api_load_to.model=1
                    api_load_to.connecting_element = self.section_phase_mapping[sectionID][ "tonodeid" ]
                    api_load_to.name = sectionID+'_ne_to_load'
                    # Set the connection index for the from_element (info is in the section)
    
                    api_load_to.phase_loads = []
                    try:
                        api_load_to.feeder_name = self.section_feeder_mapping[sectionID]
                    except:
                        pass

                    for ph in phases:
                        try:
                            api_phase_load_to = PhaseLoad(model)
                        except:
                            raise ValueError(
                                "Unable to instanciate PhaseLoad DiTTo object."
                            )
    
                        try:
                            api_phase_load_to.phase = ph
                        except:
                            pass
    
                        try:
                            api_phase_load_to.p, api_phase_load_to.q = (
                                10 ** 3 * float(settings['loadtokw'+ph.lower()]),
                                10 ** 3 * float(settings['loadtokvar'+ph.lower()]),
                            )
                        except:
                            pass
    
                        # TODO : use load_type_data
                        api_phase_load_to.ppercentcurrent = 0
                        api_phase_load_to.qpercentcurrent = 0
                        api_phase_load_to.ppercentpower = 1
                        api_phase_load_to.qpercentpower = 1
                        api_phase_load_to.ppercentimpedance = 0
                        api_phase_load_to.qpercentimpedance = 0
    
    
                        api_load_to.phase_loads.append(api_phase_load_to)
    



    def parse_loads(self, model=None):
        print("Inside parse_loads")
        """Parse the loads from CYME to DiTTo."""
        # Instanciate the list in which we store the DiTTo load objects
        self._loads = {}

        mapp_loads = {"sectionid": 0, "devicenumber": 1, "loadtype": 4, "connection": 5}

        mapp_customer_loads = {
            "sectionid": 0,
            "devicenumber": 1,
            "loadtype": 2,
            "customernumber": 3,
            "customertype": 4,
            "loadmodelid": 8,
            "valuetype": 11,
            "loadphase": 12,
            "value1": 13,
            "value2": 14,
            "connectedkva": 15,
            "numberofcustomer": 17,
        }

        mapp_customer_class = {
            "id": 0,
            "constantpower": 4,
            "constantcurrent": 5,
            "constantimpedance": 6,
            "powerfactor": 8,
            "constantimpedancezp": 17,
            "constantimpedancezq": 18,
            "constantcurrentip": 19,
            "constantcurrentiq": 20,
            "constantpowerpp": 21,
            "constantpowerpq": 22,
        }

        self.loads = {}
        self.customer_loads = {}
        self.customer_class = {}

        #####################################################
        #                                                   #
        #                     LOAD FILE                     #
        #                                                   #
        #####################################################
        #
        # Open the network file
        self.get_file_content("load")

        # Loop over the load file
        for line in self.content:

            #########################################
            #                                       #
            #                 LOADS                 #
            #                                       #
            #########################################
            #
            self.loads.update(
                self.parser_helper(
                    line,
                    ["loads"],
                    ["sectionid", "devicenumber", "loadtype", "connection"],
                    mapp_loads,
                )
            )

            #########################################
            #                                       #
            #           CUSTOMER LOADS              #
            #                                       #
            #########################################
            #
            self.customer_loads.update(
                self.parser_helper(
                    line,
                    ["customer_loads"],
                    [
                        "sectionid",
                        "devicenumber",
                        "loadtype",
                        "customernumber",
                        "customertype",
                        "loadmodelid",
                        "valuetype",
                        "loadphase",
                        "value1",
                        "value2",
                        "connectedkva",
                        "numberofcustomer",
                    ],
                    mapp_customer_loads,
                )
            )

            #########################################
            #                                       #
            #           CUSTOMER CLASS              #
            #                                       #
            #########################################
            #
            self.customer_class.update(
                self.parser_helper(
                    line,
                    ["customer_class"],
                    [
                        "id",
                        "constantpower",
                        "constantcurrent",
                        "constantimpedance",
                        "powerfactor",
                        "constantimpedancezp",
                        "constantimpedancezq",
                        "constantcurrentip",
                        "constantcurrentiq",
                        "constantpowerpp",
                        "constantpowerpq",
                    ],
                    mapp_customer_class,
                )
            )

        duplicate_loads = set()
        for sectionID in self.customer_loads.keys():
            if sectionID.endswith("*"):
                duplicate_loads.add(sectionID.lower().strip("*"))
        for sectionID, settings in self.customer_loads.items():

            sectionID = sectionID.strip("*").lower()

            feedername = self.section_feeder_mapping[sectionID]
            model = self.feeder_models[feedername]

            if sectionID in self.loads:
                load_data = self.loads[sectionID]
            else:
                load_data = {}

            # Lusha
            if "loadmodelid" in settings:
                load_model_id =  int(settings["loadmodelid"])

            # Lusha
            # choose load model to use
            # PHI 1 is default, 2 is winter, 3 is summer
            # BGE 1 is default, 2 is summer, 4 is winter
            if load_model_id == 1:

                if "connectedkva" in settings:
                    connectedkva = float(settings["connectedkva"])
                else:
                    connectedkva = None

                if "valuetype" in settings:
                    value_type = int(settings["valuetype"])

                if "value1" in settings and "value2" in settings:
                    if (
                        float(settings["value1"]) == 0.0
                        and float(settings["value2"]) == 0.0
                    ):
                        p = 0
                        q = 0
                    elif value_type == 0:  # P and Q are given
                        try:
                            p, q = float(settings["value1"]), float(settings["value2"])
                        except:
                            logger.warning(
                                "WARNING:: Skipping load on section {}".format(sectionID)
                            )
                            continue
                    elif value_type == 1:  # KVA and PF are given
                        try:
                            kva, PF = (
                                float(settings["value1"]),
                                float(settings["value2"]) * 0.01,
                            )
                            if kva == 0 and "connectedkva" in settings:
                                kva = float(settings["connectedkva"])
                            p = kva * PF
                            q = math.sqrt(kva ** 2 - p ** 2)
                        except:
                            logger.warning(
                                "WARNING:: Skipping load on section {}".format(sectionID)
                            )
                            continue
                    elif value_type == 2:  # P and PF are given

                        try:
                            p, PF = float(settings["value1"]), float(settings["value2"])
                            if 0 <= PF <= 1:
                                q = p * math.sqrt((1 - PF ** 2) / PF ** 2)
                            elif 1 < PF <= 100:
                                PF /= 100.0
                                q = p * math.sqrt((1 - PF ** 2) / PF ** 2)
                            else:
                                logger.warning("problem with PF")
                                logger.warning(PF)
                        except:
                            logger.warning("Skipping load on section {}".format(sectionID))
                            continue

                    elif value_type == 3:  # AMP and PF are given
                        # TODO
                        logger.warning(
                            "WARNING:: Skipping load on section {}".format(sectionID)
                        )
                        continue

                    if p >= 0 or q >= 0:

                        if "loadphase" in settings:
                            phases = settings["loadphase"]
                        else:
                            phases = []


                        fused = False
                        if sectionID in duplicate_loads:
                            fusion = True
                            if sectionID in self._loads:
                                api_load = self._loads[sectionID]
                                fused = True
                            elif p != 0:
                                api_load = Load(model)
                        else:
                            fusion = False
                            api_load = Load(model)

                        if fusion and p == 0:
                            # logger.warning(
                            #    "WARNING:: Skipping duplicate load on section {} with p=0".format(sectionID)
                            # )
                            continue

                        try:
                            if fusion and sectionID in self._loads:
                                api_load.name += "_" + reduce(
                                    lambda x, y: x + "_" + y, phases
                                )
                            else:
                                api_load.name = (
                                    "Load_"
                                    + sectionID
                                    + "_"
                                    + reduce(lambda x, y: x + "_" + y, phases)
                                )
                        except:
                            pass

                        try:
                            if not (fusion and sectionID in self._loads):
                                if connectedkva is not None:
                                    api_load.transformer_connected_kva = (
                                        connectedkva * 10 ** 3
                                    )  # DiTTo in var
                            elif connectedkva is not None:
                                if api_load.transformer_connected_kva is None:
                                    api_load.transformer_connected_kva = (
                                        connectedkva * 10 ** 3
                                    )  # DiTTo in var
                                else:
                                    api_load.transformer_connected_kva += (
                                        connectedkva * 10 ** 3
                                    )  # DiTTo in var
                        except:
                            pass

                        try:
                            if not (fusion and sectionID in self._loads):
                                api_load.connection_type = self.connection_configuration_mapping(
                                    load_data["connection"]
                                )
                        except:
                            pass

                        if not (fusion and sectionID in self._loads):
                            if (
                                "loadtype" in settings
                                and settings["loadtype"] in self.customer_class
                            ):
                                load_type_data = self.customer_class[settings["loadtype"]]
                            else:
                                load_type_data = {}

                        try:
                            if not (fusion and sectionID in self._loads):
                                api_load.connecting_element = self.section_phase_mapping[
                                    sectionID
                                ]["fromnodeid"]
                        except:
                            pass

                        try:
                            feeder_name = self.section_feeder_mapping[sectionID]
                            api_load.feeder_name = feeder_name
                        except:
                            pass

                        # Lusha
                        try:
                            api_load.substation_name = self.feeder_sub_mapping[feeder_name]
                        except:
                            api_load.substation_name = feeder_name

                        api_load.num_users = float(settings["numberofcustomer"])

                        for ph in phases:
                            try:
                                api_phase_load = PhaseLoad(model)
                            except:
                                raise ValueError(
                                    "Unable to instanciate PhaseLoad DiTTo object."
                                )

                            try:
                                api_phase_load.phase = ph
                            except:
                                pass

                            try:
                                api_phase_load.p, api_phase_load.q = (
                                    10 ** 3 * p / len(phases),
                                    10 ** 3 * q / len(phases),
                                )
                            except:
                                pass

                            # ZIP load parameters
                            try:
                                api_phase_load.ppercentcurrent = (
                                    float(load_type_data["constantcurrentip"]) / 100.0
                                )
                                api_phase_load.qpercentcurrent = (
                                    float(load_type_data["constantcurrentiq"]) / 100.0
                                )
                                api_phase_load.ppercentpower = (
                                    float(load_type_data["constantpowerpp"]) / 100.0
                                )
                                api_phase_load.qpercentpower = (
                                    float(load_type_data["constantpowerpq"]) / 100.0
                                )
                                api_phase_load.ppercentimpedance = (
                                    float(load_type_data["constantimpedancezp"]) / 100.0
                                )
                                api_phase_load.qpercentimpedance = (
                                    float(load_type_data["constantimpedancezq"]) / 100.0
                                )
                                # api_phase_load.use_zip=1
                                # api_phase_load.model=8
                            except:
                                pass

                            # CYME store phase loads with P=0 and Q=0.
                            # Do not add them to DiTTo (otherwise it will make the validation
                            # on the number of objects fail since we will have many more loads than there actually are...)
                            # if api_phase_load.p!=0 or api_phase_load.q!=0:
                            api_load.phase_loads.append(api_phase_load)


                        self._loads[sectionID] = api_load
                        if not sectionID in self.section_duplicates:
                            self.section_duplicates[sectionID] = []
                        if not fused: #Because mutiple loads on different phases are joined into a single one
                            self.section_duplicates[sectionID].append(api_load)
            else:
                print("no load found\n")
        return 1

    def parse_dg(self, model):
        """ Parse the Distributed Generation from CYME to DiTTo. May be respresented as ECGs or PVs.
            This reads the objets [CONVERTER], [CONVERTER CONTROL SETTING], [LONG TERM DYNAMICS CURVE EXT] [DGGENERATIONMODEL] and in the case when PV is included [PHOTOVOLTAIC SETTINGS]"""
        self._dgs = []
        self.converter = {}
        self.converter_settings = {}
        self.long_term_dynamics = {}
        self.photovoltaic_settings = {}
        self.bess = {}
        self.bess_settings = {}
        self.dg_generation = {}

        mapp_converter = {
            "devicenumber": 0,
            "devicetype": 1,
            "converterrating": 2,
            "activepowerrating": 3,
            "reactivepowerrating": 4,
            "minimumpowerfactor": 5,
            "powerfalllimit": 23,
            "powerriselimit": 24,
            "risefallunit": 25,
        }

        mapp_converter_settings = {
            "devicenumber": 0,
            "devicetype": 1,
            "controlindex": 2,
            "timetriggerindex": 3,
            "controltype": 4,
            "fixedvarinjection": 5,
            "injectionreference": 6,
            "convertercontrolid": 7,
            "powerreference": 8,
            "powerfactor": 9,
        }

        mapp_photovoltaic_settings = {
            "sectionid": 0,
            "location": 1,
            "devicenumber": 2,
            "equipmentid": 6,
            "eqphase": 7,
            "ambienttemperature": 11,
        }

        mapp_bess = {
            "id": 0,
            "ratedstorageenergy": 1,
            "maxchargingpower": 2,
            "maxdischargingpower": 3,
            "chargeefficiency": 4,
            "dischargeefficiency": 5,
        }

        mapp_bess_settings = {
            "sectionid": 0,
            "devicenumber": 2,
            "equipmentid": 6,
            "phase": 7,
            "maximumsoc": 10,
            "minimumsoc": 11,
            "initialsoc": 16,
        }

        mapp_bess = {
            "id": 0,
            "ratedstorageenergy": 1,
            "maxchargingpower": 2,
            "maxdischargingpower": 3,
            "chargeefficiency": 4,
            "dischargeefficiency": 5,
        }

        mapp_bess_settings = {
            "sectionid": 0,
            "devicenumber": 2,
            "equipmentid": 6,
            "phase": 7,
            "maximumsoc": 10,
            "minimumsoc": 11,
            "initialsoc": 16,
        }

        mapp_long_term_dynamics = {
            "devicenumber": 0,
            "devicetype": 1,
            "adjustmentsettings": 2,
            "powercurvemodel": 3,
        }

        mapp_dg_generation_model = {
            "devicenumber": 0,
            "devicetype": 1,
            "loadmodelname": 2,
            "activegeneration": 3,
            "powerfactor": 4,
        }

        #####################################################
        #                                                   #
        #                   NETWORK FILE                    #
        #                                                   #
        #####################################################
        #
        # Open the network file
        self.get_file_content("network")

        # Loop over the network file
        for line in self.content:

            #########################################
            #                                       #
            #              CONVERTER                #
            #                                       #
            #########################################

            self.converter.update(
                self.parser_helper(
                    line,
                    ["converter"],
                    [
                        "devicenumber",
                        "devicetype",
                        "converterrating",
                        "activepowerrating",
                        "reactivepowerrating",
                        "minimumpowerfactor",
                        "powerfalllimit",
                        "powerriselimit",
                        "risefallunit",
                    ],
                    mapp_converter,
                    {"type": "converter"},
                )
            )

            #########################################
            #                                       #
            #    CONVERTER CONTROL SETTINGS         #
            #                                       #
            #########################################

            self.converter_settings.update(
                self.parser_helper(
                    line,
                    ["converter_control_settings"],
                    [
                        "devicenumber",
                        "devicetype",
                        "controltype",
                        "fixedvarinjection",
                        "injectionreference",
                        "convertercontrolid",
                        "powerreference",
                        "powerfactor",
                    ],
                    mapp_converter_settings,
                    {"type": "converter_settings"},
                )
            )

            #########################################
            #                                       #
            #      PHOTOVOLTAIC SETTINGS            #
            #                                       #
            #########################################

            self.photovoltaic_settings.update(
                self.parser_helper(
                    line,
                    ["photovoltaic_settings"],
                    ["sectionid", "devicenumber", "eqphase", "ambienttemperature"],
                    mapp_photovoltaic_settings,
                    {"type": "photovoltaic_settings"},
                )
            )

            #########################################
            #                                       #
            #              BESS SETTINGS            #
            #                                       #
            #########################################

            self.bess_settings.update(
                self.parser_helper(
                    line,
                    ["bess_settings"],
                    [
                        "sectionid",
                        "devicenumber",
                        "equipmentid",
                        "phase",
                        "maximumsoc",
                        "minimumsoc",
                        "initialsoc",
                    ],
                    mapp_bess_settings,
                    {"type": "bess_settings"},
                )
            )

            #########################################
            #                                       #
            #    LONG TERM DYNAMICS CURVE EXT       #
            #                                       #
            #########################################

            self.long_term_dynamics.update(
                self.parser_helper(
                    line,
                    ["long_term_dynamics_curve_ext"],
                    [
                        "devicenumber",
                        "devicetype",
                        "adjustmentsettings",
                        "powercurvemodel",
                    ],
                    mapp_long_term_dynamics,
                    {"type": "long_term_dynamics"},
                )
            )

            #########################################
            #                                       #
            #         DGGENERATIONMODEL             #
            #                                       #
            #########################################

            self.dg_generation.update(
                self.parser_helper(
                    line,
                    ["dggenerationmodel"],
                    [
                        "devicenumber",
                        "devicetype",
                        "activegeneration",
                        "powerfactor",
                        "loadmodelname",
                    ],
                    mapp_dg_generation_model,
                    {"type": "dg_generation_model"},
                )
            )

        #####################################################
        #                                                   #
        #                 EQUIPMENT FILE                    #
        #                                                   #
        #####################################################
        #
        # Open the equipment file
        self.get_file_content("equipment")

        # Loop over the equipment file
        for line in self.content:

            #########################################
            #                                       #
            #                  BESS                 #
            #                                       #
            #########################################
            #
            self.bess.update(
                self.parser_helper(
                    line,
                    ["bess"],
                    [
                        "id",
                        "ratedstorageenergy",
                        "maxchargingpower",
                        "maxdischargingpower",
                        "chargeefficiency",
                        "dischargeefficiency",
                    ],
                    mapp_bess,
                )
            )

        api_photovoltaics = {}
        api_bessi = {}
        for sectionID, settings in self.photovoltaic_settings.items():
            try:
                api_photovoltaic = Photovoltaic(model)
            except:
                raise ValueError(
                    "Unable to instanciate photovoltaic {id}".format(id=sectionID)
                )
            try:
                api_photovoltaic.name = "PV_" + settings["devicenumber"].lower()
                api_photovoltaic.feeder_name = self.section_feeder_mapping[
                    sectionID.lower()
                ]
                api_photovoltaics[settings["devicenumber"].lower()] = api_photovoltaic
            except:
                raise ValueError(
                    "Unable to set photovoltaic name for {id}".format(id=sectionID)
                )

            try:
                api_photovoltaic.temperature = float(
                    settings["ambienttemperature"]
                )  # Not included in ECG SETTINGS
            except:
                pass

            try:
                api_photovoltaic.phases = [
                    Unicode(k) for k in list(settings["eqphase"])
                ]
            except:
                pass
            try:
                api_photovoltaic.connecting_element = self.section_phase_mapping[
                    sectionID.lower()
                ]["fromnodeid"]
            except:
                pass

            if not sectionID in self.section_duplicates:
                self.section_duplicates[sectionID] = []
            self.section_duplicates[sectionID].append(api_photovoltaic)

        for sectionID, settings in self.bess_settings.items():
            try:
                api_bess = Storage(model)
            except:
                raise ValueError("Unable to instanciate bess {id}".format(id=sectionID))
            try:
                api_bess.name = "BESS_" + settings["devicenumber"].lower()
                api_bess.feeder_name = self.section_feeder_mapping[sectionID.lower()]
                api_bessi[settings["devicenumber"].lower()] = api_bess
            except:
                raise ValueError(
                    "Unable to set bess name for {id}".format(id=sectionID)
                )

            phase_storages = []
            if "phase" in settings:
                phases = self.phase_mapping(settings["phase"])
            else:
                phases = ["A", "B", "C"]

            for phase in phases:
                phase_storage = PhaseStorage(model)
                phase_storage.phase = phase
                phase_storages.append(phase_storage)

            api_bess.phase_storages = phase_storages

            if "equipmentid" in settings:
                dev_num = settings["equipmentid"]
            else:
                dev_num = None

            if dev_num is not None and dev_num in self.bess:
                bess_data = self.bess[dev_num]
                try:
                    api_bess.rated_kWh = float(bess_data["ratedstorageenergy"])
                except:
                    pass

                try:
                    api_bess.chargeefficiency = float(bess_data["chargingefficiency"])
                except:
                    pass

                try:
                    api_bess.dischargeefficiency = float(
                        bess_data["dischargeefficiency"]
                    )
                except:
                    pass

                try:
                    charging = float("inf")
                    discharging = float("inf")
                    if "maxchargingpower" in bess_data:
                        charging = float(bess_data["maxchargingpower"])
                    if "maxdischargingpower" in bess_data:
                        discharging = float(bess_data["maxdischargingpower"])
                    power = min(charging, discharging) * 1000
                    if power < float("inf"):
                        average_power = power / float(len(phase_storages))
                        for ps in phase_storages:
                            ps.p = average_power
                except:
                    pass

            try:
                api_bess.reserve = float(settings["maximumsoc"])
            except:
                pass

            try:
                api_bess.stored_kWh = (
                    float(settings["initialsoc"]) * api_bess.rated_kWh / 100.0
                )
            except:
                pass

            try:
                api_bess.connecting_element = self.section_phase_mapping[
                    sectionID.lower()
                ]["fromnodeid"]
            except:
                pass

            if not sectionID in self.section_duplicates:
                self.section_duplicates[sectionID] = []
            self.section_duplicates[sectionID].append(api_bess)

        for deviceID, settings in self.dg_generation.items():
            deviceID = deviceID.strip(
                "*"
            ).lower()  # TODO: Deal with multiple configurations for the same location
            api_photovoltaic = api_photovoltaics[deviceID]

            # Use the default setting if available
            if (
                "loadmodelname" in settings
                and settings["loadmodelname"].lower() == "default"
            ):
                try:
                    api_photovoltaic.active_rating = (
                        float(settings["activegeneration"]) * 1000
                    )
                except:
                    pass
                try:
                    api_photovoltaic.power_factor = (
                        float(settings["powerfactor"]) / 100.0
                    )
                except:
                    pass

        for deviceID, settings in self.converter.items():

            deviceID = deviceID.strip(
                "*"
            ).lower()  # TODO: Deal with multiple configurations for the same location
            if deviceID in api_photovoltaics:
                api_photovoltaic = api_photovoltaics[deviceID]
                try:
                    api_photovoltaic.rated_power = (
                        float(settings["activepowerrating"]) * 1000
                    )
                except:
                    pass
                try:
                    api_photovoltaic.reactive_rating = (
                        float(settings["reactivepowerrating"]) * 1000
                    )
                except:
                    pass
                try:
                    api_photovoltaic.min_powerfactor = (
                        float(settings["minimumpowerfactor"]) / 100.0
                    )
                except:
                    pass
                try:
                    api_photovoltaic.fall_limit = float(settings["powerfalllimit"])
                except:
                    pass
                try:
                    api_photovoltaic.rise_limit = float(settings["powerriselimit"])
                except:
                    pass
                # TODO: check the units being used
            elif deviceID in api_bessi:
                api_bess = api_bessi[deviceID]
                try:
                    api_bess.rated_power = float(settings["activepowerrating"]) * 1000
                except:
                    pass
                try:
                    api_bess.reactive_rating = (
                        float(settings["reactivepowerrating"]) * 1000
                    )
                except:
                    pass
                try:
                    api_bess.min_powerfactor = (
                        float(settings["minimumpowerfactor"]) / 100.0
                    )
                except:
                    pass

        for deviceID, settings in self.converter_settings.items():
            deviceID = deviceID.strip(
                "*"
            ).lower()  # TODO: Deal with multiple configurations for the same location
            if deviceID in api_photovoltaics:
                api_photovoltaic = api_photovoltaics[deviceID]
                try:
                    control_type = str(settings["controltype"])
                    if control_type == "1":
                        api_photovoltaic.control_type = "voltvar_vars_over_watts"
                    if control_type == "0":
                        api_photovoltaic.control_type = "voltvar_watts_over_vars"
                    if control_type == "2":
                        api_photovoltaic.control_type = "voltvar_fixedvars"
                    if control_type == "3":
                        api_photovoltaic.control_type = "voltvar_novars"
                    if control_type == "5":
                        api_photovoltaic.control_type = "voltwatt"
                    if control_type == "6":
                        api_photovoltaic.control_type = "watt_powerfactor"
                    if control_type == "10":
                        api_photovoltaic.control_type = "powerfactor"
                except:
                    pass

                try:
                    api_photovoltaic.var_injection = float(
                        settings["fixedvarinjection"]
                    )
                except:
                    pass
                try:
                    curve = float(settings["convertercontrolid"])
                    if (
                        api_photovoltaic.control_type == "voltvar_watts_over_vars"
                        or api_photovoltaic.control_type == "voltvar_vars_over_watts"
                    ):
                        api_photovoltaic.voltvar_curve = curve
                    if api_photovoltaic.control_type == "voltwatt":
                        api_photovoltaic.voltwatt_curve = curve
                    if api_photovoltaic.control_type == "watt_powerfactor":
                        api_photovoltaic.watt_powerfactor_curve = curve
                except:
                    pass

                try:
                    pf = float(settings["powerfactor"]) / 100.0
                    api_photovoltaic.power_factor = pf
                except:
                    pass

    def fix_section_overlaps(self, model=None, **kwargs):
        """
        Some sections will have multiple components included in them (e.g. a line, transformer and capacitor).
        This function identifies the sections that have multiple components in them and creates intermediate nodes between them
        so that they are not connected in parallel

        Place components in series:
            Regulator -> Transformer -> Line -> (Loads, PV, BESS, Capacitors)

        :param model: DiTTo model
        :type model: DiTTo model
        :param verbose: Set the verbose mode. Optional. Default=True
        :type verbose: bool
        """
        #model.set_names()
        multiple_elements = {}
        for i,j in self.section_duplicates.items():
            if len(j)>1:
                multiple_elements[i] = j

        for sectionID in multiple_elements:
            connectors = []
            regulators = []
            transformers = []
            lines = [] #Warning - if multiple lines are used the names will be the same
            loads = []
            pvs = []
            bess = []
            capacitors = []

            from_element = None
            to_element = None
            connector_count = 0

            # Lusha
            feedername = self.section_feeder_mapping[sectionID]
            model = self.feeder_models[feedername]
            model.set_names()

            for element in multiple_elements[sectionID]:
                if isinstance(element,Regulator):
                    regulators.append(element)
                    from_element = element.from_element
                    to_element = element.to_element
                    connector_count+=1
                if isinstance(element,PowerTransformer):
                    transformers.append(element)
                    from_element = element.from_element
                    to_element = element.to_element
                    connector_count+=1
                if isinstance(element,Line):
                    lines.append(element)
                    from_element = element.from_element
                    to_element = element.to_element
                    connector_count+=1
                if isinstance(element,Load):
                    loads.append(element)
                if isinstance(element,Storage):
                    bess.append(element)
                if isinstance(element,Capacitor):
                    capacitors.append(element)

            # Lusha
            #connectors = [regulators,transformers,lines]
            connectors = [transformers, lines]
            non_connectors = [loads,bess,pvs,capacitors]

            if from_element is None or to_element is None: # i.e. just loads, pvs and caps so no problem
                continue

            original_from_element = from_element


            # Lusha
            if original_from_element not in model.model_names.keys():
                continue
            original_from_node = model[from_element]
            intermediate_count = 0
            for connector in connectors:
                for element in connector:
                    if from_element != original_from_element:
                        element.from_element = from_element

                    # Regulators go between the same two nodes
                    if isinstance(element,Regulator):
                        from_element = original_from_element+'_reg'
                    else:
                        from_element = original_from_element+'_sec_'+str(intermediate_count)
                    intermediate_count +=1
                    if intermediate_count != connector_count:
                        element.to_element = from_element
                        api_node = Node(model)
                        api_node.name = from_element
                        if original_from_node.positions is not None:
                            api_positions = []
                            for position in original_from_node.positions:
                                api_position = Position(model)
                                api_position.long = position.long
                                api_position.lat = position.lat
                                api_positions.append(api_position)
                            api_node.positions = api_positions #set the positions to be the same as in the original

                    # Lusha
                    element.name = element.name + '_' + str(intermediate_count)

            # Assumes we have had at least one connecting element added
            # Connect these all to the final to-node
            for non_connector in non_connectors:
                for element in non_connector:
                    element.connecting_element = to_element

