import pathlib
import numpy as np
from typing import Optional, TypeVar, Union


import libcasm.casmglobal as casmglobal
import libcasm.configuration as casmconfig
import libcasm.configuration.io as config_io
import libcasm.xtal as xtal

from ._CompositionAxes import (
    ChemicalCompositionAxes,
    OccupantCompositionAxes,
)
from ._DirectoryStructure import DirectoryStructure
from ._methods import (
    PrimToleranceSensitivity,
    make_symmetrized_prim,
    project_path,
)
from ._ProjectSettings import ProjectSettings
from .json_io import (
    printpathstr,
    read_optional,
    read_required,
    safe_dump,
)

ProjectType = TypeVar("Project")


class Project:
    """Access and store CASM project files in a standard format"""

    def __init__(
        self,
        path: Union[str, pathlib.Path, None] = None,
    ):
        self.dir: DirectoryStructure = DirectoryStructure(path=path)
        """casm.project.DirectoryStructure: Standard CASM directory structure"""

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

        self.chemical_composition_axes = None
        """ChemicalCompositionAxes: Project chemical composition axes.
        
        The chemical composition axes are based on compositions calculated such that
        all :class:`~libcasm.xtal.Occupant` that have the same "chemical name" 
        (:func:`~libcasm.xtal.Occupant.name`) are treated as a single component, 
        even if they have different magnetic spin, molecular orientation, etc.
        """

        self.chemical_composition = None
        """ChemicalCompositionCalculator: Configuration chemical \
        composition calculator.
        
        The "chemical composition" treats all :class:`~libcasm.xtal.Occupant` that 
        have the same "chemical name" (:func:`~libcasm.xtal.Occupant.name`) as a 
        single component, even if they have different magnetic spin, molecular 
        orientation, etc.
        """

        self.occupant_composition_axes = None
        """OccupantCompositionAxes: Project distinct occupant composition \
        axes.
        
        The occupant composition axes are based on compositions calculated such that
        all :class:`~libcasm.xtal.Occupant` that have different magnetic spin, 
        molecular orientation, etc. are treated as a distinct components. 
        """

        self.occupant_composition = None
        """OccupantCompositionCalculator: Configuration distinct \
        occupants composition calculator.

        The "occupant composition" treats all :class:`~libcasm.xtal.Occupant` that 
        have different magnetic spin, molecular orientation, etc. as distinct
        components.
        """

        self.strain_reference = self.prim.xtal_prim.lattice()
        # by default set it to the lattice of the prim
        """Reference `Lattice` (`L_{ref}`) used for computing relaxation strains
        for `Configurations` in the project

        Relaxation strain in Hencky, Green-Lagrange or any other metric of 
        a relaxed `Configuration` with a strained `Lattice` (`L_{relaxed}`) will be 
        computed based on the deformation tensor (`F`) w.r.t the reference `Lattice`.
        This is defined as `L_{relaxed} = F L_{ref}`

        By default it is set to the lattice of the prim
        """

        if self.dir.chemical_composition_axes().exists():
            self.chemical_composition_axes = ChemicalCompositionAxes.from_dict(
                read_optional(self.dir.chemical_composition_axes())
            )
        elif self.dir.composition_axes().exists():
            print(
                "Note: Using existing composition_axes.json file for chemical "
                "compositions (CASM v1 compatibility)."
            )
            self.chemical_composition_axes = ChemicalCompositionAxes.from_dict(
                read_optional(self.dir.composition_axes())
            )
        else:
            self.chemical_composition_axes = ChemicalCompositionAxes.init(
                xtal_prim=self.prim.xtal_prim,
                sort=True,
            )
        self.chemical_composition = self.chemical_composition_axes.config_composition

        if self.dir.occupant_composition_axes().exists():
            self.occupant_composition_axes = OccupantCompositionAxes.from_dict(
                read_optional(self.dir.occupant_composition_axes())
            )
        elif self.dir.composition_axes().exists():
            print(
                "Note: Using existing composition_axes.json file for occupant "
                "compositions (CASM v1 compatibility)."
            )
            self.occupant_composition_axes = OccupantCompositionAxes.from_dict(
                read_optional(self.dir.composition_axes())
            )
        else:
            self.occupant_composition_axes = OccupantCompositionAxes.init(
                xtal_prim=self.prim.xtal_prim,
                sort=True,
            )
        self.occupant_composition = self.occupant_composition_axes.config_composition

    @property
    def bset(self):
        """casm.project.commands.BsetCommand: Methods to construct and print cluster \
        expansion basis sets"""
        from casm.project.commands import BsetCommand

        return BsetCommand(proj=self)

    @property
    def enum(self):
        """casm.project.commands.EnumCommand: Methods to enumerate supercells, \
        configurations, events, etc."""
        from casm.project.commands._EnumCommand import EnumCommand

        return EnumCommand(proj=self)

    @property
    def sym(self):
        """casm.project.commands.SymCommand: Methods to analyse and print symmetry \
        information"""
        from casm.project.commands._SymCommand import SymCommand

        return SymCommand(proj=self)

    @staticmethod
    def init(
        path: Union[str, pathlib.Path, None] = None,
        prim: Union[xtal.Prim, casmconfig.Prim, dict, str, pathlib.Path, None] = None,
        name: Optional[str] = None,
        crystallography_tol: float = casmglobal.TOL,
        force: bool = False,
    ) -> ProjectType:
        """Initialize a CASM project

        This constructs a CASM project at the specified path and returns a
        :class:`~casm.project.Project` instance representing the project.

        Parameters
        ----------
        path: Union[str, pathlib.Path, None] = None
            The project root directory. If None, the current working directory is used.
        prim: Union[libcasm.xtal.Prim, libcasm.configuration.Prim, dict, str, pathlib.Path, None] = None
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

        check_path = project_path(path)

        if prim is None and check_path is not None:
            print(f"CASM project already exists at {path}")
            print("Using existing project")
            return Project(path=check_path)

        if check_path == path:
            raise Exception(
                "Error in casm.project.Project.init: "
                f"CASM project already exists at {path}"
            )
        elif check_path is not None:
            print(
                "Note: Creating a sub-project. "
                f"A project already exists at {check_path}"
            )

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
                msg += f"- Writing canonical, symmetrized prim: {canonical_symmetrized_path}\n"
                msg += f"- Canonical, symmetrized prim: \n{canonical_symmetrized_prim_str}\n"

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
        dir.eci_dir(clex=settings.default_clex).mkdir(parents=True, exist_ok=True)
        dir.calctype_settings_dir(calctype=settings.default_clex.calctype).mkdir(
            parents=True, exist_ok=True
        )

        # Write standard composition axes
        safe_dump(
            data=proj.chemical_composition_axes.to_dict(),
            path=dir.chemical_composition_axes(),
        )
        safe_dump(
            data=proj.occupant_composition_axes.to_dict(),
            path=dir.occupant_composition_axes(),
        )

        # Write symmetry info (overwrite existing files)
        # - write lattice_point_group.json,
        lattice_point_group_data = config_io.symgroup_to_dict_with_group_classification(
            prim.xtal_prim.lattice(),
            prim.lattice_point_group,
        )
        safe_dump(
            data=lattice_point_group_data,
            path=dir.lattice_point_group(),
            force=True,
        )

        # - write factor_group.json,
        factor_group_data = config_io.symgroup_to_dict_with_group_classification(
            prim,
            prim.factor_group,
        )
        safe_dump(
            data=factor_group_data,
            path=dir.factor_group(),
            force=True,
        )

        # - write crystal_point_group.json
        crystal_point_group_data = config_io.symgroup_to_dict_with_group_classification(
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
            f"- spacegroup={type_info['number']}\n"
        )

        type_info = crystal_point_group_data["group_classification"]["spacegroup_type"]
        print(
            "Crystal point group: \n"
            f"- size={len(prim.crystal_point_group.elements)}\n"
            f"- international={type_info['pointgroup_international']}\n"
            f"- schoenflies={type_info['pointgroup_schoenflies']}\n"
        )

        print("DONE")

        return proj
