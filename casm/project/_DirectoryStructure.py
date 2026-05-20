import pathlib
import warnings
from typing import Optional, Union

from ._ClexDescription import ClexDescription


class DirectoryStructureV1:
    """Standard CASM v1 project directory structure

    This class helps constructs the standard paths specified in the CASM
    `Project directory structure reference <https://prisms-center.github.io/CASMcode_docs/formats/project_directory_structure/>`_.

    """

    def __init__(self, path: Union[str, pathlib.Path]):
        """
        .. rubric:: Constructor

        Parameters
        ----------
        path: Union[str, pathlib.Path]
            Path to CASM project directory.

        """
        self.path = pathlib.Path(path)
        """str: Path to CASM project."""

        if self.path is None:
            raise Exception(
                "Error in casm.project.DirectoryStructure: "
                f"No CASM project found containing {path}"
            )
        self.__casm_dir = ".casm"
        self.__casmdb_dir = "jsonDB"
        self.__bset_dir = "basis_sets"
        self.__calc_dir = "training_data"
        self.__set_dir = "settings"
        self.__sym_dir = "symmetry"
        self.__clex_dir = "cluster_expansions"

    # ** Query filesystem **

    def all_bset(self):
        """Check filesystem directory structure and return list of all basis set
        names"""
        return self.__all_settings("bset", self.path / self.__bset_dir)

    def all_calctype(self):
        """Check filesystem directory structure and return list of all calctype names"""
        return self.__all_settings(
            "calctype", self.path / self.__calc_dir / self.__set_dir
        )

    def all_ref(self, calctype: str):
        """Check filesystem directory structure and return list of all ref names for
        a given calctype"""
        return self.__all_settings("ref", self.calc_settings_dir(calctype))

    def all_clex_name(self):
        """Check filesystem directory structure and return list of all cluster
        expansion names"""
        return self.__all_settings("clex", self.path / self.__clex_dir)

    def all_eci(self, property: str, calctype: str, ref: str, bset: str):
        """Check filesystem directory structure and return list of all eci names"""
        return self.__all_settings(
            "eci",
            self.path
            / self.__clex_dir
            / self.__clex_name(property)
            / self.__calctype(calctype)
            / self.__ref(ref)
            / self.__bset(bset),
        )

    # ** File and Directory paths **

    # -- Project directory --------

    def root_dir(self):
        """Return casm project directory path"""
        return self.path

    def prim(self):
        """Return prim.json path"""
        return self.casm_dir() / "prim.json"

    # -- Hidden .casm directory --------

    def casm_dir(self):
        """Return hidden .casm dir path"""
        return self.path / self.__casm_dir

    def casmdb_dir(self):
        """Return .casm/jsonDB path"""
        return self.casm_dir() / self.__casmdb_dir

    def project_settings(self):
        """Return project_settings.json path"""
        return self.casm_dir() / "project_settings.json"

    def scel_list(self, scelname: str):
        """Return master scel_list.json path"""
        return self.casmdb_dir() / "scel_list.json"

    def config_list(self, name: Optional[str] = None):
        """Return configuration set or list file path

        Parameters
        ----------
        name: Optional[str] = None
            Optional name for configuration list or set. Default (None) is
            the master configuration set.

        """
        if name is None:
            filename = "config_list.json"
        else:
            filename = f"config_list.{name}.json"
        return self.casm_dbdir() / filename

    def config_props(
        self,
        calctype: str,
        name: Optional[str] = None,
    ):
        """Return configuration properties file path for given calculation type"""
        if name is None:
            filename = "config_props.json"
        else:
            filename = f"config_props.{name}.json"
        return self.casm_dbdir() / self.__calctype(calctype) / filename

    def master_selection(self, otype):
        """Return location of MASTER selection file

        Parameters
        ----------
        otype: str
            One of "config", "scel", "event", or "path"
        """
        querydir = self.casm_dir() / "query"
        if otype == "config":
            return querydir / "Configuration" / "master_selection"
        elif otype == "scel":
            return querydir / "Supercell" / "master_selection"
        else:
            raise Exception("Unsupported type: " + str(otype))

    # -- Symmetry --------

    def symmetry_dir(self):
        """Return symmetry directory path"""
        return self.path / self.__sym_dir

    def lattice_point_group(self):
        """Return lattice_point_group.json path"""
        return self.symmetry_dir() / "lattice_point_group.json"

    def factor_group(self):
        """Return factor_group.json path"""
        return self.symmetry_dir() / "factor_group.json"

    def crystal_point_group(self):
        """Return crystal_point_group.json path"""
        return self.symmetry_dir() / "crystal_point_group.json"

    # -- Basis sets --------

    def _get_bset(
        self,
        clex: Optional[ClexDescription] = None,
        bset: Optional[str] = None,
    ):
        if bset is None:
            if clex is None:
                raise Exception("One of clex, bset is required")
            bset = clex.bset
        return bset

    def bset_dir(
        self,
        clex: Optional[ClexDescription] = None,
        bset: Optional[str] = None,
    ):
        """Return path to directory contain basis set info"""
        bset = self._get_bset(clex=clex, bset=bset)
        return self.path / self.__bset_dir / self.__bset(bset=bset)

    def bspecs(
        self,
        clex: Optional[ClexDescription] = None,
        bset: Optional[str] = None,
    ):
        """Return basis function specs (bspecs.json) file path"""
        return self.bset_dir(clex=clex, bset=bset) / "bspecs.json"

    def clust(
        self,
        clex: Optional[ClexDescription] = None,
        bset: Optional[str] = None,
    ):
        """Returns path to the clust.json file"""
        return self.bset_dir(clex=clex, bset=bset) / "clust.json"

    def basis(
        self,
        clex: Optional[ClexDescription] = None,
        bset: Optional[str] = None,
    ):
        """Returns path to the basis.json file"""
        return self.bset_dir(clex=clex, bset=bset) / "basis.json"

    def clexulator_dir(
        self,
        clex: Optional[ClexDescription] = None,
        bset: Optional[str] = None,
    ):
        """Returns path to directory containing global clexulator"""
        bset = self._get_bset(clex=clex, bset=bset)
        return self.bset_dir(bset=bset)

    def clexulator_src(
        self,
        projectname: str,
        clex: Optional[ClexDescription] = None,
        bset: Optional[str] = None,
        i_equiv: Optional[int] = None,
    ):
        """Returns path to global clexulator source file"""
        bset = self._get_bset(clex=clex, bset=bset)
        if i_equiv is None:
            return self.bset_dir(bset=bset) / (projectname + f"_Clexulator_{bset}.cc")
        else:
            return (
                self.bset_dir(bset=bset)
                / str(i_equiv)
                / (projectname + f"_Clexulator_{bset}.cc")
            )

    def clexulator_o(
        self,
        projectname: str,
        clex: Optional[ClexDescription] = None,
        bset: Optional[str] = None,
        i_equiv: Optional[int] = None,
    ):
        """Returns path to global clexulator.o file"""
        bset = self._get_bset(clex=clex, bset=bset)
        if i_equiv is None:
            return self.bset_dir(bset=bset) / (projectname + f"_Clexulator_{bset}.o")
        else:
            return (
                self.bset_dir(bset=bset)
                / str(i_equiv)
                / (projectname + f"_Clexulator_{bset}.o")
            )

    def clexulator_so(
        self,
        projectname: str,
        clex: Optional[ClexDescription] = None,
        bset: Optional[str] = None,
        i_equiv: Optional[int] = None,
    ):
        """Returns path to global clexulator so file"""
        bset = self._get_bset(clex=clex, bset=bset)
        if i_equiv is None:
            return self.bset_dir(bset=bset) / (projectname + f"_Clexulator_{bset}.so")
        else:
            return (
                self.bset_dir(bset=bset)
                / str(i_equiv)
                / (projectname + f"_Clexulator_{bset}.so")
            )

    # -- Calculations and reference --------

    def supercell_dir(self, scelname: str, calc_subdir: str = ""):
        """Return supercell directory path (scelname has format SCELV_A_B_C_D_E_F)"""
        return self.path / self.__calc_dir / calc_subdir / scelname

    def configuration_dir(self, configname: str, calc_subdir: str = ""):
        """Return configuration directory path (configname has format
        SCELV_A_B_C_D_E_F/I)"""
        return self.path / self.__calc_dir / calc_subdir / configname

    def POS(self, configname: str, calc_subdir: str = ""):
        """Return path to POS file"""
        return self.configuration_dir(configname, calc_subdir) / "POS"

    def config_json(self, configname: str, calc_subdir: str = ""):
        """Return path to structure.json file"""
        return self.configuration_dir(configname, calc_subdir) / "config.json"

    def structure_json(self, configname: str, calc_subdir: str = ""):
        """Return path to structure.json file"""
        return self.configuration_dir(configname, calc_subdir) / "structure.json"

    def calctype_dir(
        self, configname: str, clex: ClexDescription, calc_subdir: str = ""
    ):
        R"""Return calctype directory path (e.g.
        training_data/$(calc_subdir)/SCEL...../0/calctype.default"""
        return self.configuration_dir(configname, calc_subdir) / self.__calctype(
            clex.calctype
        )

    # -- calc_settings_dir --------

    def calc_settings_dir(self, clex: ClexDescription):
        """Return calculation settings directory path, for global settings from clex"""
        return (
            self.path
            / self.__calc_dir
            / self.__set_dir
            / self.__calctype(clex.calctype)
        )

    def calctype_settings_dir(self, calctype: str):
        """Return calculation settings directory path, for global settings from
        calctype"""
        return self.path / self.__calc_dir / self.__set_dir / self.__calctype(calctype)

    def supercell_calc_settings_dir(
        self,
        scelname: str,
        clex: ClexDescription,
        calc_subdir: str = "",
    ):
        """Return calculation settings directory path, for supercell specific
        settings"""
        return (
            self.supercell_dir(scelname, calc_subdir)
            / self.__set_dir
            / self.__calctype(clex.calctype)
        )

    def configuration_calc_settings_dir(
        self,
        configname: str,
        clex: ClexDescription,
        calc_subdir: str = "",
    ):
        """Return calculation settings directory path, for configuration specific
        settings"""
        return (
            self.configuration_dir(configname, calc_subdir)
            / self.__set_dir
            / self.__calctype(clex.calctype)
        )

    def calculated_properties(
        self,
        configname: str,
        clex: ClexDescription,
        calc_subdir: str = "",
    ):
        """Return calculated properties file path"""
        return (
            self.configuration_dir(configname, calc_subdir)
            / self.__calctype(clex.calctype)
            / "properties.calc.json"
        )

    def ref_dir(self, clex: ClexDescription):
        """Return calculation reference settings directory path, for global settings"""
        return self.calc_settings_dir(clex.calctype) / self.__ref(clex.ref)

    # -- Composition axes --------

    def composition_axes(self):
        """Return composition axes file path (deprecated)"""
        return self.casm_dir() / "composition_axes.json"

    def chemical_reference(self, clex: ClexDescription):
        """Return chemical reference file path"""
        return self.ref_dir(clex) / "chemical_reference.json"

    # -- Cluster expansions --------

    def property_dir(self, clex: ClexDescription):
        """Returns path to eci directory"""
        return self.path / self.__clex_dir / self.__clex_name(clex.property)

    def eci_dir(self, clex: ClexDescription):
        """
        Returns path to eci directory

        Parameters
        ----------
        clex: a casm.project.ClexDescription instance
            Specifies the cluster expansion to get the eci directory for

        Returns
        -------
        p: str
            Path to the eci directory
        """
        return (
            self.property_dir(clex)
            / self.__calctype(clex.calctype)
            / self.__ref(clex.ref)
            / self.__bset(clex.bset)
            / self.__eci(clex.eci)
        )

    def eci(self, clex: ClexDescription):
        """
        Returns path to eci.json

        Parameters
        ----------
        clex: a casm.project.ClexDescription instance
            Specifies the cluster expansion to get the eci.json for

        Returns
        -------
        p: str
            Path to the eci directory
        """
        return self.eci_dir(clex) / "eci.json"

    # private:

    def __bset(self, bset: str):
        return "bset." + bset

    def __calctype(self, calctype: str):
        return "calctype." + calctype

    def __ref(self, ref: str):
        return "ref." + ref

    def __clex_name(self, clex_name: str):
        return "clex." + clex_name

    def __eci(self, eci: str):
        return "eci." + eci

    def __all_settings(self, pattern: str, location: pathlib.Path):
        """
        Find all directories at 'location' that match 'pattern.something'
        and return a std::vector of the 'something'
        """

        all = []
        pattern += "."

        # get all
        if not location.exists():
            return all

        for child in location.iterdir():
            if child.is_dir() and child.name[: len(pattern)] == pattern:
                all.append(child.name[len(pattern) :])
        return sorted(all)


class DirectoryStructure:
    """Standard CASM v2 project directory structure

    This class helps constructs the standard paths specified in the CASM
    `Project directory structure reference <https://prisms-center.github.io/CASMcode_docs/formats/project_directory_structure/>`_.

    """

    def __init__(self, path: Union[str, pathlib.Path]):
        """
        .. rubric:: Constructor

        Parameters
        ----------
        path: Union[str, pathlib.Path]
            Path to CASM project directory.

        """
        self.path = pathlib.Path(path)
        """str: Path to CASM project."""

        if self.path is None:
            raise Exception(
                "Error in casm.project.DirectoryStructure: "
                f"No CASM project found containing {path}"
            )
        self.__casm_dir = ".casm"
        self.__enum_dir = "enumerations"
        self.__bset_dir = "basis_sets"
        self.__calculation_settings_dir = "calculation_settings"
        self.__import_dir = "imports"
        self.__fit_dir = "fits"
        self.__sym_dir = "symmetry"
        self.__system_dir = "systems"
        self.__plot_settings_dir = "plot_settings"

    # ** Query filesystem **

    def all_enum(self):
        """Check filesystem directory structure and return list of all enumeration
        names"""
        return self.__all_settings("enum", self.path / self.__enum_dir)

    def all_bset(self):
        """Check filesystem directory structure and return list of all basis set
        names"""
        return self.__all_settings("bset", self.path / self.__bset_dir)

    def all_calctype(self):
        """Check filesystem and return list of all calctype names (v2)"""
        return self.__all_settings(
            "calctype", self.path / self.__calculation_settings_dir
        )

    def all_calctype_v2(self):
        """Check filesystem directory structure and return list of all calctype names
        (deprecated)

        .. deprecated:: 2.0a2

            Use :func:`~casm.project.DirectoryStructure.all_calctype` instead.
            Will be removed in 2.0.0.

        """
        warnings.warn(
            "The method 'casm.project.DirectoryStructure.all_calctype_v2' is "
            "deprecated and will be removed in a future version. Use "
            "'casm.project.DirectoryStructure.all_calctype' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.__all_settings(
            "calctype", self.path / self.__calculation_settings_dir
        )

    # TODO: update this
    # def all_ref(self, calctype: str):
    #     """Check filesystem directory structure and return list of all ref names for
    #     a given calctype"""
    #     return self.__all_settings("ref", self.calc_settings_dir(calctype))

    def all_import(self):
        return self.__all_settings("import", self.path / self.__import_dir)

    def all_fit(self):
        return self.__all_settings("fit", self.path / self.__fit_dir)

    def all_system(self):
        return self.__all_settings("system", self.path / self.__system_dir)

    def all_plottype(self):
        return self.__all_settings("plottype", self.path / self.__plot_settings_dir)

    # ** File and Directory paths **

    # -- Project directory --------

    def root_dir(self):
        """Return casm project directory path"""
        return self.path

    def prim(self):
        """Return prim.json path"""
        return self.casm_dir() / "prim.json"

    # -- Hidden .casm directory --------

    def casm_dir(self):
        """Return hidden .casm dir path"""
        return self.path / self.__casm_dir

    def project_settings(self):
        """Return project_settings.json path"""
        return self.casm_dir() / "project_settings.json"

    # -- Symmetry --------

    def symmetry_dir(self):
        """Return symmetry directory path"""
        return self.path / self.__sym_dir

    def lattice_point_group(self):
        """Return lattice_point_group.json path"""
        return self.symmetry_dir() / "lattice_point_group.json"

    def factor_group(self):
        """Return factor_group.json path"""
        return self.symmetry_dir() / "factor_group.json"

    def crystal_point_group(self):
        """Return crystal_point_group.json path"""
        return self.symmetry_dir() / "crystal_point_group.json"

    # -- Basis sets --------

    def _get_bset(
        self,
        clex: Optional[ClexDescription] = None,
        bset: Optional[str] = None,
    ):
        if bset is None:
            if clex is None:
                raise Exception("One of clex, bset is required")
            bset = clex.bset
        return bset

    def bset_dir(
        self,
        clex: Optional[ClexDescription] = None,
        bset: Optional[str] = None,
    ):
        """Return path to directory contain basis set info"""
        bset = self._get_bset(clex=clex, bset=bset)
        return self.path / self.__bset_dir / self.__bset(bset=bset)

    def bspecs(
        self,
        clex: Optional[ClexDescription] = None,
        bset: Optional[str] = None,
    ):
        """Return basis function specs (bspecs.json) file path"""
        return self.bset_dir(clex=clex, bset=bset) / "bspecs.json"

    def basis(
        self,
        clex: Optional[ClexDescription] = None,
        bset: Optional[str] = None,
    ):
        """Returns path to the basis.json file"""
        return self.bset_dir(clex=clex, bset=bset) / "basis.json"

    def clexulator_dir(
        self,
        clex: Optional[ClexDescription] = None,
        bset: Optional[str] = None,
    ):
        """Returns path to directory containing global clexulator"""
        bset = self._get_bset(clex=clex, bset=bset)
        return self.bset_dir(bset=bset)

    def clexulator_src(
        self,
        projectname: str,
        clex: Optional[ClexDescription] = None,
        bset: Optional[str] = None,
        i_equiv: Optional[int] = None,
    ):
        """Returns path to global clexulator source file"""
        bset = self._get_bset(clex=clex, bset=bset)
        if i_equiv is None:
            return self.bset_dir(bset=bset) / (projectname + f"_Clexulator_{bset}.cc")
        else:
            return (
                self.bset_dir(bset=bset)
                / str(i_equiv)
                / (projectname + f"_Clexulator_{bset}.cc")
            )

    def clexulator_o(
        self,
        projectname: str,
        clex: Optional[ClexDescription] = None,
        bset: Optional[str] = None,
        i_equiv: Optional[int] = None,
    ):
        """Returns path to global clexulator.o file"""
        bset = self._get_bset(clex=clex, bset=bset)
        if i_equiv is None:
            return self.bset_dir(bset=bset) / (projectname + f"_Clexulator_{bset}.o")
        else:
            return (
                self.bset_dir(bset=bset)
                / str(i_equiv)
                / (projectname + f"_Clexulator_{bset}.o")
            )

    def clexulator_so(
        self,
        projectname: str,
        clex: Optional[ClexDescription] = None,
        bset: Optional[str] = None,
        i_equiv: Optional[int] = None,
    ):
        """Returns path to global clexulator so file"""
        bset = self._get_bset(clex=clex, bset=bset)
        if i_equiv is None:
            return self.bset_dir(bset=bset) / (projectname + f"_Clexulator_{bset}.so")
        else:
            return (
                self.bset_dir(bset=bset)
                / str(i_equiv)
                / (projectname + f"_Clexulator_{bset}.so")
            )

    def equivalents_info(
        self,
        clex: Optional[ClexDescription] = None,
        bset: Optional[str] = None,
    ):
        """Return cluster functions (cluster_functions.json.gz) file path"""
        return self.bset_dir(clex=clex, bset=bset) / "equivalents_info.json"

    def cluster_functions(
        self,
        clex: Optional[ClexDescription] = None,
        bset: Optional[str] = None,
    ):
        """Return cluster functions (cluster_functions.json.gz) file path"""
        return self.bset_dir(clex=clex, bset=bset) / "cluster_functions.json.gz"

    def clexulator_variables(
        self,
        clex: Optional[ClexDescription] = None,
        bset: Optional[str] = None,
    ):
        """Return clexulator variables (variables.json.gz) file path"""
        return self.bset_dir(clex=clex, bset=bset) / "variables.json.gz"

    # -- calc_settings_dir - v2 --------

    def _get_calctype(
        self,
        clex: Optional[ClexDescription] = None,
        calctype: Optional[str] = None,
    ):
        if calctype is None:
            if clex is None:
                raise Exception("One of clex, calctype is required")
            calctype = clex.calctype
        return calctype

    def calctype_settings_dir(
        self,
        clex: Optional[ClexDescription] = None,
        calctype: Optional[str] = None,
    ):
        """Return global calculation settings directory path (v2)"""
        return self.path / self.__calculation_settings_dir / self.__calctype(calctype)

    def calctype_settings_dir_v2(
        self,
        clex: Optional[ClexDescription] = None,
        calctype: Optional[str] = None,
    ):
        """Return global calculation settings directory path (deprecated)

        .. deprecated:: 2.0a2

            Use :func:`~casm.project.DirectoryStructure.calctype_settings_dir` instead.
            Will be removed in 2.0.0.


        """
        warnings.warn(
            "The method 'casm.project.DirectoryStructure.calctype_settings_dir_v2' is "
            "deprecated and will be removed in a future version. Use "
            "'casm.project.DirectoryStructure.calctype_settings_dir' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        calctype = self._get_calctype(clex=clex, calctype=calctype)
        return self.path / self.__calculation_settings_dir / self.__calctype(calctype)

    # -- chemical reference - v2 -------

    def _get_ref(
        self,
        clex: Optional[ClexDescription] = None,
        ref: Optional[str] = None,
    ):
        if ref is None:
            if clex is None:
                raise Exception("One of clex, ref is required")
            ref = clex.ref
        return ref

    def ref_dir(self, clex: ClexDescription, calctype: str, ref: str):
        """Return calculation reference settings directory path, for global settings"""
        ref = self._get_ref(clex=clex, ref=ref)
        return self.calctype_settings_dir(clex=clex, calctype=calctype) / self.__ref(
            ref
        )

    def chemical_reference(self, clex: ClexDescription, calctype: str, ref: str):
        """Return chemical reference file path"""
        return self.ref_dir(clex=clex, calctype=calctype, ref=ref) / "chemical_reference.json"

    # -- Enumerations --------

    # Re-organized in v2 to use the hierarchy: calctype / config
    # to make it easier to work with all calculations of a given type
    #
    # Example:
    #
    # .. code-block:: none
    #
    #     training_data/
    #     └── calctype.<calctype_id>/
    #         └── <configname>/
    #             ├── (calculation specific input & output files)
    #             ├── POS
    #             ├── config.json
    #             ├── structure.json
    #             └── structure_with_properties.json
    #
    # Configuration names for training data directories have the following standard
    # conventions:
    #
    # - Configuration from a ConfigurationSet: ConfigurationRecord.configuration_name
    # - Configuration from a list: "config_list/<id>", where <id> is the index of the
    #   configuration in the list
    # - LocalConfiguration for a list: "event.<event_id>/<id>/<which>", where
    #   <event_id> is the event id, <id> is the index of the configuration in the local
    #   configuration list, and <which> can be "initial", "final", "mid", or "neb-<n>"

    def enum_dir(self, enum: str):
        """Return path to directory contain enumeration info (new v2.0)"""
        return self.path / self.__enum_dir / self.__enum(enum=enum)

    def enum_calctype_dir(self, enum: str, calctype: str):
        """Return global calculation settings directory path (new v2.0)"""
        return self.enum_dir(enum) / "training_data" / self.__calctype(calctype)

    def enum_calc_dir(self, enum: str, calctype: str, configname: str):
        """Return global calculation settings directory path (new v2.0)"""
        return self.enum_calctype_dir(enum=enum, calctype=calctype) / configname

    def enum_config_file(self, enum: str, configname: str, calctype: str):
        """Return path to config.json for a configuration in an enumeration
        (new v2.0)"""
        return (
            self.enum_calc_dir(enum=enum, calctype=calctype, configname=configname)
            / "config.json"
        )

    def enum_structure_file(self, enum: str, configname: str, calctype: str):
        """Return path to structure.json for a configuration in an enumeration
        (new v2.0)"""
        return (
            self.enum_calc_dir(enum=enum, calctype=calctype, configname=configname)
            / "structure.json"
        )

    def enum_POS_file(self, enum: str, configname: str, calctype: str):
        """Return path to POS for a configuration in an enumeration (new v2.0)"""
        return (
            self.enum_calc_dir(enum=enum, calctype=calctype, configname=configname)
            / "POS"
        )

    def enum_structure_with_properties_file(
        self, enum: str, configname: str, calctype: str
    ):
        """Return path to structure_with_properties.json for a configuration in an
        enumeration (new v2.0)"""
        return (
            self.enum_calc_dir(enum=enum, calctype=calctype, configname=configname)
            / "structure_with_properties.json"
        )

    # -- Composition axes --------

    def composition_axes(self):
        """Return composition axes file path (deprecated)

        .. deprecated:: 2.0a1

            Included for v1 project compatibility. Use
            :func:`~casm.project.DirectoryStructure.chemical_composition_axes` instead.
            Will be removed in 2.0.0.

        """
        warnings.warn(
            "The method 'casm.project.DirectoryStructure.composition_axes' is "
            "deprecated and will be removed in a future version. Use "
            "'casm.project.DirectoryStructureV1.composition_axes', "
            "'casm.project.DirectoryStructure.chemical_composition_axes', or "
            "'casm.project.DirectoryStructure.occupant_composition_axes' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.casm_dir() / "composition_axes.json"

    def chemical_composition_axes(self):
        """Return chemical composition axes file path

        The `chemical_composition_axes` and `occupant_composition_axes` allow
        treating occupants that have the same chemical name but different
        magnetic spin, molecular orientation, etc. CASM v1 projects only
        have `composition_axes`.
        """
        return self.casm_dir() / "chemical_composition_axes.json"

    def occupant_composition_axes(self):
        """Return occupant composition axes file path

        The `chemical_composition_axes` and `occupant_composition_axes` allow
        treating occupants that have the same chemical name but different
        magnetic spin, molecular orientation, etc. CASM v1 projects only
        have `composition_axes`.
        """
        return self.casm_dir() / "occupant_composition_axes.json"

    # -- Imports --------

    def import_dir(self, id: str):
        """Return path to directory contain structure import info"""
        return self.path / self.__import_dir / self.__import(id)

    def import_settings(self, id: str):
        """Return path to the file contain structure import settings"""
        return self.path / self.__import_dir / self.__import(id) / "settings.json"

    # -- Fits --------

    def fit_dir(self, fit: str):
        """Return path to directory containing fitting data"""
        return self.path / self.__fit_dir / self.__fit(fit)

    # -- Systems --------

    def system_dir(self, system: str, index: Optional[int] = None):
        """Return path to directory containing system info

        For a basic system with a single set of parameters, the system information
        is expected to be stored in a directory named `system.<id>`:

        .. code-block:: shell

            systems/
            └── system.<id>/
                ├── formation_energy_eci.json
                ├── system.json
                ...

        For statistics, related systems may be stored in subdirectories as:

        .. code-block:: shell

            systems/
            └── system.<id>/
                ├── 0/
                │   ├── formation_energy_eci.0.json
                │   ├── system.0.json
                │   ...
                ├── 1/
                │   ├── formation_energy_eci.1.json
                │   ├── system.1.json
                │   ...
                └── 2/
                    ├── formation_energy_eci.2.json
                    ├── system.2.json
                    ...

        Parameters
        ----------
        system: str
            The system identifier
        index: Optional[int] = None
            The index of the sampled system. If None, then the path to the
            system directory is returned; otherwise the path to the sampled
            system subdirectory is returned

        Returns
        -------
        system_dir: pathlib.Path
            Path to the system directory or sampled system subdirectory

        """
        if index is None:
            return self.path / self.__system_dir / self.__system(system)
        else:
            return self.path / self.__system_dir / self.__system(system) / str(index)

    def system_count(self, system: str):
        """Return number of sampled systems

        For a system with a single set of parameters, the system information
        is expected to be stored in a directory named `system.<id>`:

        .. code-block:: shell

            systems/
            └── system.<id>/
                ├── formation_energy_eci.json
                ├── system.json
                ...

        For statistics, sampled systems may be stored in subdirectories as:

        .. code-block:: shell

            systems/
            └── system.<id>/
                ├── 0/
                │   ├── formation_energy_eci.0.json
                │   ├── system.0.json
                │   ...
                ├── 1/
                │   ├── formation_energy_eci.1.json
                │   ├── system.1.json
                │   ...
                └── 2/
                    ├── formation_energy_eci.2.json
                    ├── system.2.json
                    ...


        The `system_count` gives the number of sampled systems.

        Returns
        -------
        count: int
            The number of sampled systems. If no subdirectory `0` exists, then
            0 is returned.

        """
        path = self.system_dir(system=system)
        count = 0
        subdir = path / str(count)
        if not subdir.exists():
            return None
        while subdir.exists():
            count += 1
            subdir = path / str(count)
        return count

    def system_file(self, system: str, index: Optional[int] = None):
        """Return path to a system file

        Parameters
        ----------
        system: str
            The system identifier
        index: Optional[int] = None
            The index of the related system. If None, then the path to the
            system file is returned, otherwise the path to the sampled
            system file is returned.

        Returns
        -------
        system_file: pathlib.Path
            Path to the system or sampled system file
        """
        if index is None:
            return self.path / self.__system_dir / self.__system(system) / "system.json"
        else:
            return (
                self.path
                / self.__system_dir
                / self.__system(system)
                / str(index)
                / "system.json"
            )

    # -- Plots --------

    def views_dir(self):
        """Return path to directory for saving casm-vis view states."""
        return self.path / self.__plot_settings_dir / "views"

    # private:

    def __enum(self, enum: str):
        return "enum." + enum

    def __bset(self, bset: str):
        return "bset." + bset

    def __calctype(self, calctype: str):
        return "calctype." + calctype

    def __ref(self, ref: str):
        return "ref." + ref

    def __import(self, import_id: str):
        return "import." + import_id

    def __fit(self, fit: str):
        return "fit." + fit

    def __system(self, system: str):
        return "system." + system

    def __plottype(self, plottype: str):
        return "plottype." + plottype

    def __all_settings(self, pattern: str, location: pathlib.Path):
        """
        Find all directories at 'location' that match 'pattern.something'
        and return a std::vector of the 'something'
        """

        all = []
        pattern += "."

        # get all
        if not location.exists():
            return all

        for child in location.iterdir():
            if child.is_dir() and child.name[: len(pattern)] == pattern:
                all.append(child.name[len(pattern) :])
        return sorted(all)
