import sys
from typing import Optional, TextIO

import libcasm.configuration as casmconfig


class DisplayBasisOptions:
    """Options for displaying a basis set with IPython"""

    def __init__(
        self,
        linear_function_indices: Optional[set[int]] = None,
        linear_orbit_indices: Optional[set[int]] = None,
        max_terms_per_line: int = 3,
        function_type: str = "orbit",
        basis_site_index: Optional[int] = None,
        print_cluster_info: bool = False,
        site_coordinate_mode: str = "integral",
        multiple: bool = True,
    ):
        """

        .. rubric:: Constructor

        Parameters
        ----------
        linear_function_indices: Optional[set[int]] = None
            Linear basis function indices to display. If None, all functions are
            displayed.
        linear_orbit_indices: Optional[set[int]] = None
            Linear cluster orbit indices to display. If None, all orbits are displayed.
        max_terms_per_line: int = 3
            Maximum number of terms per line when displaying cluster functions.
        function_type: str = "orbit"
            Type of functions to print. Options are:

            - "prototype": Print the equivalent cluster basis
              functions that are associated with the prototype cluster only. Variables
              are indexed using neighbor list indices.
            - "prototype_with_cluster_indices": Print the equivalent cluster basis
              functions that are associated with the prototype cluster only. Variables
              are indexed using indices into sites in the prototype cluster.
            - "orbit": Print equivalent cluster basis functions on all clusters in an
              orbit, for the contribution associated with the origin unit cell.
              Variables are indexed using neighbor list indices.
            - "site": Print equivalent cluster basis functions for all cluster
              functions that include a particular site. Variables are indexed using
              neighbor list indices. The site is specified by `basis_site_index`.
            - "occ_delta_site": Print equivalent cluster basis functions for all cluster
              functions that include a particular site. Variables are indexed using
              neighbor list indices. The site is specified by `basis_site_index`.
              Functions give the change in basis function values when the occupation
              of the site is changed.

        basis_site_index: Optional[int] = None
            If `function_type` is "site" or "occ_delta_site", the site-centric
            functions are displayed for the `basis_site_index`-th basis site in the
            origin unit cell.
        print_cluster_info: bool = False
            If True, print functions by cluster orbit and print cluster information.
        site_coordinate_mode: str = "integral"
            Coordinate mode for printing cluster sites, if `print_cluster_info` is True.
            Options are:

            - 'integral': Use :class:`~libcasm.xtal.IntegralSiteCoordinate`
              ([b, i, j, k])
            - 'cart': Use Cartesian coordinates
            - 'frac': Use fractional coordinates, with respect to the Prim lattice
              vectors
        multiple: bool = True
            If True, display all functions together in one `{align}` environment.
            If False, display each function in its own `{align}` environment,
            as a separate output. Set False if math output is too large to display.

        """
        self.linear_function_indices = linear_function_indices
        """Optional[set[int]]: Linear function indices to display. If None, all 
        functions are displayed."""

        self.linear_orbit_indices = linear_orbit_indices
        """Optional[set[int]]: Linear cluster orbit indices to display. If None, all 
        orbits are displayed."""

        self.max_terms_per_line = max_terms_per_line
        """int: Maximum number of terms per line when displaying cluster functions."""

        self.function_type = function_type
        """str: Type of functions to print. 
        
        Options are:

        - "prototype": Print the equivalent cluster basis
          functions that are associated with the prototype cluster only. Variables
          are indexed using neighbor list indices.
        - "prototype_with_cluster_indices": Print the equivalent cluster basis
          functions that are associated with the prototype cluster only. Variables
          are indexed using indices into sites in the prototype cluster.
        - "orbit": Print equivalent cluster basis functions on all clusters in an
          orbit, for the contribution associated with the origin unit cell.
          Variables are indexed using neighbor list indices.
        - "site": Print equivalent cluster basis functions for all cluster
          functions that include a particular site. Variables are indexed using
          neighbor list indices. The site is specified by `basis_site_index`.
        - "occ_delta_site": Print equivalent cluster basis functions for all cluster
          functions that include a particular site. Variables are indexed using
          neighbor list indices. The site is specified by `basis_site_index`.
          Functions give the change in basis function values when the occupation
          of the site is changed.

        """

        self.basis_site_index = basis_site_index
        """Optional[int]: If `function_type` is "site", the site-centric functions are
        displayed for the `basis_site_index`-th basis site in the origin unit cell."""

        self.print_cluster_info = print_cluster_info
        """bool: If True, print functions by cluster orbit and print cluster
        information."""

        self.site_coordinate_mode = site_coordinate_mode
        """str: Coordinate mode for printing cluster sites.

        Options are:

        - 'integral': Use :class:`~libcasm.xtal.IntegralSiteCoordinate`
          ([b, i, j, k])
        - 'cart': Use Cartesian coordinates
        - 'frac': Use fractional coordinates, with respect to the Prim lattice
          vectors
        """

        self.multiple = multiple
        """bool: If True, display all functions together in one `{align}`
        environment. If False, display each function in its own `{align}`
        environment, as a separate output. Set False if math output is too
        large to display."""


def display_orbits(
    basis_dict: dict,
    prim: casmconfig.Prim,
    options: Optional[DisplayBasisOptions] = None,
    out: Optional[TextIO] = None,
):
    # TODO
    raise Exception("display_orbits: TODO, not implemented yet")
    return None


def display_occ_site_functions(
    site_functions_dict: dict,
    prim: casmconfig.Prim,
):
    """Pretty print information about occupation site basis functions

    - Prints nothing if no occupation site basis functions found

    Parameters
    ----------
    site_functions_dict: dict
        A description of the site_functions, from the contents of a `basis.json`
        file.
    prim: casmconfig.Prim
        The prim.
    """
    from IPython.display import Markdown, display

    has_occ_site_functions = False
    for sublat_func in site_functions_dict:
        if "occ" in sublat_func:
            has_occ_site_functions = True
            break
    if not has_occ_site_functions:
        return

    s = "Occupation site functions: \n"
    s += R"\phi_{b,f}(s_l)" + "\n"
    s += R"- \phi_{i_sublattice, i_function}: {[value1, ...]}" + "\n"
    occ_dof = prim.xtal_prim.occ_dof()
    for sublat_func in site_functions_dict:
        b = sublat_func.get("sublat")

        # sublat header, ex: - sublattice: 0, occ_dof: [Si, Ge]
        s += f"- sublattice: {b}, occ_dof: [" + ", ".join(occ_dof[b]) + "]" + "\n"

        # each occ site basis function:
        if "occ" in sublat_func:
            s += R"\begin{split}" + "\n"
            value = sublat_func.get("occ").get("value")
            first = True
            for i_function, function_values in enumerate(value):
                if not first:
                    s += R"\\" + "\n"
                s += f"\\phi_{{{b}, {i_function}}} &= {function_values}" + "\n"
                first = False
            s += "\n"
            s += R"\end{split}"

    display(Markdown(s))


def display_occ_site_functions_v2(
    occ_site_functions: list[dict],
    occ_site_functions_info: dict,
    prim: casmconfig.Prim,
):
    """Pretty print information about occupation site basis functions

    - Prints nothing if no occupation site basis functions found

    Parameters
    ----------
    occ_site_functions: list[dict]
        List of occupation site basis functions. For each sublattice with discrete
        site basis functions, includes:

        - `"sublattice_index"`: int, index of the sublattice
        - `"n_occupants"`: int, number of allowed occupants
        - `"value"`: list[list[float]], list of the site basis function values,
          as ``value[function_index][occupant_index]``
        - `"constant_function_index"`: int, index of the constant site basis function

    occ_site_functions_info: dict
        Information about occupation site basis functions, with format:

        - `"max_function_index"`: int, The maximum site function index, across all
            sublattices.
        - `"all_sublattices_have_same_site_functions"`: bool, True if all _sublattices
            have same site functions; False otherwise.
        - `"occ_var_name"`: str, A variable name template for the site functions,
            which may be formated using `b` for sublattice index and `m` for site
            function index (i..e ``occ_var_name.format(b=0, m=1)``).
        - `"occ_var_desc"`: str, A description of the occupation
            variable, including a description of the subscript indices.
        - `"occ_var_indices"`: list[list[str, str]], A list of lists, where each sublist
          contains the variable name and description for each subscript index.


    prim: casmconfig.Prim
        The prim.
    """
    import numpy as np
    from IPython.display import Markdown, display

    if len(occ_site_functions) == 0:
        return

    occ_var_name = occ_site_functions_info.get("occ_var_name")
    occ_var_desc = occ_site_functions_info.get("occ_var_desc")

    s = f"Occupation site functions, {occ_var_desc}:\n"

    # s += R"\phi_{b,f}(s_l)" + "\n"
    # s += R"- \phi_{i_sublattice, i_function}: {[value1, ...]}" + "\n"
    occ_dof = prim.xtal_prim.occ_dof()
    for sublat_func in occ_site_functions:
        b = sublat_func.get("sublattice_index")

        # sublat header, ex: - sublattice: 0, occ_dof: [Si, Ge]
        s += f"- sublattice: {b}, occ_dof: [" + ", ".join(occ_dof[b]) + "]" + "\n"

        # each occ site basis function:
        for m, value in enumerate(sublat_func.get("value")):
            if (np.array(value) == 1.0).all():
                continue
            s += (
                "  - $"
                + occ_var_name.format(b=b, m=m)
                + " = ["
                + ", ".join([f"{x:.8f}" for x in value])
                + "]$\n"
            )

        s += "\n"

    display(Markdown(s))


def display_functions(
    basis_dict: dict,
    prim: casmconfig.Prim,
    options: Optional[DisplayBasisOptions] = None,
    out: Optional[TextIO] = None,
):
    """Display cluster function formulas using IPython.display

    Parameters
    ----------
    basis_dict: dict
        A description of a cluster expansion basis set, the contents of a `basis.json`
        file.
    prim: casmconfig.Prim
        The prim.
    options: Optional[DisplayBasisOptions] = None
        Options for pretty-printing the basis set. If None, default options are used.
    out: Optional[stream] = None
        Output stream. Defaults to `sys.stdout`.

    """
    import IPython.display
    import latex2mathml.converter

    if out is None:
        out = sys.stdout
    if options is None:
        options = DisplayBasisOptions()

    # prints nothing if no occupation site basis functions are found
    display_occ_site_functions(
        site_functions_dict=basis_dict.get("site_functions"),
        prim=prim,
        options=options,
        out=out,
    )
    print(file=out)

    for orbit in basis_dict.get("orbits"):
        linear_orbit_index = orbit.get("linear_orbit_index")
        if (
            options.linear_orbit_indices is not None
            and linear_orbit_index not in options.linear_orbit_indices
        ):
            continue
        print(
            f"Orbit {orbit.get('linear_orbit_index')}: mult={orbit.get('mult')}",
            file=out,
        )
        # functions
        s = R"\begin{split}" + "\n"
        first = True
        functions = orbit.get("cluster_functions")
        for func in functions:
            if not first:
                s += R"\\" + "\n"
            linear_function_index = func.get("linear_function_index")
            key = R"\Phi_{" + str(linear_function_index) + "}"
            latex_formula = func.get(key)
            s += f"{key} = {latex_formula}"
            first = False
        s += "\n"
        s += R"\end{split}"
        IPython.display.display(IPython.display.HTML(latex2mathml.converter.convert(s)))
        print(file=out)


def enforce_max_terms_per_line(
    latex_formula: str,
    max_terms_per_line: int,
) -> str:
    """Enforce a maximum number of terms per line in a LaTeX formula

    Parameters
    ----------
    latex_formula: str
        The LaTeX formula.
    max_terms_per_line: int
        Maximum number of terms per line.

    Returns
    -------
    str
        The LaTeX formula with the maximum number of terms per line enforced.
    """
    final = str()

    # Iterate over each term in the formula (terms are separated by ' + ')
    # If the number of terms per line is reached:
    # - add "\\" at the end of the line (if not the last line)
    # - begin the next line with "&\quad +\ " instead of " + "

    terms = latex_formula.split(" + ")

    count = 1
    for term in terms:
        final += term
        if count == len(terms):
            break
        if count % max_terms_per_line == 0:
            final += R" & \\ &\quad +\ "
        else:
            final += " + "
        count += 1
    final += " &"
    return final


def display_functions_v2(
    variables: dict,
    options: Optional[DisplayBasisOptions] = None,
):
    from IPython.display import Latex, display

    if options is None:
        options = DisplayBasisOptions()

    # Display multiple functions in one {align} environment
    # KaTeX (e.g. VS Code) does not support {flalign}
    s = ""
    if options.multiple:
        s = R"\begin{align}" + "\n"

    bfuncs = None
    is_site_functions = False
    if options.function_type in [
        "prototype",
        "prototype_with_cluster_indices",
        "orbit",
    ]:
        bfuncs = variables.get("orbit_bfuncs")
    elif options.function_type in [
        "site",
        "occ_delta_site",
    ]:
        bfuncs = variables.get("site_bfuncs")
        is_site_functions = True
        if options.basis_site_index is None:
            raise ValueError(
                "If function type is 'site' or 'occ_delta_site', "
                "the basis_site_index must be specified"
            )

    display_index = 1 # to number displayed functions starting from (1)
    first = True
    for data in bfuncs:
        linear_function_index = data["linear_function_index"]
        linear_orbit_index = data["linear_orbit_index"]

        if not is_site_functions:
            latex_prototype_with_cluster_indices = data["latex_prototype"]
            latex_prototype = data["latex_prototype_with_neighbor_indices"]
            latex_orbit = data["latex_orbit"]
        else:
            if len(data.get("at")) == 0:
                continue

            site_data = data.get("at")[options.basis_site_index]
            latex_site = site_data["latex"]
            occ_delta_site = site_data["occ_delta_latex"]

        if options.linear_function_indices is not None:
            if linear_function_index not in options.linear_function_indices:
                continue
        if options.linear_orbit_indices is not None:
            if linear_orbit_index not in options.linear_orbit_indices:
                continue

        if options.function_type == "prototype":
            latex_formula = latex_prototype
        elif options.function_type == "prototype_with_cluster_indices":
            latex_formula = latex_prototype_with_cluster_indices
        elif options.function_type == "orbit":
            latex_formula = latex_orbit
        elif options.function_type == "site":
            latex_formula = latex_site
        elif options.function_type == "occ_delta_site":
            latex_formula = occ_delta_site
        else:
            raise ValueError(f"Unknown function_type: {options.function_type}")

        if latex_formula is None:
            continue

        if options.multiple and not first:
            s += R"\\" + "\n"

        s += (
            R"\Phi_{"
            + str(linear_function_index)
            + "} &= "
            + enforce_max_terms_per_line(
                latex_formula=latex_formula,
                max_terms_per_line=options.max_terms_per_line,
            )
            + R"\tag{"
            + str(display_index)
            + "}"
        )
        display_index += 1

        first = False

        if not options.multiple:
            try:
                display(Latex(R"\begin{align}" + s + R"& \end{align}"))
            except Exception:
                print("too much math")
            s = ""

    if options.multiple:
        s += "\n" + R"\end{align}"
        try:
            display(Latex(s))
        except Exception:
            print("too much math")
