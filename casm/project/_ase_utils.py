import ase
import ase.io
import libcasm.xtal as xtal


# Conversion function from ase.Atoms to libcasm.xtal.Structure
def casm_structure_to_ase_atoms(casm_structure: xtal.Structure) -> ase.Atoms:
    """Given `xtal.Structure`, convert it to `xtal.Structure`

    Parameters
    ----------
    casm_structure : xtal.Structure

    Returns
    -------
    ase.Atoms

    """
    if len(casm_structure.mol_type()):
        raise ValueError(
            "Error: only atomic structures may be converted using " "make_ase_atoms"
        )

    symbols = casm_structure.atom_type()
    positions = casm_structure.atom_coordinate_cart().transpose()
    cell = casm_structure.lattice().column_vector_matrix().transpose()

    return ase.Atoms(
        symbols=symbols,
        positions=positions,
        cell=cell,
        pbc=True,
    )


# Conversion function from ase.Atoms to libcasm.xtal.Structure
def ase_atoms_to_casm_structure(ase_atoms: ase.Atoms) -> xtal.Structure:
    """Given `ase.Atoms`, convert it to `xtal.Structure`

    Parameters
    ----------
    ase_atoms : ase.Atoms

    Returns
    -------
    xtal.Structure

    """

    lattice = xtal.Lattice(
        column_vector_matrix=ase_atoms.get_cell().transpose(),
    )
    atom_coordinate_frac = ase_atoms.get_scaled_positions().transpose()
    atom_type = ase_atoms.get_chemical_symbols()

    return xtal.Structure(
        lattice=lattice,
        atom_coordinate_frac=atom_coordinate_frac,
        atom_type=atom_type,
    )
