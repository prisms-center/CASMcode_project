from typing import TYPE_CHECKING

import numpy as np

import libcasm.clexulator as clex
import libcasm.composition as comp
import libcasm.configuration as casmconfig
import libcasm.xtal as xtal
from casm.tools.shared.json_io import read_optional, safe_dump

if TYPE_CHECKING:
    from casm.project import Project


class FittingData:
    """A convenient class that holds all the required properties
    of configurations which can be used while fitting cluster expansions

    This class can be constructed from :func:`make_calculated_fitting_data` or
    :func:`make_uncalculated_fitting_data`

    If it is constructed from :func:`make_calculated_fitting_data`, all the
    attributes will be filled

    If it is constructed from :func:`make_uncalculated_fitting_data`, all the
    attributes except `formation_energies` will be filled
    """

    def __init__(self, proj: "Project", id: str, use_npz: bool = False):
        """

        .. rubric:: Constructor

        Parameters
        ----------
        proj: casm.project.Project
            The CASM project
        id: str
            The fit identifier. Fitting data is stored in the
            fits directory at `<project>/fits/fit.<id>/`.
        use_npz: bool, optional
            If True, prefer loading from fitting_data.npz over
            fitting_data.json. If False (default), load from fitting_data.json only.
            Passed to :meth:`load`.
        """

        self.proj = proj
        """Project: CASM project reference"""

        self.id = id
        """str: Fit identifier"""

        self.fit_dir = self.proj.dir.fit_dir(fit=id)
        """pathlib.Path: Fitting data directory"""

        ### Data (load & commit) ###

        self.meta = dict()
        """dict: A description of the fit, read from `meta.json`."""

        self.names = None
        """Optional[np.ndarray]: Names of the configurations, a shape=(n_configs,) 
        array of strings, if given."""

        self.parametric_compositions = None
        """Optional[np.ndarray]: Parametric compositions of all the configurations, a 
        shape=(n_configs, n_axes) array, if given."""

        self.mol_compositions = None
        """ Optional[np.ndarray]: Number of components per unitcell of all the 
        configurations, a shape=(n_configs, n_components) array, if given."""

        self.correlations_per_unitcell = None
        """ Optional[np.ndarray]: Correlations per unitcell of all the configurations, a
        shape=(n_configs, n_corr_size) array, if given."""

        self.formation_energies = None
        """ Optional[np.ndarray]: Formation energy per unitcell of all the 
        configurations, a shape=(n_configs,) array, if given."""

        # load data
        self.load(use_npz=use_npz)

    def from_dict(self, data):
        """Set fitting data attributes from a dictionary.

        Parameters
        ----------
        data : dict
            A dictionary containing `names`, `parametric_compositions`,
            `mol_compositions`, `correlations_per_unitcell`, and optionally
            `formation_energies`.
        """
        self.names = np.array(data["names"])
        self.parametric_compositions = np.array(data["parametric_compositions"])
        self.mol_compositions = np.array(data["mol_compositions"])
        self.correlations_per_unitcell = np.array(data["correlations_per_unitcell"])
        if data.get("formation_energies") is not None:
            self.formation_energies = np.array(data["formation_energies"])
        else:
            self.formation_energies = None

    def load(self, use_npz: bool = False):
        """Read meta.json and fitting_data.npz or fitting_data.json

        This will replace the current contents of this FittingData object with
        the contents of the associated files, or set the current contents to None if the
        associated files do not exist.

        Parameters
        ----------
        use_npz : bool, optional
            If True, load from fitting_data.npz if it exists, falling back to
            fitting_data.json. If False (default), load from fitting_data.json only.
        """

        # read meta.json if it exists
        path = self.fit_dir / "meta.json"
        self.meta = read_optional(path, default=dict())

        npz_path = self.fit_dir / "fitting_data.npz"
        json_path = self.fit_dir / "fitting_data.json"

        if use_npz and npz_path.exists():
            data = np.load(npz_path, allow_pickle=False)
            self.names = data["names"]
            self.parametric_compositions = data["parametric_compositions"]
            self.mol_compositions = data["mol_compositions"]
            self.correlations_per_unitcell = data["correlations_per_unitcell"]
            self.formation_energies = (
                data["formation_energies"] if "formation_energies" in data else None
            )
        else:
            data = read_optional(json_path, default=None)
            if data is not None:
                self.from_dict(data)

    def commit(self, verbose: bool = True, use_npz: bool = False):
        """Write meta.json and fitting_data.npz or fitting_data.json

        If the data does not exist in this object, this will erase the associated
        files if they do exist.

        Parameters
        ----------
        verbose : bool, optional
            If True (default), print the path of the file being written.
        use_npz : bool, optional
            If True, write fitting data as a compressed numpy binary file
            (fitting_data.npz). Significantly faster and smaller for large datasets.
            Any existing fitting_data.json is removed. If False (default), write as
            fitting_data.json and remove any existing fitting_data.npz.
        """
        quiet = not verbose
        self.fit_dir.mkdir(parents=True, exist_ok=True)

        # write meta.json
        path = self.fit_dir / "meta.json"
        if len(self.meta) > 0:
            if not isinstance(self.meta, dict):
                raise TypeError(
                    "Error in FittingData.commit: FittingData.meta must be a dict"
                )
            safe_dump(
                data=self.meta,
                path=path,
                quiet=quiet,
                force=True,
            )
        elif path.exists():
            path.unlink()

        # write fitting data
        json_path = self.fit_dir / "fitting_data.json"
        npz_path = self.fit_dir / "fitting_data.npz"

        if self.names is not None:
            if use_npz:
                arrays = dict(
                    names=self.names,
                    parametric_compositions=self.parametric_compositions,
                    mol_compositions=self.mol_compositions,
                    correlations_per_unitcell=self.correlations_per_unitcell,
                )
                if self.formation_energies is not None:
                    arrays["formation_energies"] = self.formation_energies
                np.savez_compressed(npz_path, **arrays)
                if not quiet:
                    print(f"write: {npz_path}")
                if json_path.exists():
                    json_path.unlink()
            else:
                safe_dump(data=self.to_dict(), path=json_path, quiet=quiet, force=True)
                if npz_path.exists():
                    npz_path.unlink()
        else:
            for path in [json_path, npz_path]:
                if path.exists():
                    path.unlink()

    def clear(self):
        """Clear fitting data"""
        # TODO
        pass

    def __repr__(self):
        from libcasm.xtal import pretty_json

        s = "FittingData:\n"
        s += f"- id: {self.id}\n"

        if self.meta is not None and "desc" in self.meta:
            s += f'- desc: {pretty_json(self.meta["desc"]).strip()}\n'

        # TODO:

        return s.strip()

    def to_dict(self):
        """Turn `FittingData` into a dictionary with `names`,
        `parametric_compositions`, `mol_compositions`, `correlations_per_unitcell`
        and `formation_energies` for the configurations.

        Returns
        -------
        data : dict

        """
        return dict(
            names=(
                self.names if isinstance(self.names, list)
                else self.names.tolist()
            ),
            parametric_compositions=self.parametric_compositions.tolist(),
            mol_compositions=self.mol_compositions.tolist(),
            correlations_per_unitcell=self.correlations_per_unitcell.tolist(),
            formation_energies=(
                self.formation_energies.tolist()
                if self.formation_energies is not None
                else None
            ),
        )


def _extract_correlations_for_configuration(
    configuration: casmconfig.Configuration,
    clexulator: clex.Clexulator,
    prim_neighbor_list: clex.PrimNeighborList,
) -> np.ndarray:
    """Helper function which calculates correlations_per_unitcell
    of a configuration given a clexulator

    Parameters
    ----------
    configuration : libcasm.configuration.Configuration
        :class:`~libcasm.configuration.Configuration` for which to obtain
        correlations
    clexulator : libcasm.clexulator.Clexulator
        :class:`~libcasm.clexulator.Clexulator` which will be used to
        obtain correlations
    prim_neighbor_list : libcasm.clexulator.PrimNeighborList
        A :class:`~libcasm.clexulator.PrimNeighborList` which will be
        used to construct the :class:`~libcasm.clexulator.SuperNeighborList`
        for every configuration and will be used while obtaining correlations

    Returns
    -------
    corr_per_unitcell : np.ndarray
        Correlations per unitcell

    """
    transformation_matrix_to_super = (
        configuration.supercell.transformation_matrix_to_super
    )
    super_neighbor_list = clex.SuperNeighborList(
        transformation_matrix_to_super=transformation_matrix_to_super,
        prim_neighbor_list=prim_neighbor_list,
    )
    corr = clex.Correlations(
        super_neighbor_list,
        clexulator,
        configuration.dof_values,
    )
    return corr.per_unitcell(corr.per_supercell())


def _extract_mol_and_param_comp_for_configuration(
    configuration: casmconfig.Configuration,
    xtal_prim: xtal.Prim,
    composition_converter: comp.CompositionConverter,
):
    """Helper function that calculates mol and parametric
    composition given a configuration

    Parameters
    ----------
    configuration : libcasm.configuration.Configuration
        :class:`~libcasm.configuration.Configuration` for which to obtain
        correlations
    xtal_prim : libcasm.xtal.Prim
        Prim of the project
    composition_converter : libcasm.composition.CompositionConverter
        A :class:`~libcasm.composition.CompositionCalculator` object with
        the warranted composition axes set, which will be used to obtain
        mol and parametric compostions

    Returns
    -------
    mol_comp, param_comp : tuple[np.ndarray, np.ndarray]
        mol composition and parametric composition of the configuration

    """
    # Extract mol compositions-----------
    composition_calculator = comp.CompositionCalculator(
        allowed_occs=xtal_prim.occ_dof(),
        components=composition_converter.components(),
    )
    mol_comp = composition_calculator.mean_num_each_component(configuration.occupation)
    # Convert mol comp to param comp
    param_comp = composition_converter.param_composition(mol_comp)

    return mol_comp, param_comp


def make_calculated_fitting_data(
    xtal_prim: xtal.Prim,
    config_props: list[dict],
    composition_converter: comp.CompositionConverter,
    clexulator: clex.Clexulator,
    prim_neighbor_list: clex.PrimNeighborList,
    proj: "Project",
    id: str,
    names: list[str] = None,
) -> FittingData:
    """For a given `config_props` list, constructs FittingData which
    which holds compositions, correlations per unitcell, formation energies
    of all the configurations in the `config_props`

    This should be used on `config_props` which is generated by mapping/importing

    Parameters
    ----------
    xtal_prim : xtal.Prim
        Prim of the project
    config_props : list[dict]
        A list containing results of mapping/import
    composition_converter : libcasm.composition.CompositionConverter
        A :class:`~libcasm.composition.CompositionConverter` object with
        the warranted composition axes set, which will be used to obtain
        mol and parametric compostions
    clexulator : libcasm.clexulator.Clexulator
        :class:`~libcasm.clexulator.Clexulator` which will be used to
        obtain correlations
    prim_neighbor_list : libcasm.clexulator.PrimNeighborList
        A :class:`~libcasm.clexulator.PrimNeighborList` which will be
        used to construct the :class:`~libcasm.clexulator.SuperNeighborList`
        for every configuration and will be used while obtaining correlations
    proj: casm.project.Project
        The CASM project
    id: str
        The fit identifier. Fitting data is stored in the
        fits directory at `<project>/fits/fit.<id>/`.
    names: Optional[list[str]]
        Names of the configurations. If None (default), names are
        auto-generated as ``"config.0"``, ``"config.1"``, etc.

    Returns
    -------
    FittingData

    """

    _names = []
    parametric_compositions = []
    mol_compositions = []
    correlations_per_unitcell = []
    formation_energies = []

    supercell_set = casmconfig.SupercellSet(casmconfig.Prim(xtal_prim))
    for config_id, config_prop in enumerate(config_props):
        config_with_properties = casmconfig.ConfigurationWithProperties.from_dict(
            config_prop["configuration_with_properties"], supercell_set
        )
        # Extract correlations
        corr_per_unitcell = _extract_correlations_for_configuration(
            configuration=config_with_properties.configuration,
            clexulator=clexulator,
            prim_neighbor_list=prim_neighbor_list,
        )

        # Extract mol and param compositions
        mol_comp, param_comp = _extract_mol_and_param_comp_for_configuration(
            configuration=config_with_properties.configuration,
            xtal_prim=xtal_prim,
            composition_converter=composition_converter,
        )

        _names.append("config." + str(config_id))
        correlations_per_unitcell.append(corr_per_unitcell.tolist())
        mol_compositions.append(mol_comp.tolist())
        parametric_compositions.append(param_comp.tolist())

        # This currently assumes that formation energies are already
        # in config props. Should it be like this??
        formation_energies.append(config_prop["formation_energy"])

    fitting_data = FittingData(proj, id)
    fitting_data.from_dict(
        dict(
            names=names if names is not None else _names,
            parametric_compositions=parametric_compositions,
            mol_compositions=mol_compositions,
            correlations_per_unitcell=correlations_per_unitcell,
            formation_energies=formation_energies,
        )
    )

    return fitting_data


def make_uncalculated_fitting_data(
    xtal_prim: xtal.Prim,
    config_list: list[dict],
    composition_converter: comp.CompositionConverter,
    clexulator: clex.Clexulator,
    prim_neighbor_list: clex.PrimNeighborList,
    proj: "Project",
    id: str,
    names: list[str] = None,
) -> FittingData:
    """For a given `config_list` list, constructs FittingData which
    which holds compositions, correlations per unitcell of all the configurations
    in the `config_list`

    This should be used on `config_list` which is generated by enumeration

    Parameters
    ----------
    xtal_prim : xtal.Prim
        Prim of the project
    config_list : list[dict]
        A list containing results of enumeration
    composition_converter : libcasm.composition.CompositionConverter
        A :class:`~libcasm.composition.CompositionConverter` object with
        the warranted composition axes set, which will be used to obtain
        mol and parametric compostions
    clexulator : libcasm.clexulator.Clexulator
        :class:`~libcasm.clexulator.Clexulator` which will be used to
        obtain correlations
    prim_neighbor_list : libcasm.clexulator.PrimNeighborList
        A :class:`~libcasm.clexulator.PrimNeighborList` which will be
        used to construct the :class:`~libcasm.clexulator.SuperNeighborList`
        for every configuration and will be used while obtaining correlations
    proj: casm.project.Project
        The CASM project
    id: str
        The fit identifier. Fitting data is stored in the
        fits directory at `<project>/fits/fit.<id>/`.
    names: Optional[list[str]]
        Names of the configurations. If None (default), names are
        auto-generated as ``"config.0"``, ``"config.1"``, etc.

    Returns
    -------
    FittingData

    """
    _names = []
    parametric_compositions = []
    mol_compositions = []
    correlations_per_unitcell = []

    supercell_set = casmconfig.SupercellSet(casmconfig.Prim(xtal_prim))
    for config_id, config in enumerate(config_list):
        configuration = casmconfig.Configuration.from_dict(
            config["configuration_with_properties"], supercell_set
        )

        # Extract correlations
        corr_per_unitcell = _extract_correlations_for_configuration(
            configuration=configuration,
            clexulator=clexulator,
            prim_neighbor_list=prim_neighbor_list,
        )

        # Extract mol and param compositions
        mol_comp, param_comp = _extract_mol_and_param_comp_for_configuration(
            configuration=configuration,
            xtal_prim=xtal_prim,
            composition_converter=composition_converter,
        )

        _names.append("config." + str(config_id))
        correlations_per_unitcell.append(corr_per_unitcell.tolist())
        mol_compositions.append(mol_comp.tolist())
        parametric_compositions.append(param_comp.tolist())

    fitting_data = FittingData(proj, id)
    fitting_data.from_dict(
        dict(
            names=names if names is not None else _names,
            parametric_compositions=parametric_compositions,
            mol_compositions=mol_compositions,
            correlations_per_unitcell=correlations_per_unitcell,
        )
    )

    return fitting_data
