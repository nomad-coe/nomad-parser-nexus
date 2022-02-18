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

"""MPES reader implementation for the DataConverter."""

from typing import Tuple
import h5py
import json
from nexusparser.tools.dataconverter.readers.base.reader import BaseReader
import xarray as xr

default_units = {
    'X': 'step',
    'Y': 'step',
    't': 'step',
    'tofVoltage': 'V',
    'extractorVoltage': 'V',
    'extractorCurrent': 'A',
    'cryoTemperature': 'K',
    'sampleTemperature': 'K',
    'dldTimeBinSize': 'ns',
    'delay': 'ps',
    'timeStamp': 's',
    'energy': 'eV',
    'kx': '1/A',
    'ky': '1/A'}


def res_to_xarray(res, binNames, binAxes, metadata=None):
    """ creates a BinnedArray (xarray subclass) out of the given np.array
    Parameters:
        res: np.array
            nd array of binned data
        binNames (list): list of names of the binned axes
        binAxes (list): list of np.arrays with the values of the axes
    Returns:
        ba: BinnedArray (xarray)
            an xarray-like container with binned data, axis, and all available metadata
    """
    dims = binNames
    coords = {}
    for name, vals in zip(binNames, binAxes):
        coords[name] = vals

    xres = xr.DataArray(res, dims=dims, coords=coords)

    for name in binNames:
        try:
            xres[name].attrs['unit'] = default_units[name]
        except KeyError:
            pass

    xres.attrs['units'] = 'counts'
    xres.attrs['long_name'] = 'photoelectron counts'

    if metadata is not None:
        xres.attrs['metadata'] = metadata

    return xres


def h5_to_xarray(faddr, mode='r'):
    """ Rear xarray data from formatted hdf5 file
    Args:
        faddr (str): complete file name (including path)
        mode (str): hdf5 read/write mode
    Returns:
        xarray (xarray.DataArray): output xarra data
    """
    with h5py.File(faddr, mode) as h5File:
        # Reading data array
        try:
            data = h5File['binned']['BinnedData']
        except KeyError:
            print("Wrong Data Format, data not found")
            raise

        # Reading the axes
        axes = []
        binNames = []

        try:
            for axis in h5File['axes']:
                axes.append(h5File['axes'][axis])
                binNames.append(h5File['axes'][axis].attrs['name'])
        except KeyError:
            print("Wrong Data Format, axes not found")
            raise

        # load metadata
        if 'metadata' in h5File:
            def recursive_parse_metadata(node):
                if isinstance(node, h5py.Group):
                    d = {}
                    for k, v in node.items():
                        d[k] = recursive_parse_metadata(v)

                else:
                    d = node[...]
                    try:
                        d = d.item()
                        if isinstance(d, (bytes, bytearray)):
                            d = d.decode()
                    except ValueError:
                        pass

                return d

            metadata = recursive_parse_metadata(h5File['metadata'])

        xarray = res_to_xarray(data, binNames, axes, metadata)
        return xarray


def iterate_dictionary(dic, key_string):
    keys = key_string.split('/', 1)
    if keys[0] in dic:
        if len(keys) == 1:
            return dic[keys[0]]
        else:
            return iterate_dictionary(dic[keys[0]], keys[1])
    else:
        raise KeyError


class MPESReader(BaseReader):

    # pylint: disable=too-few-public-methods

    # Whitelist for the NXDLs that the reader supports and can process
    supported_nxdls = ["NXmpes"]

    def read(self, template: dict = None, file_paths: Tuple[str] = None) -> dict:
        """Reads data from given file and returns a filled template dictionary"""

        if not file_paths:
            raise Exception("No input files were given to MPES Reader.")

        for file_path in file_paths:

            file_extension = file_path[file_path.rindex("."):]

            if file_extension == '.h5':
                x_array_loaded = h5_to_xarray(file_path)

            elif file_extension == '.json':
                with open(file_path, 'r') as f:
                    config_file_dict = json.load(f)

        for k, v in config_file_dict.items():

            if isinstance(v, str) and ':' in v:
                precursor = v.split(':')[0]
                value = v[v.index(':') + 1:]

                # Filling in the data and axes along with units from xarray
                if precursor == '@data':
                    try:
                        template[k] = eval("x_array_loaded." + value)
                        if k.split('/')[-1] == '@axes':
                            template[k] = list(template[k])

                    except NameError:
                        print(f"Incorrect naming syntax or the xarray doesn't contain entry corresponding to the path {k}")
                    except KeyError:
                        print(f"The xarray doesn't contain entry corresponding to the path {k}")

                # Filling in the metadata from xarray
                elif precursor == '@attrs':

                    try:  # Tries to fill the metadata
                        template[k] = iterate_dictionary(x_array_loaded.attrs, value)

                    except KeyError:
                        print(f"The xarray doesn't contain entry corresponding to the path {k}")

            else:
                # Fills in the fixed metadata
                template[k] = v

        return template


READER = MPESReader