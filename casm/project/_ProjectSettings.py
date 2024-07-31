import re

import numpy as np

import libcasm.casmglobal as casmglobal
import libcasm.xtal as xtal
from libcasm.clexulator import PrimNeighborList

from ._ClexDescription import ClexDescription


class ProjectSettings(object):
    """CASM project settings"""

    def __init__(
        self,
        data: dict,
    ):
        """
        .. rubric:: Constructor

        Parameters
        ----------
        data: dict
            Project settings as a dictionary.
        """

        self.cluster_expansions = data.get("cluster_expansions", {})
        """dict[str, ClexDescription]: Named cluster expansions
        
        The named cluster expansions make it easier to select the choice of 
        basis set, calculation settings, reference, and ECI fit used to predict 
        a particular property, and to switch and compare among multiple possible 
        choices stored in a single CASM project.

        A single cluster expansion includes the choice of values for 
        `<property>`, `<calctyp>`, `<ref>`, `<bset>`, and `<eci>` used to read 
        data from project directories.
        """

        self.crystallography_tol = data.get("crystallography_tol", casmglobal.TOL)
        """float: Tolerance used for crystallographic comparisons. Default=1e-5."""

        self.default_clex_name = self._get_default_clex_name(data)
        """Optional[str]: Name of the default cluster expansion to use when not \
        otherwise specified. 
        
        A key in cluster_expansions. If not present, `"formation_energy"` is used. 
        If that is also not present, then the first found is used. If None are
        present, then it is set to None.
        """

        self.default_clex = self._get_default_clex(data)
        """Optional[ClexDescription]: Default cluster expansion to use when not \
        otherwise specified. 

        A value in cluster_expansions, with key equal to `default_clex_name`, if 
        present.
        """

        self.lin_alg_tol = data.get("lin_alg_tol", 1e-10)
        """float: Linear algebra tolerance. Default=1e-10.
         
         A tolerance used by some methods when a stricter tolerance is needed for 
         linear algebra, such as identifying the rank of a space.
         """

        self.name = data.get("name")
        """str: Project name
        
        Typically read from “title” in `prim.json` when a project is initialized.
        """

        self.nlist_sublat_indices = data.get("nlist_sublat_indices")
        """list[int]: Indices of sublattices included in the neighbor list. 
        
        Typically determined from the prim and does not need to be modified. If 
        for some reason it is modified, all basis set source code must be 
        regenerated.
        """

        self.nlist_weight_matrix = np.array(
            data.get("nlist_weight_matrix"), dtype="int"
        )
        """numpy.ndarray[numpy.int[3,3]]: Used in determining the order of \
        unit cells in the neighbor list. 
        
        The default value is determined from the prim lattice vectors. Typically 
        does not need to be modified. If for some reason it is modified, all basis 
        set source code must be regenerated.
        """

        self.query_alias = data.get("query_alias")
        """dict: Stores casm query aliases.
        
        Example:
        
        .. code-block:: python
        
            "query_alias" : {
              "Configuration" : {
                "is_dilute_O" : "and(lt(comp_n(O),0.01001),gt(comp_n(O),0.00001))",
              },
              "Supercell" : {
                "is_vol_4" : "eq(scel_size,4)"
              }
            }
        
        """

        self.required_properties = data.get("required_properties")
        """dict: List of properties required for a particular `<calctype>` to be \
        complete
        
        .. code-block:: Python
        
            "required_properties" : {
              "Configuration" : {
                "default" : [ "energy" ],
                "lda": [ "energy" ]
              }
            }
        
        """

        self.view_command = data.get("view_command")
        """str: CASM view command
        
        Command to support viewing POSCAR representations of configurations directly 
        from the casm view command.
        """

        self.strain_references = data.get("strain_references", {})
        """dict[str, ]: Named strain references
        
        The named strain references make it easier to select the choice of 
        reference lattice used for calculating strains and to switch 
        and compare among multiple possible choices stored in a single CASM project.
        """
        self.default_strain_reference_name = self._get_default_strain_reference_name(
            data
        )
        """Optional[str]: Name of the default strain reference to use when not \
        otherwise specified. 
        
        A key in "strain_references". If not present, `"prim_lattice"` is used. 
        If that is also not present, then the first found is used. If None are
        present, then it is set to None.
        """

    def _get_default_clex_name(self, data):
        if "default_clex" in data:
            return data["default_clex"]
        elif "formation_energy" in data["cluster_expansions"]:
            return "formation_energy"
        else:
            for key, value in data["cluster_expansions"].items():
                return key
        return None

    def _get_default_clex(self, data):
        clexname = self._get_default_clex_name(data)
        if clexname is None:
            return None
        return ClexDescription(**data["cluster_expansions"][clexname])

    def _get_default_strain_reference_name(self, data):
        if "default_strain_reference_name" in data:
            return data["default_strain_reference_name"]
        elif "prim_lattice" in data["strain_references"]:
            return "prim_lattice"
        else:
            for key, _ in data["strain_references"].items():
                return key
        return None

    @staticmethod
    def make_default(
        xtal_prim: xtal.Prim,
        name: str = None,
    ):
        """Create default ProjectSettings for a new CASM project

        Parameters
        ----------
        xtal_prim : xtal.Prim
            The prim.
        name: str = None
            Project name. If not provided, uses `xtal_prim.title()`. Must consist of
            alphanumeric characters and underscores only. The first character may not
            be a number.
        """
        if name is None:
            name = xtal_prim.to_dict().get("title", "")
        pattern = R"^[a-zA-Z_]+\w*"
        if not re.match(
            pattern,
            name,
        ):
            raise Exception(
                f"Project name '{name}' is not valid: ",
                "Must consist alphanumeric characters and underscores only. "
                "The first character may not be a number.",
            )
        nlist_sublat_indices = PrimNeighborList.default_sublattice_indices(
            xtal_prim=xtal_prim,
        )
        nlist_weight_matrix = PrimNeighborList.default_lattice_weight_matrix(
            xtal_prim=xtal_prim,
        )
        data = {
            "cluster_expansions": {
                "formation_energy": {
                    "bset": "default",
                    "calctype": "default",
                    "eci": "default",
                    "name": "formation_energy",
                    "property": "formation_energy",
                    "ref": "default",
                }
            },
            "crystallography_tol": casmglobal.TOL,
            "default_clex": "formation_energy",
            "lin_alg_tol": 1e-10,
            "name": name,
            "nlist_sublat_indices": nlist_sublat_indices,
            "nlist_weight_matrix": nlist_weight_matrix.tolist(),
            "query_alias": {},
            "required_properties": {"Configuration": {"default": ["energy"]}},
            "view_command": "",
            "strain_references": {
                "prim_lattice": {
                    "lattice_vectors": xtal_prim.lattice()
                    .column_vector_matrix()
                    .T.tolist()  # note the transpose. Each row will be one lattice vector
                }
            },
            "default_strain_reference": "prim_lattice",
        }
        return ProjectSettings(data=data)

    @staticmethod
    def from_dict(data: dict):
        return ProjectSettings(data=data)

    def to_dict(self):
        return {
            "cluster_expansions": self.cluster_expansions,
            "crystallography_tol": self.crystallography_tol,
            "default_clex": self.default_clex_name,
            "lin_alg_tol": self.lin_alg_tol,
            "name": self.name,
            "nlist_sublat_indices": self.nlist_sublat_indices,
            "nlist_weight_matrix": self.nlist_weight_matrix.tolist(),
            "query_alias": self.query_alias,
            "required_properties": self.required_properties,
            "view_command": self.view_command,
            "strain_references": self.strain_references,
        }
