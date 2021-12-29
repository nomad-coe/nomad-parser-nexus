#!/usr/bin/env python3
"""This tool accomplishes some tests for the yaml2nxdl parser

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

import os
import sys
from datetime import datetime
from pathlib import Path
import pytest
from click.testing import CliRunner
import nexusparser.tools.yaml2nxdl.yaml2nxdl as yml2nxdl

sys.path.insert(0, '../nexusparser/tools')
sys.path.insert(0, '../nexusparser/tools/yaml2nxdl')

LOCALDIR = os.path.abspath(os.path.dirname(__file__))


def delete_duplicates(list_of_matching_string):
    """Delete duplicate from lists

    """
    return list(dict.fromkeys(list_of_matching_string))


def find_matches(xml_file, desired_matches):
    """Read xml file and find desired matches.
Return a list of two lists in the form:
[[matching_line],[matching_line_index]]

    """
    with open(xml_file, 'r') as file:
        xml_reference = file.readlines()
    lines = []
    lines_index = []
    found_matches = []
    for i, line in enumerate(xml_reference):
        for desired_match in desired_matches:
            if str(desired_match) in str(line):
                lines.append(line)
                lines_index.append(i)
                found_matches.append(desired_match)
    # ascertain that all the desired matches were found in file
    found_matches_clean = delete_duplicates(found_matches)
    assert len(found_matches_clean) == len(desired_matches), 'some desired_matches were \
not found in file'
    return [lines, lines_index]


def compare_matches(ref_xml_file, test_yml_file, test_xml_file, desired_matches):
    """Check if a new xml file is generated
and if test xml file is equal to reference xml file

    """
    # Reference file is read
    ref_matches = find_matches(ref_xml_file, desired_matches)
    # Test file is generated
    result = CliRunner().invoke(yml2nxdl.yaml2nxdl, ['--input-file', test_yml_file])
    assert result.exit_code == 0
    path = Path(test_xml_file)
    timestamp = datetime.fromtimestamp(path.stat().st_mtime).strftime("%d/%m/%Y %H:%M")
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    assert timestamp == now, 'xml file not generated'
    # Test file is read
    test_matches = find_matches(test_xml_file, desired_matches)
    assert test_matches == ref_matches


@pytest.fixture
def test_links():
    """First test: check the correct parsing of links

    """
    ref_xml_link_file = os.path.join(
        LOCALDIR, 'data/yaml2nxdl_test_data/Ref_NXtest_links.nxdl.xml')
    test_yml_link_file = os.path.join(
        LOCALDIR, 'data/yaml2nxdl_test_data/NXtest_links.yml')
    test_xml_link_file = os.path.join(
        LOCALDIR, 'data/yaml2nxdl_test_data/NXtest_links.nxdl.xml')
    desired_matches = ['<link', '/>']
    compare_matches(
        ref_xml_link_file,
        test_yml_link_file,
        test_xml_link_file,
        desired_matches)


@pytest.fixture
def test_symbols():
    """Second test: check the correct parsing of symbols

    """
    ref_xml_symbol_file = os.path.join(
        LOCALDIR, 'data/yaml2nxdl_test_data/Ref_NXnested_symbols.nxdl.xml')
    test_yml_symbol_file = os.path.join(
        LOCALDIR, 'data/yaml2nxdl_test_data/NXnested_symbols.yml')
    test_xml_symbol_file = os.path.join(
        LOCALDIR, 'data/yaml2nxdl_test_data/NXnested_symbols.nxdl.xml')
    desired_matches = ['<symbols>', '</symbols>', '<symbols']
    compare_matches(
        ref_xml_symbol_file,
        test_yml_symbol_file,
        test_xml_symbol_file,
        desired_matches)


@pytest.fixture
def test_attributes():
    """Third test: check the correct handling of empty attributes
    or attributes fields, e.g. doc

    """
    ref_xml_attribute_file = os.path.join(
        LOCALDIR, 'data/yaml2nxdl_test_data/Ref_NXattributes.nxdl.xml')
    test_yml_attribute_file = os.path.join(
        LOCALDIR, 'data/yaml2nxdl_test_data/NXattributes.yml')
    test_xml_attribute_file = os.path.join(
        LOCALDIR, 'data/yaml2nxdl_test_data/NXattributes.nxdl.xml')
    desired_matches = ['<attribute', '</attribute>', '<doc>', '</doc>']
    compare_matches(
        ref_xml_attribute_file,
        test_yml_attribute_file,
        test_xml_attribute_file,
        desired_matches)


if __name__ == '__main__':
    test_links()
    test_symbols()
    test_attributes()
