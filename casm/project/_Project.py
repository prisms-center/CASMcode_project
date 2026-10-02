import pathlib
from typing import Optional, Union

import numpy as np

import libcasm.casmglobal as casmglobal
import libcasm.clexulator as casmclex
import libcasm.configuration as casmconfig
import libcasm.xtal as xtal
from casm.tools.shared.json_io import (
    printpathstr,
    read_optional,
    read_required,
    safe_dump,
)

from ._CompositionAxes import CompositionAxes
from ._DirectoryStructure import (
    DirectoryStructure,
    DirectoryStructureV1,
)
from ._methods import (
    PrimToleranceSensitivity,
    get_dof_types,
    get_generic_dof_types,
    make_symmetrized_prim,
    project_path,
)
from ._ProjectSettings import ProjectSettings
from ._symgroup import symgroup_to_dict_with_group_classification


class Project:
    """Access and store CASM project files in a standard format"""

    def __init__(
        self,
        path: Union[str, pathlib.Path, None] = None,
    ):
        self.dir: DirectoryStructure = DirectoryStructure(path=path)
        """casm.project.DirectoryStructure: Standard CASM directory structure"""

        self._dir_v1: DirectoryStructureV1 = DirectoryStructureV1(path=path)
        """casm.project.DirectoryStructureV1: CASM v1 directory structure (for
        compatibility with v1 projects)"""

        self.path: pathlib.Path = self.dir.path
        """str: Path to CASM project."""

        self.settings: ProjectSettings = ProjectSettings.from_dict(
            data=read_required(self.dir.project_settings())
        )
        """casm.project.ProjectSettings: CASM project settings"""

        self.name: str = self.settings.name
        """str: CASM project name"""

        self.prim = casmconfig.Prim.from_dict(read_required(self.dir.prim()))
        """libcasm.configuration.Prim: Primitive crytal structure and allowed degrees 
        of freedom (DoF) with symmetry information"""

        (
            self._global_dof,
            self._local_continuous_dof,
            self._local_discrete_dof,
        ) = get_dof_types(xtal_prim=self.prim.xtal_prim)

        self._generic_dof = get_generic_dof_types(xtal_prim=self.prim.xtal_prim)

        self.prim_neighbor_list = casmclex.PrimNeighborList(
            lattice_weight_matrix=self.settings.nlist_weight_matrix,
            sublattice_indices=self.settings.nlist_sublat_indices,
            total_n_sublattice=len(self.prim.xtal_prim.occ_dof()),
        )
        """casmclex.PrimNeighborList: The :class:`PrimNeighborList` used for 
        constructing Clexulator.
        
        If the `nlist_weight_matrix` or `nlist_sublat_indices` project settings change,
        the Project should be re-constructed so that the `PrimNeighborList` is updated,
        and all basis sets will need to be updated with the new neighbor list.
        """

        self.chemical_composition_axes = None
        """CompositionAxes: Project chemical composition axes.
        
        The chemical composition axes are based on compositions calculated such that
        all :class:`~libcasm.xtal.Occupant` that have the same "chemical name" 
        (:func:`~libcasm.xtal.Occupant.name`) are treated as a single component, 
        even if they have different magnetic spin, molecular orientation, etc.
        """

        self.occupant_composition_axes = None
        """CompositionAxes: Project distinct occupant composition \
        axes.
        
        The occupant composition axes are based on compositions calculated such that
        all :class:`~libcasm.xtal.Occupant` that have different magnetic spin, 
        molecular orientation, etc. are treated as a distinct components. 
        """

        if self.dir.chemical_composition_axes().exists():
            self.chemical_composition_axes = CompositionAxes(
                path=self.dir.chemical_composition_axes()
            )
            self.chemical_composition_axes.load()
        elif self._dir_v1.composition_axes().exists():
            print(
                "Note: Using existing composition_axes.json file for chemical "
                "compositions (CASM v1 compatibility)."
            )
            self.chemical_composition_axes = CompositionAxes.from_dict(
                data=read_optional(self._dir_v1.composition_axes()),
                path=self.dir.chemical_composition_axes(),
            )
        else:
            self.chemical_composition_axes = CompositionAxes.init_chemical_axes(
                xtal_prim=self.prim.xtal_prim,
                path=self.dir.chemical_composition_axes(),
            )

        if self.dir.occupant_composition_axes().exists():
            self.occupant_composition_axes = CompositionAxes.from_dict(
                read_optional(self.dir.occupant_composition_axes())
            )
        elif self._dir_v1.composition_axes().exists():
            print(
                "Note: Using existing composition_axes.json file for occupant "
                "compositions (CASM v1 compatibility)."
            )
            self.occupant_composition_axes = CompositionAxes.from_dict(
                read_optional(self._dir_v1.composition_axes())
            )
        else:
            self.occupant_composition_axes = CompositionAxes.init_occupant_axes(
                xtal_prim=self.prim.xtal_prim,
                path=self.dir.occupant_composition_axes(),
            )

        # Make project.X persist
        self._enum = None
        self._bset = None
        self._sym = None
        self._calc = None
        self._structure_import = None
        self._fit = None
        self._system = None
        self._vis = None

    def make_chemical_comp_calculator(self):
        """Make a chemical composition calculator using the current axes.

        The "chemical composition" treats all :class:`~libcasm.xtal.Occupant` that
        have the same "chemical name" (:func:`~libcasm.xtal.Occupant.name`) as a
        single component, even if they have different magnetic spin, molecular
        orientation, etc.

        Returns
        -------
        chemical_comp_calculator: casm.configuration.ConfigCompositionCalculator
            A configuration composition calculator for the chemical composition axes,
            using the currently selected parametric composition axes (may be None).
        """
        return self.chemical_composition_axes.make_config_comp_calculator()

    def make_occupant_comp_calculator(self):
        """Make an occupant composition calculator using the current axes.

        The "occupant composition" treats all :class:`~libcasm.xtal.Occupant` that
        have different magnetic spin, molecular orientation, etc. as distinct
        components.

        Returns
        -------
        occupant_comp_calculator: casm.configuration.ConfigCompositionCalculator
            A configuration composition calculator for the occupant composition axes,
            using the currently selected parametric composition axes (may be None).
        """
        return self.occupant_composition_axes.make_config_comp_calculator()

    def commit_settings(self):
        """Commit the project settings to the project directory."""
        safe_dump(
            data=self.settings.to_dict(),
            path=self.dir.project_settings(),
            force=True,
        )

    def load_settings(self):
        """Load the project settings from the project directory."""
        prev_settings = self.settings

        self.settings = ProjectSettings.from_dict(
            data=read_required(self.dir.project_settings())
        )

        if self.settings.name != prev_settings.name:
            print(f"""!!! Warning: Project name has changed !!!
            
Project name changed from '{prev_settings.name}' to '{self.settings.name}'. 

You will need to:
1) Construct a new Project object for this project
2) Update all bset built with the previous project name 
   using project.bset.update(...).""")

        if not np.allclose(
            self.settings.nlist_weight_matrix, prev_settings.nlist_weight_matrix
        ) or not (
            self.settings.nlist_sublat_indices == prev_settings.nlist_sublat_indices
        ):
            print("""!!! Warning: Project neighbor list has changed !!!

The neighbor list weight matrix has changed.

You will need to:
1) Construct a new Project object for this project
2) Update all bset built with the previous project name 
   using project.bset.update(...).""")

    @property
    def global_dof_types(self):
        """list[str]: List of global degrees of freedom for the project."""
        return self._global_dof

    @property
    def local_continuous_dof_types(self):
        """list[str]: List of local continuous degrees of freedom for the project."""
        return self._local_continuous_dof

    @property
    def local_discrete_dof_types(self):
        """list[str]: List of local discrete degrees of freedom for the project."""
        return self._local_discrete_dof

    @property
    def generic_dof_types(self):
        """list[str]: List of generic degrees of freedom for the project (i.e. "strain"
        instead of "Hstrain")."""
        return self._generic_dof

    @property
    def bset(self):
        """casm.project.bset.BsetCommand: Methods to construct and print cluster \
        expansion basis sets"""
        from casm.project.bset import BsetCommand

        if self._bset is None:
            self._bset = BsetCommand(proj=self)
        return self._bset

    @property
    def enum(self):
        """casm.project.enum.EnumCommand: Methods to enumerate supercells, \
        configurations, events, etc."""
        from casm.project.enum import EnumCommand

        if self._enum is None:
            self._enum = EnumCommand(proj=self)
        return self._enum

    @property
    def sym(self):
        """casm.project.sym.SymCommand: Methods to analyse and print symmetry \
        information"""
        from casm.project.sym import SymCommand

        if self._sym is None:
            self._sym = SymCommand(proj=self)
        return self._sym

    @property
    def calc(self):
        """casm.project.calc.CalcCommand: Methods to help setup, perform, and collect
        DFT calculations"""
        from casm.project.calc import CalcCommand

        if self._calc is None:
            self._calc = CalcCommand(proj=self)
        return self._calc

    @property
    def structure_import(self):
        """casm.project.structure_import.StructureImportCommand: Methods to import and
        map structures"""
        from casm.project.structure_import import StructureImportCommand

        if self._structure_import is None:
            self._structure_import = StructureImportCommand(proj=self)
        return self._structure_import

    @property
    def fit(self):
        """casm.project.fit.FitCommand: Methods to fit cluster expansions"""
        from casm.project.fit import FitCommand

        if self._fit is None:
            self._fit = FitCommand(proj=self)
        return self._fit

    @property
    def system(self):
        """casm.project.system.SystemCommand: Methods to setup and use model systems"""
        from casm.project.system import SystemCommand

        if self._system is None:
            self._system = SystemCommand(proj=self)
        return self._system

    @property
    def vis(self):
        """casm.project.vis.VisCommand: Visualize CASM project data."""
        from casm.project.vis import VisCommand

        if self._vis is None:
            self._vis = VisCommand(proj=self)
        return self._vis

    @staticmethod
    def init(
        path: Union[str, pathlib.Path, None] = None,
        prim: Union[xtal.Prim, casmconfig.Prim, dict, str, pathlib.Path, None] = None,
        name: Optional[str] = None,
        crystallography_tol: float = casmglobal.TOL,
        force: bool = False,
    ) -> "Project":
        """Initialize a CASM project

        This constructs a CASM project at the specified path and returns a
        :class:`~casm.project.Project` instance representing the project.

        Notes
        -----

        Initializing a project checks that the input prim is primitive,
        right-handed, in canonical form, and not sensitive to the crystallography
        tolerance. These can be overridden with `force=True`. If the checks fail,
        suggested prims are written to the project root. See
        :func:`~casm.project.make_symmetrized_prim`,
        :func:`~libcasm.xtal.make_canonical_prim`, and
        :func:`~libcasm.xtal.make_primitive_prim` for more information.
        `crystallography_tol` is only used when `prim` is read from a dictionary or
        JSON.

        Parameters
        ----------
        path: Union[str, pathlib.Path, None] = None
            The project root directory. If None, the current working directory is used.
        prim: Union[libcasm.xtal.Prim, libcasm.configuration.Prim, dict, str, \
        pathlib.Path, None] = None
            The prim, or the path to the prim.json file. If None, a `prim.json` file
            is expected in the project directory specified by `path`. Unless the
            `force` option is used, the prim must be in primitive, canonical form, and
            the lattice point group size, factor group size, and canonical lattice
            cannot vary for a crystallography tolerance in the range `[1e-7, 1e-3]`.
        name: str = None
            Project name. If not provided, uses title from `prim`. Must consist of
            alphanumeric characters and underscores only. The first character may not
            be a number.
        crystallography_tol: float = casmglobal.TOL
            The tolerance for crystallography comparisons.
        force: bool = False
            If True, allow initialization of a project with a non-standard or
            tolerance sensitive prim.

        Returns
        -------
        project: casm.project.Project
            The created project object.
        """
        ### Get CASM project path
        if path is None:
            path = pathlib.Path.cwd()
        else:
            path = pathlib.Path(path)

        check_path = None
        if path.exists():
            check_path = project_path(path)

        if check_path is not None:
            if check_path.resolve() == path.resolve():
                print(f"CASM project already exists at {printpathstr(path)}")
                print("Using existing project")
                return Project(path=check_path)
            else:
                print("** Creating a sub-project. **")
                print(f"A project already exists at {printpathstr(check_path)}")
                print()

        if not path.exists():
            print(f"Creating CASM project directory at {printpathstr(path)}")
            path.mkdir(parents=True, exist_ok=True)

        ### Get Prim
        if isinstance(prim, casmconfig.Prim):
            pass
        elif isinstance(prim, xtal.Prim):
            prim = casmconfig.Prim(prim)
        elif isinstance(prim, dict):
            prim = casmconfig.Prim(
                xtal.Prim.from_dict(
                    prim,
                    xtal_tol=crystallography_tol,
                )
            )
        else:
            prim_path = None
            if prim is None:
                prim_path = path / "prim.json"
            else:
                prim_path = pathlib.Path(prim)

            if not prim_path.exists():
                raise Exception(
                    "Error in casm.project.Project.init: "
                    f"No prim.json file at {prim_path}"
                )
            prim = casmconfig.Prim(
                xtal.Prim.from_dict(
                    read_required(prim_path),
                    xtal_tol=crystallography_tol,
                )
            )

        if not isinstance(prim, casmconfig.Prim):
            raise Exception(
                "Error in casm.project.Project.init: "
                "Failed to construct Prim (unknown reason)"
            )

        ### Warn if prim is not atomic:
        if not prim.is_atomic:
            print(
                "\n"
                "** WARNING *********************************************************\n"
                "The prim is not atomic. An atomic prim:                             \n"
                "- allows 1 or more occupants on each site,                          \n"
                "- all occupants have a single atom without coordinate offset,       \n"
                "- there are no Occupant properties, only AtomComponent properties.  \n"
                "                                                                    \n"
                "Some CASM methods, such as structure mapping and conversions between\n"
                "configuration and structure, may not be implemented. If possible,   \n"
                "use AtomComponent properties for magspin instead of Occupant        \n"
                "properties .                                                        \n"
                "********************************************************************\n"
                "\n"
            )

        ### Checks to see if the prim is a standard prim and not tolerance sensitive ###
        # Check primitive, canonical form
        xtal_prim = prim.xtal_prim
        canonical_xtal_prim = xtal.make_canonical_prim(
            xtal.make_primitive_prim(xtal_prim)
        )
        canonical_symmetrized_xtal_prim = None

        is_standard = True
        msg = ""
        if xtal_prim.lattice().volume() < 0.0:
            msg += "--- !! Input prim is not right-handed !! ---\n"
            is_standard = False
        if len(canonical_xtal_prim.occ_dof()) != len(xtal_prim.occ_dof()):
            msg += "--- !! Input prim is not primitive !! ---\n"
            is_standard = False
        if canonical_xtal_prim.lattice() != xtal_prim.lattice():
            msg += "--- !! Input prim is not canonical !! ---\n"
            is_standard = False

        # Check sensitivity to crystallography_tol
        x = PrimToleranceSensitivity(xtal_prim=xtal_prim)
        if x.is_sensitive:
            if x.lattice_point_group_size_sensitivity_msg is not None:
                msg += x.lattice_point_group_size_sensitivity_msg
            if x.factor_group_size_sensitivity_msg is not None:
                msg += x.factor_group_size_sensitivity_msg
            if x.canonical_lattice_sensitivity_msg is not None:
                msg += x.canonical_lattice_sensitivity_msg

            msg += (
                f"- Will attempt to symmetrize the canonical prim using symmetry \n"
                f"  operations found with tol={x.symmetrize_tol}\n"
            )

            symmetrized_xtal_prim = make_symmetrized_prim(
                prim=canonical_xtal_prim,
                tol=x.symmetrize_tol,
            ).xtal_prim
            canonical_symmetrized_xtal_prim = xtal.make_canonical_prim(
                xtal.make_primitive_prim(symmetrized_xtal_prim)
            )
            y = PrimToleranceSensitivity(canonical_symmetrized_xtal_prim)
            if y.is_sensitive:
                msg += "- FAILED: Tolerance sensitivity remains.\n\n"

                msg += "~~~ Symmetrization attempt results ~~~ \n"
                if y.lattice_point_group_size_sensitivity_msg is not None:
                    msg += y.lattice_point_group_size_sensitivity_msg
                if y.factor_group_size_sensitivity_msg is not None:
                    msg += y.factor_group_size_sensitivity_msg
                if y.canonical_lattice_sensitivity_msg is not None:
                    msg += y.canonical_lattice_sensitivity_msg
                msg += "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ \n\n"
            else:
                msg += "- SUCCESS: Symmetrization removed the tolerance sensitivity\n"
            is_standard = False

        ### If not a standard prim, print warnings and suggested prim ###
        if not is_standard:
            # Write canonical (but not symmetrized) prim
            canonical_path = path / "prim.canonical.json"
            index = 2
            while canonical_path.exists():
                canonical_path = path / f"prim.canonical.{index}.json"
                index += 1

            canonical_prim_str = xtal.pretty_json(canonical_xtal_prim.to_dict())

            msg += "\n"
            msg += f"- Writing canonical prim: {canonical_path}\n"
            msg += f"- Canonical prim: \n{canonical_prim_str}\n"

            with open(canonical_path, "w") as f:
                f.write(canonical_prim_str)

            # Write canonical and symmetrized prim
            if x.is_sensitive:
                canonical_symmetrized_path = path / "prim.canonical.symmetrized.json"
                index = 2
                while canonical_symmetrized_path.exists():
                    canonical_symmetrized_path = (
                        path / f"prim.canonical.symmetrized.{index}.json"
                    )
                    index += 1

                canonical_symmetrized_prim_str = xtal.pretty_json(
                    canonical_symmetrized_xtal_prim.to_dict()
                )

                msg += "\n"
                msg += (
                    f"- Writing canonical, symmetrized prim: "
                    f"{canonical_symmetrized_path}\n"
                )
                msg += (
                    f"- Canonical, symmetrized prim: "
                    f"{canonical_symmetrized_prim_str}\n"
                )

                with open(canonical_symmetrized_path, "w") as f:
                    f.write(canonical_symmetrized_prim_str)

            if force:
                msg += "- Continuing due to usage of 'force' option.\n"
                print(msg)
            else:
                msg += "- Stopping.\n"
                msg += "- To initialize your project anyway, use the 'force' option.\n"
                print(msg)
                print("FAILED")
                return None

        ### If a standard prim, or "force", build the project ###

        # Create default project settings
        settings = ProjectSettings.make_default(
            xtal_prim=xtal_prim,
            name=name,
        )
        dir = DirectoryStructure(path=path)

        print(f"Initializing CASM project '{settings.name}'")
        print(f"Creating CASM project directory tree at: {printpathstr(dir.path)}")

        # Create .casm and files (fail if already exists)
        dir.casm_dir().mkdir(parents=True, exist_ok=False)
        safe_dump(
            data=prim.to_dict(),
            path=dir.prim(),
            force=False,
        )
        safe_dump(
            data=settings.to_dict(),
            path=dir.project_settings(),
            force=False,
        )

        # Create the project obj (also creates standard composition axes)
        proj = Project(path=path)

        # Create standard directories
        dir.symmetry_dir().mkdir(parents=True, exist_ok=True)
        dir.bset_dir(clex=settings.default_clex).mkdir(parents=True, exist_ok=True)
        dir.calctype_settings_dir(calctype=settings.default_clex.calctype).mkdir(
            parents=True, exist_ok=True
        )

        # Write standard composition axes
        proj.chemical_composition_axes.commit()
        proj.occupant_composition_axes.commit()

        # Write symmetry info (overwrite existing files)
        # - write lattice_point_group.json,
        lattice_point_group_data = symgroup_to_dict_with_group_classification(
            prim,
            prim.lattice_point_group,
        )
        safe_dump(
            data=lattice_point_group_data,
            path=dir.lattice_point_group(),
            force=True,
        )

        # - write factor_group.json,
        factor_group_data = symgroup_to_dict_with_group_classification(
            prim,
            prim.factor_group,
        )
        safe_dump(
            data=factor_group_data,
            path=dir.factor_group(),
            force=True,
        )

        # - write crystal_point_group.json
        crystal_point_group_data = symgroup_to_dict_with_group_classification(
            prim,
            prim.crystal_point_group,
        )
        safe_dump(
            data=crystal_point_group_data,
            path=dir.crystal_point_group(),
            force=True,
        )
        print()

        # Lattice point group
        type_info = lattice_point_group_data["group_classification"]["spacegroup_type"]
        print(
            "Lattice point group: \n"
            f"- size={len(prim.lattice_point_group.elements)}\n"
            f"- international={type_info['pointgroup_international']}\n"
            f"- schoenflies={type_info['pointgroup_schoenflies']}\n"
        )

        type_info = factor_group_data["group_classification"]["spacegroup_type"]
        print(
            "Factor group: \n"
            f"- size={len(prim.factor_group.elements)}\n"
            f"- international={type_info['international']}, "
            f"{type_info['international_full']}, "
            f"{type_info['international_short']}\n"
            f"- schoenflies={type_info['schoenflies']}\n"
            f"- spacegroup={type_info['number']}\n",
            end="",
        )
        if "magnetic_spacegroup_type" in factor_group_data["group_classification"]:
            type_info = factor_group_data["group_classification"][
                "magnetic_spacegroup_type"
            ]
            print(f"- magnetic spacegroup uni_number={type_info['uni_number']}\n")
        else:
            print()

        type_info = crystal_point_group_data["group_classification"]["spacegroup_type"]
        print(
            "Crystal point group: \n"
            f"- size={len(prim.crystal_point_group.elements)}\n"
            f"- international={type_info['pointgroup_international']}\n"
            f"- schoenflies={type_info['pointgroup_schoenflies']}\n",
            end="",
        )
        if (
            "magnetic_spacegroup_type"
            in crystal_point_group_data["group_classification"]
        ):
            type_info = crystal_point_group_data["group_classification"][
                "magnetic_spacegroup_type"
            ]
            print(f"- magnetic spacegroup uni_number={type_info['uni_number']}\n")
        else:
            print()

        print("DONE")

        return proj
