import pathlib
from typing import Callable, Optional, Union

import numpy as np

import libcasm.configuration as casmconfig
import libcasm.xtal as xtal


def project_path(start: Union[str, pathlib.Path, None] = None):
    """Find the path to the enclosing CASM project directory

    Crawl up from `start` to find '.casm'. If found, returns the directory containing
    the '.casm' directory. If not found, return None.

    Parameters
    ----------
    start: Union[str, pathlib.Path, None] = None
        Starting directory. If None, uses current working directory.

    Returns
    -------
    project_path: Optional[pathlib.Path]
        If found, returns the directory above `start` with contains a '.casm'
        directory. If not found, return None.
    """
    if start is None:
        start = pathlib.Path.cwd()
    else:
        start = pathlib.Path(start).resolve()
    if not start.is_dir():
        raise Exception(f"Error in casm.project.project_path: no directory named {dir}")
    curr = start
    cont = True
    while cont is True:
        test_path = curr / ".casm"
        if test_path.is_dir():
            return curr
        elif curr == curr.parent:
            return None
        else:
            curr = curr.parent
    return None


def find_upper_tol(
    f: Callable[[float], int],
    init_tol: float = -5.0,
    max_tol: float = -2.00001,
    step: float = 1.0,
    min_step: float = 0.09,
):
    """Find the tolerance greater than `init_tol` at which a function yields a \
    different value

    Parameters
    ----------
    f: Callable[[float], int]
        Callable function of tolerance
    init_tol: float = -5.0
        Initial tolerance exponent, i.e. -5.0 means tolerance of pow(10,-0.5)
    max_tol: float = -2.00001
        Maximum tolerance exponent.
    step: float = 1.0
        Initial tolerance exponent step.
    min_step: float = 0.09
        Minimum tolerance exponent step size.

    Returns
    -------
    (upper_tol, value):

        upper_tol: float
            Tolerance exponent at which a function yields a different value

        value: int
            The value of the function using `pow(10., upper_tol)` for the tolerance
    """
    base = 10.0
    init_value = f(pow(base, init_tol))
    tol = init_tol
    while True:
        value = f(pow(base, tol + step))
        if value == init_value:
            tol += step
            if tol >= max_tol:
                break
        else:
            if step / 10.0 <= min_step:
                tol += step
                break
            else:
                step = step / 10.0
    return (tol, value)


def find_lower_tol(
    f: Callable[[float], int],
    init_tol: float = -5.0,
    min_tol: float = -9.99999,
    step: float = 1.0,
    min_step: float = 0.09,
):
    """Find the tolerance lesser than `init_tol` at which a function yields a \
    different value

    Parameters
    ----------
    f: Callable[[float], int]
        Callable function of tolerance
    init_tol: float = -5.0
        Initial tolerance exponent, i.e. -5.0 means tolerance of pow(10,-0.5)
    min_tol: float = -2.00001
        Maximum tolerance exponent.
    step: float = 1.0
        Initial tolerance exponent step.
    min_step: float = 0.09
        Minimum tolerance exponent step size.

    Returns
    -------
    (upper_tol, value):

        upper_tol: float
            Tolerance exponent at which a function yields a different value

        value: int
            The value of the function using `pow(10., upper_tol)` for the tolerance
    """
    base = 10.0
    init_value = f(pow(base, init_tol))
    tol = init_tol
    while True:
        value = f(pow(base, tol - step))
        if value == init_value:
            tol -= step
            if tol <= min_tol:
                break
        else:
            if step / 10.0 <= min_step:
                tol -= step
                break
            else:
                step = step / 10.0
    return (tol, value)


def make_lattice_with_tol(
    lattice: xtal.Lattice,
    tol: float,
):
    return xtal.Lattice(
        column_vector_matrix=lattice.column_vector_matrix(),
        tol=tol,
    )


def _as_xtal_prim(
    prim: Union[xtal.Prim, casmconfig.Prim],
) -> xtal.Prim:
    if isinstance(prim, casmconfig.Prim):
        return prim.xtal_prim
    elif isinstance(prim, xtal.Prim):
        return prim
    else:
        raise ValueError("Not a prim")


def _as_prim(
    prim: Union[xtal.Prim, casmconfig.Prim],
) -> xtal.Prim:
    if isinstance(prim, casmconfig.Prim):
        return prim
    elif isinstance(prim, xtal.Prim):
        return casmconfig.Prim(prim)
    else:
        raise ValueError("Not a prim")


def make_xtal_prim_with_tol(
    prim: Union[xtal.Prim, casmconfig.Prim],
    tol: float,
):
    xtal_prim = _as_xtal_prim(prim)
    labels = xtal_prim.labels()
    if len(labels) and labels[0] == -1:
        labels = None
    return xtal.Prim(
        lattice=xtal.Lattice(
            column_vector_matrix=xtal_prim.lattice().column_vector_matrix(), tol=tol
        ),
        coordinate_frac=xtal_prim.coordinate_frac(),
        occ_dof=xtal_prim.occ_dof(),
        local_dof=xtal_prim.local_dof(),
        global_dof=xtal_prim.global_dof(),
        occupants=xtal_prim.occupants(),
        title=xtal_prim.to_dict().get("title"),
        labels=labels,
    )


def make_prim_with_tol(
    prim: Union[xtal.Prim, casmconfig.Prim],
    tol: float,
):
    return casmconfig.Prim(xtal_prim=make_xtal_prim_with_tol(prim=prim, tol=tol))


def make_prim_with_lattice(
    prim: Union[xtal.Prim, casmconfig.Prim],
    lattice: xtal.Lattice,
):
    xtal_prim = _as_xtal_prim(prim=prim)
    labels = xtal_prim.labels()
    if len(labels) and labels[0] == -1:
        labels = None
    xtal_prim_with_lattice = xtal.Prim(
        lattice=lattice,
        coordinate_frac=xtal_prim.coordinate_frac(),
        occ_dof=xtal_prim.occ_dof(),
        local_dof=xtal_prim.local_dof(),
        global_dof=xtal_prim.global_dof(),
        occupants=xtal_prim.occupants(),
        title=xtal_prim.to_dict().get("title"),
        labels=labels,
    )
    return casmconfig.Prim(xtal_prim=xtal_prim_with_lattice)


def make_symmetrized_lattice(lattice: xtal.Lattice, tol: float):
    tol_init = lattice.tol()

    # See CASMcode_crystallography symmetrized_with_fractional
    lattice_with_tol = make_lattice_with_tol(lattice, tol)
    pg = xtal.make_point_group(lattice_with_tol)

    # get point group ops as
    frac_mat = []
    L = lattice_with_tol.column_vector_matrix()
    Linv = np.linalg.inv(L)
    for op in pg:
        frac_mat.append(np.rint(Linv @ op.matrix() @ L).astype(int))

    # symmetrize the squared lattice column vector matrix
    L_symmetrized_squared = np.zeros((3, 3))
    for M in frac_mat:
        L_symmetrized_squared += M.T @ L.T @ L @ M
    L_symmetrized_squared /= len(frac_mat)

    # get sqrt of L_symmetrized_squared, which will be misoriented
    U, S, Vh = np.linalg.svd(L_symmetrized_squared, full_matrices=True)
    L_symmetrized_misoriented = U @ np.diag(np.sqrt(S)) @ Vh

    # remove misorientation
    U, S, Vh = np.linalg.svd(L_symmetrized_misoriented @ Linv, full_matrices=True)
    L_symmetrized = Vh.T @ U.T @ L_symmetrized_misoriented

    return xtal.Lattice(
        column_vector_matrix=L_symmetrized,
        tol=tol_init,
    )


def make_symmetrized_prim(
    prim: Union[xtal.Prim, casmconfig.Prim],
    tol: float,
) -> casmconfig.Prim:
    """Returns a prim symmetrized with tolerance `tol`

    The lattice is symmetrized to the lattice point group, then each basis site is
    replaced by the average of its symmetrically equivalent positions under the
    factor group. The result is not made primitive, canonical, or right-handed. See
    :func:`~libcasm.xtal.make_canonical_prim` and
    :func:`~libcasm.xtal.make_primitive_prim` for more information on making a prim
    canonical or primitive.

    Parameters
    ----------
    prim: Union[libcasm.xtal.Prim, libcasm.configuration.Prim]
        The initial prim.
    tol: float
        The tolerance used to find the lattice point group and factor group.

    Returns
    -------
    symmetrized_prim: libcasm.configuration.Prim
        The symmetrized prim.
    """
    xtal_prim_init = _as_xtal_prim(prim=prim)
    init_tol = xtal_prim_init.lattice().tol()

    # symmetrized_lattice is symmetrized
    symmetrized_lattice = make_symmetrized_lattice(
        lattice=xtal_prim_init.lattice(), tol=tol
    )
    symmetrized_lattice_with_tol = make_lattice_with_tol(
        lattice=symmetrized_lattice,
        tol=tol,
    )

    # Make prim with symmetrized lattice, get factor group at 'tol'
    prim = make_prim_with_lattice(
        prim=xtal_prim_init,
        lattice=symmetrized_lattice_with_tol,
    )
    factor_group_at_tol = prim.factor_group

    # Going to apply `factor_group_at_tol` and find average basis site coordinates
    init_coord_cart = prim.xtal_prim.coordinate_cart()
    avg_coord_cart = init_coord_cart.copy()

    # Apply each op in `factor_group_at_tol`
    n_ops = len(factor_group_at_tol.elements)
    for op in factor_group_at_tol.elements:
        transformed_coord_cart = (
            op.matrix() @ init_coord_cart + op.translation().reshape(3, 1)
        )

        # for each coord in transformed_coord_cart,
        # find index of closest site in init_coord_cart
        n = init_coord_cart.shape[1]
        for i_transformed in range(n):
            best_disp = None  # transformed - init
            best_dist = None
            i_init_best = None
            transformed_site_coord = transformed_coord_cart[:, i_transformed]
            for i_init in range(n):
                init_site_coord = init_coord_cart[:, i_init]
                disp = xtal.min_periodic_displacement(
                    lattice=symmetrized_lattice_with_tol,
                    r1=init_site_coord,
                    r2=transformed_site_coord,
                    robust=True,
                )
                dist = np.linalg.norm(disp)
                if i_init_best is None or dist < best_dist:
                    i_init_best = i_init
                    best_disp = disp
                    best_dist = dist
            avg_coord_cart[:, i_init_best] += best_disp / n_ops

    symmetrized_lattice = make_lattice_with_tol(
        lattice=symmetrized_lattice_with_tol,
        tol=init_tol,
    )
    labels = xtal_prim_init.labels()
    if len(labels) and labels[0] == -1:
        labels = None
    return casmconfig.Prim(
        xtal.Prim(
            lattice=symmetrized_lattice,
            coordinate_frac=xtal.cartesian_to_fractional(
                lattice=symmetrized_lattice,
                coordinate_cart=avg_coord_cart,
            ),
            occ_dof=xtal_prim_init.occ_dof(),
            local_dof=xtal_prim_init.local_dof(),
            global_dof=xtal_prim_init.global_dof(),
            occupants=xtal_prim_init.occupants(),
            title=xtal_prim_init.to_dict().get("title"),
            labels=labels,
        )
    )


class _CalcLatticePointGroupSize:
    """Check if lattice point group size changes as crystallography tol changes"""

    def __init__(
        self,
        xtal_prim: xtal.Prim,
    ):
        self.xtal_prim = xtal_prim

    def __call__(self, tol: float):
        lattice_with_tol = make_lattice_with_tol(self.xtal_prim.lattice(), tol)
        return len(xtal.make_point_group(lattice_with_tol))


class _CalcFactorGroupSize:
    """Check if factor group size changes as crystallography tol changes"""

    def __init__(
        self,
        xtal_prim: xtal.Prim,
    ):
        self.xtal_prim = xtal_prim

    def __call__(self, tol: float):
        prim_with_tol = make_prim_with_tol(self.xtal_prim, tol)
        return len(prim_with_tol.factor_group.elements)


class _IsSameCanonicalLattice:
    """Check if canonical lattice changes as crystallography tol changes"""

    def __init__(
        self,
        xtal_prim: xtal.Prim,
    ):
        self.xtal_prim = xtal_prim
        self.canonical_lattice = xtal.make_canonical_lattice(self.xtal_prim.lattice())

    def __call__(self, tol: float):
        lattice_with_tol = make_lattice_with_tol(self.xtal_prim.lattice(), tol)
        canonical_lattice = xtal.make_canonical_lattice(lattice_with_tol)
        return np.allclose(
            self.canonical_lattice.column_vector_matrix(),
            canonical_lattice.column_vector_matrix(),
            atol=tol,
        )


class PrimToleranceSensitivity:
    def __init__(
        self,
        xtal_prim: xtal.Prim,
    ):
        self.lattice_point_group_size_sensitivity = None
        self.lattice_point_group_size_sensitivity_msg = None
        self.factor_group_size_sensitivity = None
        self.factor_group_size_sensitivity_msg = None
        self.canonical_lattice_sensitivity = None
        self.canonical_lattice_sensitivity_msg = None
        self.is_sensitive = False
        self.symmetrize_tol = None

        # range for tolerance sensitivity
        upper_range = -3.0  # tolerance 1e-3
        lower_range = -7.0  # tolerance 1e-7
        is_sensitive = False
        symmetrize_tol = -5.0  # tolerance 1e-5
        base = 10.0

        init_tol = -5.0

        # Check lattice point group size sensitivity
        calc_lattice_pg = _CalcLatticePointGroupSize(xtal_prim)
        default_tol = pow(base, init_tol)
        value_at_default = calc_lattice_pg(default_tol)
        tol_upper, value_upper = find_upper_tol(
            f=calc_lattice_pg, init_tol=init_tol, step=1.0, min_step=0.09
        )
        tol_lower, value_lower = find_lower_tol(
            f=calc_lattice_pg, init_tol=init_tol, step=1.0, min_step=0.09
        )
        self.lattice_point_group_size_sensitivity = [
            (tol_lower, value_lower),
            (init_tol, value_at_default),
            (tol_upper, value_upper),
        ]

        if tol_upper < upper_range or tol_lower > lower_range:
            msg = "--- !! Lattice point group size is tolerance sensitive !! ---\n"
            msg += (
                "- Tolerance sensitivity may cause CASM to fail to properly \n"
                "  standardize and compare objects.\n"
            )
            if tol_upper < upper_range:
                msg += (
                    f"- At tol={pow(base,tol_upper)} "
                    f"lattice point group size = {value_upper}\n"
                )
                if tol_upper > symmetrize_tol:
                    symmetrize_tol = tol_upper

            msg += (
                f"- At tol={default_tol} "
                f"lattice point group size = {value_at_default}\n"
            )

            if tol_lower > lower_range:
                msg += (
                    f"- At tol={pow(base,tol_lower)} "
                    f"lattice point group size = {value_lower}\n"
                )

            self.lattice_point_group_size_sensitivity_msg = msg
            is_sensitive = True

        # Check factor group size sensitivity
        calc_fg = _CalcFactorGroupSize(xtal_prim)
        default_tol = pow(base, init_tol)
        value_at_default = calc_fg(default_tol)
        tol_upper, value_upper = find_upper_tol(
            f=calc_fg, init_tol=-5.0, step=1.0, min_step=0.09
        )
        tol_lower, value_lower = find_lower_tol(
            f=calc_fg, init_tol=-5.0, step=1.0, min_step=0.09
        )
        self.factor_group_size_sensitivity = [
            (tol_lower, value_lower),
            (default_tol, value_at_default),
            (tol_upper, value_upper),
        ]

        if tol_upper < upper_range or tol_lower > lower_range:
            msg = "--- !! Factor group size is tolerance sensitive !! ---\n"
            msg += (
                "- Tolerance sensitivity may cause CASM to fail to properly \n"
                "  standardize and compare objects.\n"
            )
            if tol_upper < upper_range:
                msg += (
                    f"- At tol={pow(base,tol_upper)} "
                    f"factor group size = {value_upper}\n"
                )
                if tol_upper > symmetrize_tol:
                    symmetrize_tol = tol_upper

            msg += f"- At tol={default_tol} factor group size = {value_at_default}\n"

            if tol_lower > lower_range:
                msg += (
                    f"- At tol={pow(base,tol_lower)} "
                    f"factor group size = {value_lower}\n"
                )

            self.factor_group_size_sensitivity_msg = msg
            is_sensitive = True

        # Check canonical lattice sensitivity
        check_lattice = _IsSameCanonicalLattice(xtal_prim)
        default_tol = pow(base, init_tol)
        value_at_default = calc_fg(default_tol)
        tol_upper, value_upper = find_upper_tol(
            f=check_lattice, init_tol=-5.0, step=1.0, min_step=0.09
        )
        tol_lower, value_lower = find_lower_tol(
            f=check_lattice, init_tol=-5.0, step=1.0, min_step=0.09
        )
        self.canonical_lattice_sensitivity = [
            (tol_lower, value_lower),
            (default_tol, value_at_default),
            (tol_upper, value_upper),
        ]

        if tol_upper < upper_range or tol_lower > lower_range:
            msg = "--- !! Canonical lattice is tolerance sensitive !! ---\n"
            msg += (
                "- Tolerance sensitivity may cause CASM to fail to properly \n"
                "  standardize and compare objects.\n"
            )
            if tol_upper < upper_range:
                msg += (
                    f"- At tol={pow(base,tol_upper)} "
                    "the canonical lattice is different\n"
                )
                if tol_upper > symmetrize_tol:
                    symmetrize_tol = tol_upper
            if tol_lower > lower_range:
                msg += (
                    f"- At tol={pow(base,tol_lower)} "
                    "the canonical lattice is different\n"
                )
            self.canonical_lattice_sensitivity_msg = msg
            is_sensitive = True

        if is_sensitive:
            self.symmetrize_tol = pow(base, symmetrize_tol)
            self.is_sensitive = is_sensitive


def get_dof_types(
    xtal_prim: xtal.Prim,
) -> tuple[list[str], list[str], list[str]]:
    """Given a prim, get lists of DoF types

    Parameters
    ----------
    xtal_prim: xtal.Prim
        The Prim

    Returns
    -------
    (global_dof, local_continuous_dof, local_discrete_dof):

        global_dof: list[str]
            The types of global degree of freedom (DoF). All global DoF are treated
            as continuous.

        local_continuous_dof: list[str]
            The types of local discrete degree of freedom (DoF).

        local_discrete_dof: list[str]
            The types of local discrete degree of freedom (DoF).

    """
    all_global_dof = set()
    for _global_dof in xtal_prim.global_dof():
        all_global_dof.add(_global_dof.dofname())

    all_local_continuous_dof = set()
    for _sublattice_dof in xtal_prim.local_dof():
        for _local_dof in _sublattice_dof:
            all_local_continuous_dof.add(_local_dof.dofname())

    # TODO: support other local discrete dof
    all_local_discrete_dof = set()
    for _occ_dof in xtal_prim.occ_dof():
        if len(_occ_dof) > 1:
            all_local_discrete_dof.add("occ")

    global_dof = list(all_global_dof)
    local_continuous_dof = list(all_local_continuous_dof)
    local_discrete_dof = list(all_local_discrete_dof)

    return (global_dof, local_continuous_dof, local_discrete_dof)


def get_generic_dof_types(
    xtal_prim: xtal.Prim,
    generic_types: Optional[list[str]] = None,
) -> list[str]:
    """Given a prim, get the generic DoF types (without flavors)

    Parameters
    ----------
    xtal_prim: xtal.Prim
        The Prim

    Returns
    -------
    generic_dof: list[str]
        The generic DoF types, i.e. "strain" instead of "Hstrain", and "magspin" instead
        of "Cmagspin".

    """
    if generic_types is None:
        generic_types = [
            "strain",
            "magspin",
        ]

    def _make_generic(dof: str) -> bool:
        for generic_type in generic_types:
            if dof.endswith(generic_type):
                return generic_type
        return dof

    global_dof, local_continuous_dof, local_discrete_dof = get_dof_types(
        xtal_prim=xtal_prim
    )

    generic_dof = set()
    for dof in global_dof + local_continuous_dof + local_discrete_dof:
        generic_dof.add(_make_generic(dof))

    return sorted(list(generic_dof))


def print_asymmetric_units(prim: Union[xtal.Prim, casmconfig.Prim]):
    """Print the asymmetric units for a prim.


    Given a prim, print the asymmetric units
    and the occupation degrees of freedom on
    each site. Each asymmetric unit is a group
    of equivalent sites for the configurational
    cluster expansion.

    Parameters
    ----------
    prim: Union[xtal.Prim, casmconfig.Prim]
        The prim to print.
    """
    xtal_prim = _as_xtal_prim(prim=prim)
    asymmetric_unit_indices = xtal.asymmetric_unit_indices(xtal_prim)
    occ_dof = xtal_prim.occ_dof()
    for asym_index, asym_unit in enumerate(asymmetric_unit_indices):
        print(f"Asymmetric Unit: {asym_index}")
        for site in asym_unit:
            print(f"Sublattice {site}: Occupants={occ_dof[site]}")
