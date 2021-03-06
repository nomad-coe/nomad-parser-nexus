"""parser doc

"""
#
# Copyright The NOMAD Authors.
#
# This file is part of NOMAD. See https://nomad-lab.eu for further info.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from typing import Iterable, Union
import os
import pathlib
import numpy as np
from nomad.datamodel import EntryArchive
from nomad.parsing import Parser
# from . import metainfo  # pylint: disable=unused-import
from nexusparser.tools import nexus as read_nexus
from nexusparser.metainfo import nexus


def get_to_new_subsection(hdf_name, nxdef, nxdl_node, act_section):
    """hdf_name         name of the hdf group/field/attribute (None for definition)
    nxdef           application definition
    nxdl_node        node in the nxdl.xml
    act_class       actual class
    act_section     actual section in which the new entry needs to be picked up from
                    Note that if the new element did not exists, it is created now
    return          (new_class, new_section)
    TODO:   try to find also in the base section???

"""
    if hdf_name is None:
        nomad_def_name = 'nx_application_' + nxdef[2:]
        # nomad_class_name = nxdef
    elif nxdl_node.tag.endswith('field'):
        nxdl_f_a_name = nxdl_node.attrib['name'] if 'name' in nxdl_node.attrib else hdf_name
        nomad_def_name = 'nx_field_' + nxdl_f_a_name
        # nomad_class_name = self.get_nomad_classname(nxdl_f_a_name, None, "Field")
    elif nxdl_node.tag.endswith('group'):
        nxdl_g_name = nxdl_node.attrib['name'] \
            if 'name' in nxdl_node.attrib else nxdl_node.attrib['type'][2:].upper()
        nomad_def_name = 'nx_group_' + nxdl_g_name
        # nomad_class_name = self.get_nomad_classname(read_nexus.get_node_name(nxdl_node),
        #                                             nxdl_node.attrib['type'], "Group")
    else:
        nxdl_f_a_name = nxdl_node.attrib['name'] if 'name' in nxdl_node.attrib else hdf_name
        nomad_def_name = 'nx_attribute_' + nxdl_f_a_name
        # nomad_class_name = self.get_nomad_classname(nxdl_f_a_name, None, "Attribute")

    new_def = act_section.m_def.all_sub_sections[nomad_def_name]
    new_class = new_def.section_def.section_cls
    new_section = None
    for section in act_section.m_get_sub_sections(new_def):
        if hdf_name is None or (getattr(section, "nx_name") and section.nx_name == hdf_name):
            new_section = section
            break
    if new_section is None:
        act_section.m_create(new_class)
        new_section = act_section.m_get_sub_section(new_def, -1)
        if hdf_name is not None:
            new_section.nx_name = hdf_name
    return (new_class, new_section)


def get_value(hdf_node):
    """Get value from hdl5 node

"""
    hdf_value = hdf_node[...]
    if str(hdf_value.dtype) == 'bool':
        val = bool(hdf_value)
    elif hdf_value.dtype.kind in 'iufc':
        val = hdf_value
    else:
        try:
            val = str(hdf_value.astype(str))
        except UnicodeDecodeError:
            val = str(hdf_node[()].decode())
    return val


def helper_nexus_populate(nxdl_attribute, act_section, val, logger):
    """Handle info of units attribute, raise error if default or something else is found

"""
    try:
        if nxdl_attribute == "units":
            act_section.nx_unit = val[0]
        elif nxdl_attribute == "default":
            Exception("Quantity 'default' is not yet added by default to groups in Nomad schema")
    except Exception as exc:  # pylint: disable=broad-except
        logger.debug("Problem with storage!!!\n" + str(exc))


def nexus_populate_helper(params):
    """helper for nexus_populate"""
    (path_level, nxdl_path, act_section, logstr, val, loglev, nxdef, hdf_node) = params
    if path_level < len(nxdl_path):
        nxdl_attribute = nxdl_path[path_level]
        if isinstance(nxdl_attribute, str):
            # conventional attribute not in schema. Only necessary,
            # if schema is not populated according
            # helper_nexus_populate(nxdl_attribute, act_section, val, logger)
            try:
                if nxdl_attribute == "units":
                    act_section.nx_unit = val[0]
                elif nxdl_attribute == "default":
                    Exception(
                        "'default' is not yet added by default to groups in Nomad schema")
            except Exception as exc:  # pylint: disable=broad-except
                logstr += ("Problem with storage!!!\n" + str(exc)) + '\n'
                loglev = 'error'
        else:
            # attribute in schema
            act_section = \
                get_to_new_subsection(nxdl_attribute.attrib['name'], nxdef,
                                      nxdl_attribute, act_section)[1]
            try:
                act_section.nx_value = val[0]
            except (AttributeError, TypeError, ValueError) as exc:
                logstr += ("Problem with storage!!!\n" + str(exc)) + '\n'
                loglev = 'error'
    else:
        try:
            data_field = get_value(hdf_node)
            if hdf_node[...].dtype.kind in 'iufc' and \
                    isinstance(data_field, np.ndarray) and \
                    data_field.size > 1:
                data_field = np.array([
                    np.mean(data_field),
                    np.var(data_field),
                    np.min(data_field),
                    np.max(data_field)
                ])
            act_section.nx_value = data_field
        except (TypeError, ValueError) as exc:
            logstr += ("Problem with storage!!!\n" + str(exc)) + '\n'
            loglev = 'error'
    return [logstr, loglev]


def add_log(params, logstr):
    """adds log entry for the given node"""
    if params["nxdef"] is not None:
        logstr += params["nxdef"]
    else:
        logstr += '???'
    logstr += ':'
    first = True
    for p_node in params["nxdl_path"]:
        if first:
            first = False
        else:
            logstr += '.'
        if isinstance(p_node, str):
            logstr += p_node
        else:
            read_nexus.get_node_name(p_node)
    logstr += ' - ' + params["val"][0]
    if len(params["val"]) > 1:
        logstr += '...'
    logstr += '\n'
    return logstr


class NexusParser(Parser):
    """NesusParser doc

"""
    def __init__(self):
        super().__init__()
        self.name = "parsers/nexus"
        self.archive = None
        self.nxroot = None
        self.domain = 'ems'

    def is_mainfile(  # pylint: disable=too-many-arguments
            self, filename: str, mime: str, buffer: bytes, decoded_buffer: str,
            compression: str = None) -> Union[bool, Iterable[str]]:
        accepted_extensions = (".nxs", ".yaml", ".yml")
        extension = pathlib.Path(filename).suffix
        if extension in accepted_extensions:
            if buffer[0:8] == b'\x89HDF\r\n\x1a\n':
                return True
            if buffer[0:30] == b"# NexusParser Parameter File -":
                return True
        return False

#     def get_nomad_classname(self, xml_name, xml_type, suffix):
#         """Get nomad classname from xml file

# """
#         if suffix == 'Attribute' or suffix == 'Field' or xml_type[2:].upper() != xml_name:
#             name = xml_name + suffix
#         else:
#             name = xml_type + suffix
#         return name

    def nexus_populate(self, params, attr=None):
        """Walks through hdf_namelist and generate nxdl nodes
        (hdf_info, nxdef, nxdl_path, val, logger) = params"""
        hdf_path = params["hdf_info"]['hdf_path']
        hdf_node = params["hdf_info"]['hdf_node']
        logstr = hdf_path + (("@" + attr) if attr else '') + '\n'
        loglev = 'info'
        if params["nxdl_path"] is not None:
            logstr = add_log(params, logstr)
            act_section = self.nxroot
            hdf_namelist = hdf_path.split('/')[1:]
            act_section = get_to_new_subsection(None, params["nxdef"], None, act_section)[1]
            path_level = 1
            for hdf_name in hdf_namelist:
                if path_level < len(params["nxdl_path"]):
                    nxdl_node = params["nxdl_path"][path_level]
                else:
                    nxdl_node = hdf_name
                act_section = get_to_new_subsection(hdf_name, params["nxdef"],
                                                    nxdl_node, act_section)[1]
                path_level += 1
            helper_params = (path_level, params["nxdl_path"], act_section, logstr, params["val"],
                             loglev, params["nxdef"], hdf_node)
            (logstr, loglev) = nexus_populate_helper(helper_params)
        else:
            logstr += ('NOT IN SCHEMA - skipped') + '\n'
            loglev = 'warning'
        if loglev == 'info':
            params["logger"].info('Parsing', nexusparser=logstr)
        elif loglev == 'warning':
            params["logger"].warning('Parsing', nexusparser=logstr)
        elif loglev == 'error':
            params["logger"].error('Parsing', nexusparser=logstr)
        else:
            params["logger"].critical('Parsing', nexusparser=logstr + 'NOT HANDLED\n')

    def parse(self, mainfile: str, archive: EntryArchive, logger=None, child_archives=None):
        self.archive = archive
        self.archive.m_create(nexus.Nexus)  # type: ignore[attr-defined] # pylint: disable=no-member
        self.nxroot = self.archive.nexus

        extension = pathlib.Path(mainfile).suffix
        if extension in (".yaml", ".yml"):
            base_dir = os.path.dirname(mainfile)
            from nexusparser.tools.dataconverter.convert import convert, parse_params_file
            with open(mainfile) as file:
                conv_params = parse_params_file(file)

                def check_path(path: str):
                    """Return true if path supplied by the user is not absolute or has a ../"""
                    if os.path.isabs(path) or ".." in path:
                        raise Exception("The user provided an invalid path in the parameter YAML.")
                    return path

                if isinstance(conv_params["input_file"], list):
                    conv_params["input_file"] = [f"{base_dir}{os.sep}{check_path(file)}"
                                                 for file in conv_params["input_file"]]
                else:
                    conv_params["input_file"] = (f"{base_dir}{os.sep}"
                                                 f"{check_path(conv_params['input_file'])}")
                conv_params["output"] = f"{base_dir}{os.sep}{check_path(conv_params['output'])}"
                convert(**conv_params)
                mainfile = conv_params["output"]

        nexus_helper = read_nexus.HandleNexus(logger, [mainfile])
        nexus_helper.process_nexus_master_file(self.nexus_populate)

        appdef = ""
        for var in dir(archive.nexus):
            if var.startswith("nx_application") and getattr(archive.nexus, var) is not None:
                appdef = var[len("nx_application_"):]

        if archive.metadata is not None:
            archive.metadata.entry_type = f"NX{appdef}"
