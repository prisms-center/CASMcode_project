import numpy as np
import libcasm.xtal as xtal
from typing import Optional
from casm.project._Project import Project
from casm.project.json_io import (
    read_required,
    safe_dump,
)


class SymCommand:
    """Methods to analyse and print symmetry information"""

    def __init__(self, proj: Project):
        self.proj = proj

    def print_lattice_point_group(
        self,
        brief: bool = True,
        coord: str = "frac",
    ):
        """Print the lattice point group"""
        lattice_point_group = [
            op.to_dict()
            for op in xtal.make_point_group(self.proj.prim.xtal_prim.lattice())
        ]
        print("Printing lattice point group: ")
        print(xtal.pretty_json(lattice_point_group))

    def print_factor_group(
        self,
        brief: bool = True,
        coord: str = "frac",
    ):
        """Print the prim factor group"""
        factor_group = [
            op.to_dict() for op in xtal.make_factor_group(self.proj.prim.xtal_prim)
        ]
        print("Printing factor group: ")
        print(xtal.pretty_json(factor_group))

    def print_crystal_point_group(
        self,
        brief: bool = True,
        coord: str = "frac",
    ):
        """Print the crystal point group"""
        crystal_point_group = [
            op.to_dict()
            for op in xtal.make_crystal_point_group(self.proj.prim.xtal_prim)
        ]
        print("Printing crystal point group: ")
        print(xtal.pretty_json(crystal_point_group))

    def dof_space_analysis(
        self,
    ):
        print("dof_space_analysis")
        return None

    def config_space_analysis(
        self,
    ):
        print("config_space_analysis")
        return None
