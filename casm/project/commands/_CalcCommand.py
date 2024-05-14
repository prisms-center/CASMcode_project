import os

# import numpy as np
# import libcasm.xtal as xtal
# import casm.project.json_io as json_io

from typing import Iterable, Optional, Union
import libcasm.configuration as casmconfig

from casm.project._Project import Project
from casm.project._ClexDescription import ClexDescription
import casm.project.text_io as text_io


class CalcCommand:
    """Methods to interact with DFT or atomistic calculators"""

    def __init__(self, proj: Project):
        self.proj = proj

    def setup_vasp(
        self,
        configurations: Union[
            Iterable[casmconfig.Configuration], casmconfig.ConfigurationSet
        ],
        clex_description: ClexDescription,
        force_write=False,
        id="",
    ):
        """Setup VASP calculations

        Parameters
        ----------
        configurations: Union[Iterable[libcasm.configuration.Configuration], \
        libcasm.configuration.ConfigurationSet]
            The candidate configurations. Must be a
            :class:`~libcasm.configuration.ConfigurationSet` or an iterable of
            :class:`~libcasm.configuration.Configuration`.

        calctype: str
            The calctype is used by CASM to find a calc.json file with VASP settings.

        id: Optional[str] = None
            An optional calculation identifier string specifying where a record
            of this set of calculations is stored. Calculation data is stored in a
            CASM project at
            `<project>/calculations/calc.<id>/`. If None, a sequential id is
            generated automatically.


        Returns
        -------
        id: str
            Calculation ID allows for finding information about the calculation that
            were setup. This can be used later with `calc_vasp` or `report_vasp` or
            with imports.
        """
        print("setup_vasp: Create VASP calculation input files")

        incar_settings_path = os.path.join(
            self.proj.dir.calc_settings_dir(clex=clex_description), "INCAR"
        )
        incar = text_io.read_required(incar_settings_path)

        # Setting up a vasp calculation for each of the libcasm.Configuration in configurations
        for config in configurations:
            # make a configname
            config_name = os.path.join(config.supercell_name, config.configuration_id)

            config_calc_dir = self.proj.dir.calctype_dir(
                configname=config_name, clex=clex_description, calc_subdir=id
            )

            # <project>/training_data/id/config_name/calctype.calctype
            config_calc_dir.mkdir(parents=True, exist_ok=True)

            # write POSCAR
            config_poscar_str = config.configuration.to_structure().to_poscar_str()
            poscar_path = os.path.join(config_calc_dir, "POSCAR")
            text_io.safe_dump(config_poscar_str, poscar_path, force=force_write)

            # copy INCAR from settings calctype dir
            incar_copy_path = os.path.join(config_calc_dir, "INCAR")
            text_io.safe_dump(incar, incar_copy_path, force=force_write)

    def calc_vasp(
        self,
        id: Optional[str] = None,
    ):
        print("calc_vasp: Run VASP calculations")
        NotImplementedError("calc_vasp method implemented yet: ", id)
        return None

    def report_vasp(
        self,
        batchfile: Optional[str] = None,
        id: Optional[str] = None,
    ):
        """Report VASP calculations, converting to libcasm.xtal.Structure

        Parameters
        ----------
        batchile: Optional[str] = None
            TODO: This needs some work... Something to indicate VASP calculations
            performed outside that should be read and converted to
            libcasm.xtal.Structure

        id: Optional[str] = None
            An optional calculation identifier string specifying where a record
            of this set of calculations is stored. Calculation data is stored in a
            CASM project at
            `<project>/calculations/calc.<id>/`. If None, a sequential id is
            generated automatically.


        Returns
        -------
        id: str
            Calculation ID allows for finding information about the calculation that
            were setup. This can be used later with `calc_vasp` or `report_vasp` or
            with imports.
        """
        print(
            "report_vasp: "
            "Parse VASP calculation output files and convert to libcasm.xtal.Structure"
        )
        NotImplementedError("report_vasp method implemented yet: ", id, batchfile)
        return None
