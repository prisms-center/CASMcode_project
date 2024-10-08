import pathlib
import re
import sys
import time
from typing import Optional, TYPE_CHECKING, Union

import numpy as np

from casm.bset import build_cluster_functions, make_clex_basis_specs, write_clexulator
from casm.bset.cluster_functions import ClexBasisSpecs, ClusterFunctionsBuilder
from libcasm.clexulator import (
    Clexulator,
    LocalClexulator,
    make_clexulator,
    make_local_clexulator,
)
from libcasm.clusterography import Cluster, ClusterOrbitGenerator
from libcasm.occ_events import OccEvent

from ._ConfigCorrCalculator import ConfigCorrCalculator
from ._display_bset import (
    DisplayBasisOptions,
    display_functions,
)
from ._print_bset import (
    PrettyPrintBasisOptions,
    pretty_print_functions,
    pretty_print_orbits,
)
from casm.project.json_io import printpathstr, read_optional, safe_dump

if TYPE_CHECKING:
    from casm.project import Project


class BsetOutputData:
    """Reads basis set data from the files generated by
    :func:`BsetData.update <casm.project.BsetData.update>`.

    """

    def __init__(self, proj: "Project", id: str):
        self.proj = proj
        """Project: CASM project reference"""

        self.id = id
        """str: Basis set identifier"""

        self.bset_dir = self.proj.dir.bset_dir(bset=id)
        """pathlib.Path: Basis set directory"""

    ### Data from generated files (load only) ###
    # written by write_clexulator

    @property
    def basis_dict(self):
        """Optional[dict]: A description of a cluster expansion basis set.

        See the CASM documentation for the
        `basis.json format <https://prisms-center.github.io/CASMcode_docs/formats/casm/clex/ClexBasis/>`_.
        """
        return read_optional(self.bset_dir / "basis.json")

    @property
    def prototype_clusters(self) -> list[Cluster]:
        """list[Cluster]: The prototype cluster, for each basis function"""
        orbits = self.basis_dict.get("orbits")
        _prototype_clusters = []
        for orbit in orbits:
            _prototype = Cluster.from_dict(
                data=orbit.get("prototype"),
                prim=self.proj.prim.xtal_prim(),
            )
            for func in orbit.get("cluster_functions"):
                _prototype_clusters.append(_prototype)
        return _prototype_clusters

    @property
    def cluster_multiplicity(self):
        """np.ndarray[numpy.float[n_functions]]: The number of clusters per orbit, for
        each basis function"""
        orbits = self.basis_dict.get("orbits")
        mult = []
        for orbit in orbits:
            _mult = orbit.get("mult")
            for func in orbit.get("cluster_functions"):
                mult.append(_mult)
        return np.array(mult, dtype=int)

    @property
    def cluster_size(self) -> np.ndarray:
        """numpy.ndarray[numpy.int[n_functions]]: The number of cluster sites, for each
        basis function"""
        return np.array([len(x) for x in self.cluster_prototypes], dtype=int)

    @property
    def equivalents_info(self):
        """Optional[dict]: The equivalents info provides the phenomenal cluster and
        local-cluster orbits for all symmetrically equivalent local-cluster expansions,
        and the indices of the factor group operations used to construct each equivalent
        local cluster expansion from the prototype local-cluster expansion.

        When there is an orientation to the local-cluster expansion this information
        allows generating the proper diffusion events, etc. from the prototype.

        See the CASM documentation for the
        `equivalents_info.json format <TODO>`_.
        """
        self.equivalents_info = read_optional(self.bset_dir / "equivalents_info.json")

    @property
    def generated_files(self):
        """Optional[dict]: Lists of generated files.

        If available, returns a dict with format:

        - `all`: list[str], All generated files
        - `src_path`: str, Clexulator or prototype local clexulator source file
        - `local_src_path`: list[str], Local Clexulator source files

        All paths are relative to the basis set directory, as given by
        :attr:`BsetData.bset_dir <casm.project.BsetData.bset_dir>`

        """
        return read_optional(self.bset_dir / "generated_files.json")

    @property
    def src_path(self):
        """Optional[pathlib.Path]: Clexulator source file path"""
        x = self.generated_files
        if x is None:
            return None
        y = x.get("src_path")
        if y is None:
            return None
        return self.bset_dir / y

    @property
    def local_src_path(self):
        """Optional[list[pathlib.Path]]: Local Clexulator source file paths"""
        x = self.generated_files
        if x is None:
            return None
        y = x.get("local_src_path")
        if y is None:
            return None
        return [self.bset_dir / p for p in y]

    @property
    def variables(self):
        """Optional[dict]: Variables used to write the Clexulator

        Values in this file correspond to documented attributes of the class used
        to write the Clexulator, which depends on the version:

        - For version `v1.basic`: :class:`~casm.bset.clexwriter.WriterV1Basic`
        - For version `v1.diff`: :class:`~casm.bset.clexwriter.WriterV1Diff` (TODO)
        """
        return read_optional(self.bset_dir / "variables.json.gz", gz=True)

    @property
    def local_variables(self, i_equiv: int):
        """Optional[list[dict]]: Variables used to write LocalClexulator

        Values in these files correspond to documented attributes of the class used
        to write the Clexulator, which depends on the version:

        - For version `v1.basic`: :class:`~casm.bset.clexwriter.WriterV1Basic`
        - For version `v1.diff`: :class:`~casm.bset.clexwriter.WriterV1Diff` (TODO)
        """
        return read_optional(
            self.bset_dir / str(i_equiv) / "variables.json.gz", gz=True
        )


class BsetData:
    """Manage basis set data for a CASM project

    .. code-block:: shell

        <project>/
        └── basis_sets/
            └── bset.<id>/
                ├── bspecs.json
                ├── meta.json
                ├── basis.json
                ├── cluster_functions.json.gz
                ├── equivalents_info.json
                ├── variables.json.gz
                ├── generated_files.json
                ├── writer_params.json
                ├── <projectname>_Clexulator_<id>.json
                ├── 0/
                │   ├── <projectname>_Clexulator_<id>_0.cpp
                │   └── variables.json.gz
                ├── 1/
                │   └── <projectname>_Clexulator_<id>_1.cpp
                │   └── variables.json.gz
                ...

    Input files summary:

    - `bspecs.json`: Basis set specifications, used to construct
      :class:`~casm.bset.cluster_functions.ClexBasisSpecs` which specifies how to
      generate clusters and cluster functions.
    - `meta.json`: Metadata for the basis set. JSON formatted file with custom metadata
      for any use case. If `desc` exists, it will be printed as a descriptive summary
      by ``print``.
    - `writer_params.json`: Parameters used to write the Clexulator or LocalClexulator.

    Generated files summary:

    - `basis.json`: A description of the generated cluster expansion basis set. See the
      CASM documentation for the `basis.json file format
      <https://prisms-center.github.io/CASMcode_docs/formats/casm/clex/ClexBasis/>`_.
    - `equivalents_info.json`: The equivalents info provides the phenomenal cluster and
      local-cluster orbits for all symmetrically equivalent local-cluster expansions,
      and the indices of the factor group operations used to construct each equivalent
      local cluster expansion from the prototype local-cluster expansion.
    - `<Project>_Clexulator_<id>.cpp`: The Clexulator source file, or a prototype local
      Clexulator source file.
    - `cluster_functions.json.gz`: A file which contains the clusters, functions, and
      matrix representations used to construct the functions. Values in this file
      correspond to documented attributes of
      :class:`~casm.bset.cluster_functions.ClusterFunctionsBuilder`.
    - `variables.json.gz`: A file for each Clexulator (including local Clexulator) which
      contains the variables used by the jinja2 templates as well as information like
      basis function formulas generated during the write process. Values in this file
      correspond to documented attributes of the following classes:

      - For version `v1.basic`: :class:`~casm.bset.clexwriter.WriterV1Basic`
      - For version `v1.diff`: :class:`~casm.bset.clexwriter.WriterV1Diff` (TODO)

    - `<Project>_Clexulator_<id>.o`: The compiled Clexulator object file.
    - `<Project>_Clexulator_<id>.so`: The compiled Clexulator shared object library
      file.
    - `<equivalent_index>/<Project>_Clexulator_<id>_<equivalent_index>.cpp`: The
      Clexulator source file for one of the equivalent local basis sets.
    - `generated_files.json`: A list of generated files, used to track generated files
      and clean up old files.

    """

    def __init__(self, proj: "Project", id: str):
        if not re.match(
            R"^\w+",
            id,
        ):
            raise Exception(
                f"id='{id}' is not a valid basis set name: ",
                "Must consist alphanumeric characters and underscores only.",
            )

        self.proj = proj
        """casm.project.Project: CASM project reference"""

        self.id = id
        """str: Basis set identifier"""

        self.bset_dir = self.proj.dir.bset_dir(bset=id)
        """pathlib.Path: Basis set directory"""

        ### Data (load & commit) ###

        self.meta = dict()
        """dict: A description of the enumeration, read from `meta.json`."""

        self.clex_basis_specs = None
        """Optional[ClexBasisSpecs]: Clexulator basis set specifications, read from
        `bspecs.json`"""

        self.version = "v1.basic"
        """str: Version of the Clexulator to write, read from `writer_params.json`
        
        Expected to be one of:
        
        - "v1.basic": Standard CASM v1 compatible Clexulator, without automatic
          differentiation
        - "v1.diff": (TODO) CASM v1 compatible Clexulator, with ``fadbad`` automatic
          differentiation enabled
        
        """

        self.linear_function_indices = None
        """Optional[set[int]]: Linear function indices to include in the Clexulator, 
        read from `writer_params.json`
        
        If None, all functions will be included in the Clexulator.
        Otherwise, only the specified functions will be included in the Clexulator.
        Generally this is not known the first time a Clexulator is generated, but
        after fitting coefficients it may be used to re-generate the Clexulator
        with the subset of the basis functions needed.
        """

        ### Data (load only) ###
        # written by write_clexulator
        self.out = BsetOutputData(proj=proj, id=id)
        """Optional[casm.project.BsetOutputData]: Output data generated by the 
        :func:`~casm.project.BsetData.update` method."""

        self.load()

    def load(self):
        """Read bspecs.json, meta.json, and writer_params.json.

        This will replace the current contents of this BsetData object with the
        contents of the associated files, or set the current contents to None if the
        associated files do not exist.
        """

        # read meta.json if it exists
        path = self.bset_dir / "meta.json"
        self.meta = read_optional(path, default=dict())

        # read bspecs.json if it exists
        path = self.proj.dir.bspecs(bset=self.id)
        data = read_optional(path, default=None)
        if data is not None:
            self.clex_basis_specs = ClexBasisSpecs.from_dict(
                data=data,
                prim=self.proj.prim,
            )

        else:
            self.clex_basis_specs = None
            self.linear_function_indices = None
            self.version = None

        # read writer_params.json if it exists
        data = read_optional(self.bset_dir / "writer_params.json", default={})
        self.linear_function_indices = data.get("linear_function_indices", None)
        self.version = data.get("version", "v1.basic")

    def commit(self):
        """Write bspecs.json, meta.json, and writer_params.json

        Notes:

        - This will overwrite existing files.
        - If an attribute is None, the corresponding file will be deleted.

        """

        # validate clex_basis_specs
        if not isinstance(self.clex_basis_specs, ClexBasisSpecs):
            raise TypeError(
                "Error in BsetData.commit: "
                "BsetData.clex_basis_specs must be a ClexBasisSpecs"
            )
        versions = ["v1.basic"]
        if self.version not in versions:
            raise TypeError(
                f"Error in BsetData.commit: version={self.version}; "
                f"must be one of {versions}"
            )

        # validate meta
        if not isinstance(self.meta, dict):
            raise TypeError("Error in BsetData.commit: BsetData.meta must be a dict")

        # write bspecs.json
        path = self.proj.dir.bspecs(bset=self.id)
        if self.clex_basis_specs is not None:
            data = self.clex_basis_specs.to_dict()
            safe_dump(
                data=data,
                path=path,
                quiet=False,
                force=True,
            )

            # write writer_params.json
            data = {
                "version": self.version,
                "linear_function_indices": self.linear_function_indices,
            }
            safe_dump(
                data=data,
                path=self.bset_dir / "writer_params.json",
                quiet=False,
                force=True,
            )

        elif path.exists():
            print(f"Removing {printpathstr(path)}")
            path.unlink()

            path = self.bset_dir / "writer_params.json"
            print(f"Removing {printpathstr(path)}")
            path.unlink()

        # write meta.json:
        path = self.bset_dir / "meta.json"
        if len(self.meta) > 0:
            safe_dump(
                data=self.meta,
                path=path,
                quiet=False,
                force=True,
            )
        elif path.exists():
            print(f"Removing {printpathstr(path)}")
            path.unlink()

        # newline
        print()

    def clean(self, verbose: bool = True):
        """Remove all generated files associated with the basis set, as read from
        generated_files.json"""
        # read generated_files.json if it exists
        generated_files = self.out.generated_files

        if verbose:
            print("Cleaning generated files:")

        if generated_files is None:
            if verbose:
                print("- No generated files to remove")
                print()
            return

        files = generated_files.get("all", [])
        for file in files:
            path = self.bset_dir / file
            if path.exists():
                if verbose:
                    print(f"- Removing {printpathstr(path)}")
                path.unlink()

        if verbose:
            print()

    def __repr__(self):
        from libcasm.xtal import pretty_json

        s = "BsetData:\n"
        s += f"- id: {self.id}\n"

        if self.meta is not None and "desc" in self.meta:
            s += f'- desc: {pretty_json(self.meta["desc"]).strip()}\n'

        if self.clex_basis_specs is None:
            s += "- (No basis set specifications)"
            return s

        clexulator = self.make_clexulator()
        if clexulator is None:
            s += "- (No Clexulator, requires `update`)"
            return s
        n_functions = clexulator.n_functions()

        variables = self.out.variables
        variables_needed = variables.get("orbit_bfuncs_variables_needed", {})
        nbor_needed = set()
        for key, value in variables_needed.items():
            for component_index, nbor_index, sublattice_index in value:
                if nbor_index is not None:
                    nbor_needed.add(nbor_index)
        n_update_neighborhood_sites = len(
            variables.get("complete_neighborhood", {}).get("sites", None)
        )

        s += f"- n_functions: {n_functions}\n"
        s += f"- n_sites: {len(nbor_needed)}\n"  # sites involved in eval orbit funcs
        if len(variables_needed) == 0:  # vars involved in eval orbit funcs
            s += "- n_variables: (none)\n"
        else:
            s += "- n_variables: \n"
            for key in variables_needed:
                s += f"  - {key}: {len(variables_needed[key])}\n"

        s += f"- n_update_neighborhood_sites: {n_update_neighborhood_sites}\n"

        return s.strip()

    def set_bspecs(
        self,
        clex_basis_specs: ClexBasisSpecs,
    ):
        """Set :attr:`~casm.project.BsetData.clex_basis_specs`

        Parameters
        ----------
        clex_basis_specs : ClexBasisSpecs
            The ClexBasisSpecs object

        """
        self.clex_basis_specs = clex_basis_specs

    def make_bspecs(
        self,
        dofs: Optional[list[str]] = None,
        max_length: Optional[list[float]] = [],
        custom_generators: Optional[list[ClusterOrbitGenerator]] = [],
        phenomenal: Union[Cluster, OccEvent, None] = None,
        cutoff_radius: Optional[list[float]] = [],
        occ_site_basis_functions_specs: Union[str, list[dict], None] = None,
        global_max_poly_order: Optional[int] = None,
        orbit_branch_max_poly_order: Optional[dict] = None,
    ):
        """Construct :attr:`~casm.project.BsetData.clex_basis_specs`

        Parameters
        ----------
        dofs: Optional[list[str]] = None
            An list of string of dof type names that should be used to construct basis
            functions. The default value is all DoF types included in the prim.

        max_length: list[float] = []
            The maximum site-to-site distance to allow in clusters, by number of sites
            in the cluster. Example: `[0.0, 0.0, 5.0, 4.0]` specifies that pair
            clusters up to distance 5.0 and triplet clusters up to distance 4.0 should
            be included. The null cluster and point cluster values (elements 0 and 1)
            are arbitrary.

        custom_generators: list[libcasm.clusterography.ClusterOrbitGenerator] = []]
            Specifies clusters that should be uses to construct orbits regardless of the
            `max_length` or `cutoff_radius` parameters.

        phenomenal: Union[libcasm.clusterography.Cluster, libcasm.occ_events.OccEvent, \
        None] = None
            If provided, generate local cluster functions using the invariant group of
            the phenomenal cluster or event. By default, periodic cluster functions are
            generated.

        cutoff_radius: list[float] = []
            For local clusters, the maximum distance of sites from any phenomenal
            cluster site to include in the local environment, by number of sites in the
            cluster. The null cluster value (element 0) is arbitrary.

        occ_site_basis_functions_specs: Union[str, list[dict], None] = None
            Provides instructions for constructing occupation site basis functions.
            The accepted options are "chebychev", "occupation", or a `list[dict]`
            a specifying sublattice-specific choice of site basis functions. This
            parameter corresponds to the value of

            .. code-block:: Python

                "dof_specs": {
                    "occ": {
                        "site_basis_functions": ...
                    }
                }

            as described in detail in the section
            `DoF Specifications <https://prisms-center.github.io/CASMcode_pydocs/casm/bset/2.0/usage/basis_function_specs.html#dof-specifications>`_
            and is required for functions of occupation DoF.

        global_max_poly_order: Optional[int] = None
            The maximum order of polynomials of continuous DoF to generate, for any
            orbit not specified more specifically by `orbit_branch_max_poly_order`.

        orbit_branch_max_poly_order: Optional[dict[int, int]] = None
            Specifies for continuous DoF the maximum polynomial order to generate by
            cluster size, according to
            ``orbit_branch_max_poly_order[cluster_size] = max_poly_order``. By default,
            for a given cluster orbit, polynomials of order up to the cluster size are
            created. Higher order polynomials are requested either according to cluster
            size using `orbit_branch_max_poly_order` or globally using
            `global_max_poly_order`. The most specific level specified is used.
        """
        self.clex_basis_specs = make_clex_basis_specs(
            prim=self.proj.prim,
            dofs=dofs,
            max_length=max_length,
            custom_generators=custom_generators,
            phenomenal=phenomenal,
            cutoff_radius=cutoff_radius,
            occ_site_basis_functions_specs=occ_site_basis_functions_specs,
            global_max_poly_order=global_max_poly_order,
            orbit_branch_max_poly_order=orbit_branch_max_poly_order,
        )

    def build(
        self,
        make_equivalents: bool = True,
        make_all_local_basis_sets: bool = True,
        verbose: bool = False,
    ) -> ClusterFunctionsBuilder:
        """Construct the cluster functions for the basis set, but do not write anything

        This uses the current basis set specifications to construct clusters and
        cluster functions. It raises if no basis set specifications exist.


        Parameters
        ----------
        make_equivalents: bool = True
            If True, make all equivalent clusters and functions. Otherwise, only
            construct and return the prototype clusters and functions on the prototype
            cluster (i.e. ``i_equiv=0`` only).

        make_all_local_basis_sets: bool = True
            If True, make local clusters and functions for all phenomenal
            clusters in the primitive cell equivalent by prim factor group symmetry.
            Requires that `make_equivalents` is True.

        verbose: bool = False
            Print progress statements

        Returns
        -------
        builder: casm.bset.cluster_functions.ClusterFunctionsBuilder
            The ClusterFunctionsBuilder data structure holds the generated cluster
            functions and associated clusters.

        """
        if self.clex_basis_specs is None:
            raise Exception(
                "Error in BsetData.make_cluster_functions: no bspecs loaded"
            )
        if self.proj.prim_neighbor_list is None:
            raise Exception(
                "Error in BsetData.make_cluster_functions: "
                "project prim_neighbor_list is None"
            )

        return build_cluster_functions(
            prim=self.proj.prim,
            clex_basis_specs=self.clex_basis_specs,
            prim_neighbor_list=self.proj.prim_neighbor_list,
            make_equivalents=make_equivalents,
            make_all_local_basis_sets=make_all_local_basis_sets,
            verbose=verbose,
        )

    def update(
        self,
        no_compile: bool = False,
        only_compile: bool = False,
        verbose: bool = True,
        very_verbose: bool = False,
    ):
        """Write the Clexulator source file(s) for the basis set, and/or compile the
        Clexulator(s)

        Data in files generated by this method can be accessed using the
        :attr:`~casm.project.BsetData.out` attribute, which is an object of
        type :class:`~casm.project.BsetOutputData`.

        Parameters
        ----------
        no_compile: bool = False
            If True, do not compile the Clexulator or LocalClexulator.
        only_compile: bool = False
            If True, only compile the Clexulator or LocalClexulator from existing
            source files, do not write the source file(s).
        verbose: bool = True
            Print progress statements
        very_verbose: bool = False
            Print detailed progress statements from the cluster functions builder.
        """
        if self.proj.prim_neighbor_list is None:
            raise Exception(
                "Error in BsetData.write_clexulator: "
                "project prim_neighbor_list is None"
            )
        if self.clex_basis_specs is None:
            raise Exception(
                "Error in BsetData.write_clexulator: "
                "no basis set specifications found"
            )
        if only_compile is False:
            self.clean(verbose=verbose)

            if verbose:
                start = time.time()
                print("Generating clexulator...")
                sys.stdout.flush()
            write_clexulator(
                prim=self.proj.prim,
                clex_basis_specs=self.clex_basis_specs,
                bset_dir=self.bset_dir,
                prim_neighbor_list=self.proj.prim_neighbor_list,
                project_name=self.proj.name,
                bset_name=self.id,
                version=self.version,
                linear_function_indices=self.linear_function_indices,
                cpp_fmt=None,
                verbose=verbose,
                very_verbose=very_verbose,
            )
            if verbose:
                print("Generated files:")
                for file in self.out.generated_files.get("all", []):
                    print(f"- {printpathstr(self.bset_dir / file)}")
                print()
                print("Generating clexulator DONE")
                elapsed_time = time.time() - start
                print(f"generation time: {elapsed_time:0.4f} (s)")
                print()
                sys.stdout.flush()

        if no_compile:
            return

        src_path = self.out.src_path
        if src_path is None:
            raise ValueError("Error in BsetData.update: No Clexulator src_path.")

        # compile Clexulator
        if self.out.local_src_path is None:
            if verbose:
                print("Compiling clexulator...")
                sys.stdout.flush()
            _ = self.make_clexulator()
            if verbose:
                print("Compiling clexulator DONE")
                sys.stdout.flush()
        else:
            if verbose:
                print("Compiling local clexulator...")
                sys.stdout.flush()
            _ = self.make_local_clexulator()
            if verbose:
                print("Compiling local clexulator DONE")
                sys.stdout.flush()

    def _update_generated_files(self, abspaths: list[pathlib.Path]):
        """Update the generated_files.json file with the given absolute paths"""
        generated_files = self.out.generated_files
        if generated_files is None:
            generated_files = {"all": []}
        relpaths = [str(p.relative_to(self.bset_dir)) for p in abspaths]
        changed = False
        for relpath in relpaths:
            if relpath not in generated_files["all"]:
                generated_files["all"].append(relpath)
                changed = True
        if changed:
            safe_dump(
                data=generated_files,
                path=self.bset_dir / "generated_files.json",
                quiet=False,
                force=True,
            )
            print()

    def make_clexulator(self) -> Optional[Clexulator]:
        """The Clexulator for the basis set, if available.

        When accessed, the Clexulator will be compiled if it has not yet been compiled,
        but it will not be written without explicitly calling
        :func:`~casm.project.Bset.update`.

        Returns
        -------
        clexulator: Optional[Clexulator]
            The Clexulator for the basis set, if available; otherwise None.
        """
        src_path = self.out.src_path
        if src_path is None:
            return None
        clexulator = make_clexulator(
            source=str(src_path),
            prim_neighbor_list=self.proj.prim_neighbor_list,
        )

        self._update_generated_files(
            abspaths=[
                self.proj.dir.clexulator_o(projectname=self.proj.name, bset=self.id),
                self.proj.dir.clexulator_so(projectname=self.proj.name, bset=self.id),
            ],
        )

        return clexulator

    def make_local_clexulator(self) -> Optional[LocalClexulator]:
        """The LocalClexulator for the basis set, if available.

        When accessed, the LocalClexulator will be compiled if it has not yet been
        compiled, but it will not be written without explicitly calling
        :func:`~casm.project.Bset.update`.

        Returns
        -------
        local_clexulator: Optional[LocalClexulator]
            The LocalClexulator for the basis set, if available; otherwise None.
        """
        local_src_path = self.out.local_src_path
        if local_src_path is None:
            return None
        local_clexulator = make_local_clexulator(
            source=str(self.out.src_path),
            prim_neighbor_list=self.proj.prim_neighbor_list,
        )

        abspaths = []
        for i_equiv, path in enumerate(local_src_path):
            abspaths += [
                self.proj.dir.clexulator_o(
                    projectname=self.proj.name, bset=self.id, i_equiv=i_equiv
                ),
                self.proj.dir.clexulator_so(
                    projectname=self.proj.name, bset=self.id, i_equiv=i_equiv
                ),
            ]

        self._update_generated_files(abspaths=abspaths)

        return local_clexulator

    def make_corr_calculator(
        self,
        linear_function_indices: Optional[list[int]] = None,
    ):
        """Return a correlations calculator for this basis set.

        Parameters
        ----------
        linear_function_indices: Optional[list[int]] = None
            If provided, only calculate the basis functions with corresponding indices.
            The same size correlation array is always returned, but other values will
            be of undefined value.

        Returns
        -------
        corr_calculator: ConfigCorrCalculator
            A correlations calculator for this basis set.
        """
        clexulator = self.make_clexulator()
        if clexulator is None:
            if self.clex_basis_specs is None:
                raise Exception("No basis.json. No basis set specifications.")
            else:
                raise Exception("No basis.json. Do you need to run update?.")

        return ConfigCorrCalculator(
            clexulator=self.make_clexulator(),
            prim_neighbor_list=self.proj.prim_neighbor_list,
            linear_function_indices=linear_function_indices,
        )

    def print_orbits(
        self,
        linear_orbit_indices: Optional[set[int]] = None,
        print_invariant_group: bool = False,
        invariant_group_coordinate_mode: str = "cart",
        site_coordinate_mode: str = "integral",
    ):
        basis_dict = self.out.basis_dict
        if basis_dict is None:
            if self.clex_basis_specs is None:
                raise Exception("No basis.json. No basis set specifications.")
            else:
                raise Exception("No basis.json. Do you need to run update?.")

        options = PrettyPrintBasisOptions()
        options.linear_orbit_indices = linear_orbit_indices
        options.print_invariant_group = print_invariant_group
        options.invariant_group_coordinate_mode = invariant_group_coordinate_mode
        options.print_prototypes = True
        options.site_coordinate_mode = site_coordinate_mode

        pretty_print_orbits(
            basis_dict=basis_dict,
            prim=self.proj.prim,
            options=options,
        )

    def print_clusters(
        self,
        linear_orbit_indices: Optional[set[int]] = None,
        print_invariant_group: bool = False,
        invariant_group_coordinate_mode: str = "cart",
        site_coordinate_mode: str = "integral",
    ):
        basis_dict = self.out.basis_dict
        if basis_dict is None:
            if self.clex_basis_specs is None:
                raise Exception("No basis.json. No basis set specifications.")
            else:
                raise Exception("No basis.json. Do you need to run update?.")

        options = PrettyPrintBasisOptions()
        options.linear_orbit_indices = linear_orbit_indices
        options.print_invariant_group = print_invariant_group
        options.invariant_group_coordinate_mode = invariant_group_coordinate_mode
        options.print_prototypes = False
        options.site_coordinate_mode = site_coordinate_mode

        pretty_print_orbits(
            basis_dict=basis_dict,
            prim=self.proj.prim,
            options=options,
        )

    def print_functions(
        self,
        linear_orbit_indices: Optional[set[int]] = None,
        print_invariant_group: bool = False,
        invariant_group_coordinate_mode: str = "cart",
        print_prototypes: bool = False,
        site_coordinate_mode: str = "integral",
    ):
        # basis_dict = self.out.basis_dict
        # if basis_dict is None:
        #     if self.clex_basis_specs is None:
        #         raise Exception("No basis.json. No basis set specifications.")
        #     else:
        #         raise Exception("No basis.json. Do you need to run update?.")

        variables = self.out.variables
        if variables is None:
            if self.clex_basis_specs is None:
                raise Exception("No variables.json.gz. No basis set specifications.")
            else:
                raise Exception("No variables.json.gz. Do you need to run update?.")
        basis_dict = self.out.basis_dict
        if basis_dict is None:
            if self.clex_basis_specs is None:
                raise Exception("No basis.json. No basis set specifications.")
            else:
                raise Exception("No basis.json. Do you need to run update?.")

        options = PrettyPrintBasisOptions()
        options.linear_orbit_indices = linear_orbit_indices
        options.print_invariant_group = print_invariant_group
        options.invariant_group_coordinate_mode = invariant_group_coordinate_mode
        options.print_prototypes = print_prototypes
        options.site_coordinate_mode = site_coordinate_mode

        pretty_print_functions(
            basis_dict=basis_dict,
            variables=variables,
            prim=self.proj.prim,
            options=options,
        )

    # TODO:
    # def display_orbits(self, ...):
    #     return None

    # TODO:
    # def display_clusters(self, ...):
    #     return None

    def display_functions(
        self,
        id: str,
        linear_orbit_indices: Optional[set[int]] = None,
    ):
        """Display cluster function formulas using IPython.display

        Parameters
        ----------
        id: str
            The basis set identifier. Must consist alphanumeric characters and
            underscores only.
        linear_orbit_indices: Optional[set[int]] = None
            Linear cluster orbit indices to print associated functions for. If None,
            functions are printed for all cluster orbits.

        """
        basis_dict = self.out.basis_dict
        if basis_dict is None:
            if self.clex_basis_specs is None:
                raise Exception("No basis.json. No basis set specifications.")
            else:
                raise Exception("No basis.json. Do you need to run update?.")

        options = DisplayBasisOptions()
        options.linear_orbit_indices = linear_orbit_indices
        options.display_invariant_group = False

        display_functions(
            basis_dict=basis_dict,
            prim=self.proj.prim,
            options=options,
        )
