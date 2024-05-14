import numpy as np
import libcasm.xtal as xtal
from casm.project._Project import Project
from casm.project.json_io import (
    safe_dump,
)


def pretty_print_sym_ops(sym_group: list[dict], display_precision=5):
    """Given a list of symmetry operations represented as dicts,
    prints each symmetry operation with Matrix, Translation
    and Time reversal in a pretty way using the np.printoptions

    Uses np.printoptions to set display_precision for floats

    Parameters
    ----------
    sym_group : list[dict]
        Symmetry operations as a list of dictionaries
    display_precision : int, optional
        Uses this value to set precision of np.printoption
        (default = 5)

    Returns
    -------
    None

    """
    for op_index, op in enumerate(sym_group):
        print("Symmetry operation ", op_index)
        with np.printoptions(suppress=True, precision=display_precision):
            print("Matrix:\n", np.array(op["matrix"]))
            print("Translation:\n", np.array(op["tau"]))
        print("Time reversal:\n", op["time_reversal"])
        print("------------")


class SymCommand:
    """Methods to analyse and print symmetry information"""

    def __init__(self, proj: Project):
        self.proj = proj

    def print_lattice_point_group(
        self,
        outfilename: str = "lattice_point_group.json",
        brief: bool = True,
    ) -> None:
        """Writes the lattice point group to `outfilename`
        If `brief` is `False` also prints the lattice point
        group to the terminal

        Parameters
        ----------
        outfilename : str, optional
            Writes the lattice group as a json file
            (default = `lattice_point_group.json`)

        brief : bool, optional
            If `brief` is set to `False`, the lattice point
            group is printed to the terminal
            (default = `True`)

        Returns
        -------
        None

        """
        lattice_point_group = [
            op.to_dict()
            for op in xtal.make_point_group(self.proj.prim.xtal_prim.lattice())
        ]
        if brief == False:
            print("Printing lattice point group: ")
            pretty_print_sym_ops(lattice_point_group)
            safe_dump(lattice_point_group, outfilename)
        else:
            safe_dump(lattice_point_group, outfilename)

    def print_factor_group(
        self, brief: bool = True, outfilename="factor_group.json"
    ) -> None:
        """Writes the factor group to `outfilename`
        If `brief` is `False` also prints the factor
        group to the terminal

        Parameters
        ----------
        outfilename : str, optional
            Writes the factor group a json file
            (default = `factor_group.json`)

        brief : bool, optional
            If `brief` is set to `False`, the factor
            group is printed to the terminal
            (default = `True`)

        Returns
        -------
        None

        """
        factor_group = [
            op.to_dict() for op in xtal.make_factor_group(self.proj.prim.xtal_prim)
        ]
        if brief == False:
            print("Printing factor group: ")
            pretty_print_sym_ops(factor_group)
            safe_dump(factor_group, outfilename)
        else:
            safe_dump(factor_group, outfilename)

    def print_crystal_point_group(
        self, brief: bool = True, outfilename="crystal_point_group.json"
    ) -> None:
        """Writes the crystal point group to `outfilename`
        If `brief` is `False` also prints the crystal point
        group to the terminal

        Parameters
        ----------
        outfilename : str, optional
            Writes the crystal point group a json file
            (default = `crystal_point_group.json`)

        brief : bool, optional
            If `brief` is set to `False`, the crystal
            point group is printed to the terminal
            (default = `True`)

        Returns
        -------
        None

        """
        crystal_point_group = [
            op.to_dict()
            for op in xtal.make_crystal_point_group(self.proj.prim.xtal_prim)
        ]
        if brief == False:
            print("Printing crystal point group: ")
            pretty_print_sym_ops(crystal_point_group)
            safe_dump(crystal_point_group, outfilename)
        else:
            safe_dump(crystal_point_group, outfilename)

    def dof_space_analysis(
        self,
    ) -> None:
        print("dof_space_analysis")
        NotImplementedError("Not implemented yet!")

    def config_space_analysis(
        self,
    ):
        print("config_space_analysis")
        NotImplementedError("Not implemented yet!")
