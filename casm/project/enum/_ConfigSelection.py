from __future__ import annotations

import pathlib
from typing import TYPE_CHECKING, Any, Callable, Optional, Union

import numpy as np

import libcasm.xtal as xtal
from casm.project import (
    ClexDescription,
)
from casm.tools.shared.json_io import (
    read_optional,
    read_required,
    safe_dump,
)
from libcasm.configuration import Configuration, SupercellRecord

if TYPE_CHECKING:
    from ._EnumData import EnumData


def _run_in(
    args: Union[str, list[str], list[list[str]]],
    working_dir: pathlib.Path,
    write_log: bool = True,
    capture_output: bool = False,
    text: Optional[bool] = None,
    shell: bool = False,
    log_base: str = "log",
):
    """Run a subprocess command in the given working directory.

    Parameters
    ----------
    args: Union[str, list[str], list[list[str]]]
        The arguments to run for one or more subprocesses. The subprocesses will be run
        in the calculation directory for each selected configuration.

        By default (if `shell` is False), a `list[str]` provides the arguments for one
        subprocess call and a `list[list[str]]` provides the arguments for a sequence
        of subprocess calls. If `shell` is True, a single `str` provides the
        command to run in a single subprocess, and a `list[str]` provides the
        commands to run in a sequence of subprocesses.

    working_dir: pathlib.Path
        The working directory in which to run the command. This is typically the
        calculation directory for a configuration.
    write_log: bool = True
        If True, write the standard output and error of the command to files named
        `<log_base>.out.txt` and `<log_base>.err.txt` in the working
        directory. If False, the output is printed to the console.
    capture_output: bool = False
        If True, the standard output and error of the command will be captured and
        returned as a list of `subprocess.CompletedProcess` objects. The `write_log`
        argument may not be supplied at the same time as `capture_output`.
    text: Optional[bool] = None
        If True, the output will be captured as text (string) instead of bytes. If

    shell: bool = False
        If True, the specified command will be executed through the shell.
    log_base: str = "log"
        Base name for the log files. If `write_log` is True, the output files will
        be named `<log_base>.out.txt` and `<log_base>.err.txt`.

    Returns
    -------
    completed_processes: list[subprocess.CompletedProcess]
        A list of completed subprocesses, one for each command run.
    """
    import subprocess

    working_dir.mkdir(parents=True, exist_ok=True)

    if shell:
        if isinstance(args, str):
            multi_args = [args]
        else:
            multi_args = args
    else:
        if isinstance(args[0], str):
            multi_args = [args]
        else:
            multi_args = args

    def _make_filename(parent: pathlib.Path, base: str, ext: str) -> pathlib.Path:
        """Create a unique filename."""
        filename = parent / f"{base}.{ext}"
        if filename.exists():
            index = 1
            filename = parent / f"{base}.{index}.{ext}"
            while filename.exists():
                index += 1
                filename = parent / f"{base}.{index}.{ext}"
        return filename

    completed_processes = []

    if write_log:
        stdout_filename = _make_filename(
            parent=working_dir, base=log_base + ".out", ext="txt"
        )
        stderr_filename = _make_filename(
            parent=working_dir, base=log_base + ".err", ext="txt"
        )

        # Run the command in the working directory,
        # save stdout and stderr to files
        with open(stdout_filename, "w") as stdout_file:
            with open(stderr_filename, "w") as stderr_file:
                for single_args in multi_args:
                    subprocess.run(
                        single_args,
                        stdout=stdout_file,
                        stderr=stderr_file,
                        cwd=working_dir,
                        shell=shell,
                    )

    else:
        # Run the command in the working directory,
        # print stdout and stderr to console
        for single_args in multi_args:
            x = subprocess.run(
                single_args,
                cwd=working_dir,
                capture_output=capture_output,
                text=text,
                check=True,
                shell=shell,
            )
            completed_processes.append(x)

    return completed_processes


class ConfigSelectionRecord:
    """A ConfigSelection record.

    This class is provided when iterating over a :class:`ConfigSelection`.

    Notes
    -----
    - The record contains a :py:attr:`~ConfigSelectionRecord.data` dictionary, which is
      a reference to an element of the `records` list in a :class:`ConfigSelection`.
    - The record may be modified by modifying the :py:attr:`~ConfigSelectionRecord.data`
      dictionary or the using :func:`set` method to change the selection status or to
      add or remove custom key-value pairs, but changes are not saved to disk until
      `commit()` is called on the parent :class:`ConfigSelection`.
    - The :py:attr:`~ConfigSelectionRecord.data` dictionary should not be reassigned,
      because that will not update the original record data.

    """

    def __init__(self, parent: ConfigSelection, data: dict):

        self.parent: ConfigSelection = parent
        """ConfigSelection: The parent configuration selection that this record belongs
        to. 
        
        This is used to access context such as the default calctype_id."""

        self.data: dict = data
        """dict: The configuration selection record data. 
        
        This is a reference to an element of the `records` list in a
        :class:`ConfigSelection`. The dictionary may be modified to change the
        selection status or to add or remove custom key-value pairs, but changes are 
        not saved to disk until `commit()` is called on the parent 
        :class:`ConfigSelection`.
        
        The :py:attr:`ConfigSelectionRecord.data` dictionary should not be reassigned,
        because it is a reference to the original record data.
        """

        if "source" not in data:
            raise ValueError("Configuration selection record must have a 'source' key.")
        if "name" not in data:
            raise ValueError("Configuration selection record must have a 'name' key.")
        if "selected" not in data:
            raise ValueError(
                "Configuration selection record must have a 'selected' key."
            )

        # Cache for reading calc status.json file
        self._calc_status_data = None
        self._calc_status_data_mtime = None

    @property
    def _enum(self) -> "EnumData":
        """EnumData: The EnumData for the enumeration the parent selection belongs
        to."""
        return self.parent._enum

    @property
    def source(self) -> str:
        """str: The source of the configuration. One of `config_set.json` or
        `config_list.json`."""
        return self.data["source"]

    @property
    def name(self) -> str:
        """str: The name of the configuration."""
        return self.data["name"]

    @property
    def is_selected(self) -> bool:
        """bool: Whether the configuration is selected."""
        return self.data["selected"]

    def set_selected(self, selected: bool):
        """Set the selection status of the configuration.

        Notes
        -----
        This does not commit the change to disk. You must call `commit()` on the
        :class:`ConfigSelection` to save the change.

        Parameters
        ----------
        selected : bool
            The selection status to set.
        """
        self.data["selected"] = bool(selected)

    def select(self):
        """Select the configuration.

        Notes
        -----
        This does not commit the change to disk. You must call `commit()` on the
        :class:`ConfigSelection` to save the change.

        """
        self.data["selected"] = True

    def deselect(self):
        """Deselect the configuration.

        Notes
        -----
        This does not commit the change to disk. You must call `commit()` on the
        :class:`ConfigSelection` to save the change.

        """
        self.data["selected"] = False

    @property
    def configuration(self) -> Configuration:
        """libcasm.configuration.Configuration: The configuration."""
        if self.source == "config_set.json":
            return self._enum.configuration_set.get_by_name(self.name).configuration
        elif self.source == "config_list.json":
            try:
                index = int(self.name.split("/")[-1])
                return self._enum.configuration_list[index]
            except (ValueError, IndexError) as e:
                raise ValueError(
                    f"Invalid configuration name format: {self.name}"
                ) from e
        else:
            raise ValueError(f"Unsupported source: {self.source}")

    @property
    def structure(self) -> xtal.Structure:
        """libcasm.xtal.Structure: The configuration's structure (vacancies not
        included)."""
        return self.configuration.to_structure()

    @property
    def structure_with_vacancies(self) -> xtal.Structure:
        """libcasm.xtal.Structure: The configuration's structure with vacancies
        included as atoms."""
        return self.configuration.to_structure(
            excluded_species=None,
        )

    @property
    def supercell(self) -> Configuration:
        """libcasm.configuration.Supercell: The configuration's supercell."""
        return self.configuration.supercell

    @property
    def supercell_name(self) -> Configuration:
        """str: The configuration's supercell's name."""
        return SupercellRecord(self.supercell).supercell_name

    @property
    def n_unitcells(self) -> int:
        """int: The number of unit cells in the configuration's supercell."""
        return self.supercell.n_unitcells

    @property
    def chemical_param_comp(self) -> np.ndarray:
        """numpy.ndarray: The parametric chemical composition of the configuration in
        the project's default chemical composition axes."""
        return self.parent._chemical_comp_calculator.param_composition(
            self.configuration
        )

    @property
    def chemical_comp_per_supercell(self) -> np.ndarray:
        """numpy.ndarray: The chemical composition of the configuration, in number per
        supercell."""
        return self.parent._chemical_comp_calculator.per_supercell(self.configuration)

    @property
    def chemical_comp_per_unitcell(self) -> np.ndarray:
        """numpy.ndarray: The chemical composition of the configuration, in number per
        unitcell."""
        return self.parent._chemical_comp_calculator.per_unitcell(self.configuration)

    @property
    def chemical_comp_species_frac(self) -> np.ndarray:
        """numpy.ndarray: The chemical composition of the configuration, in species
        fraction, with [Va] = 0.0"""
        return self.parent._chemical_comp_calculator.species_frac(self.configuration)

    def chemical_sublat_comp_per_supercell(
        self,
        sublattice_index: Optional[int] = None,
    ) -> np.ndarray:
        """Calculate chemical sublattice composition per supercell.

        Returns
        -------
        value: numpy.ndarray
            The chemical composition of the configuration, in number per
            supercell, on the requested sublattice.
        """
        return self.parent._chemical_comp_calculator.per_supercell(
            self.configuration,
            sublattice_index=sublattice_index,
        )

    def chemical_sublat_comp_per_unitcell(
        self,
        sublattice_index: Optional[int] = None,
    ) -> np.ndarray:
        """Calculate chemical sublattice composition per unitcell.

        Returns
        -------
        value: numpy.ndarray
            The chemical composition of the configuration, in number per
            unitcell, on the requested sublattice.
        """
        return self.parent._chemical_comp_calculator.per_unitcell(
            self.configuration,
            sublattice_index=sublattice_index,
        )

    def chemical_sublat_comp_species_frac(
        self,
        sublattice_index: Optional[int] = None,
    ) -> np.ndarray:
        """Calculate chemical sublattice composition as species fraction, with
        [Va] = 0.0

        Returns
        -------
        value: numpy.ndarray
            The chemical composition of the configuration, in species fraction, with
            [Va] = 0.0, on the requested sublattice.
        """
        return self.parent._chemical_comp_calculator.species_frac(
            self.configuration,
            sublattice_index=sublattice_index,
        )

    @property
    def occupant_param_comp(self) -> np.ndarray:
        """numpy.ndarray: The parametric occupant composition of the configuration in
        the project's default occupant composition axes."""
        return self.parent._occupant_comp_calculator.param_composition(
            self.configuration
        )

    @property
    def occupant_comp_per_supercell(self) -> np.ndarray:
        """numpy.ndarray: The occupant composition of the configuration, in number per
        supercell."""
        return self.parent._occupant_comp_calculator.per_supercell(self.configuration)

    @property
    def occupant_comp_per_unitcell(self) -> np.ndarray:
        """numpy.ndarray: The occupant composition of the configuration, in number per
        unitcell."""
        return self.parent._occupant_comp_calculator.per_unitcell(self.configuration)

    @property
    def occupant_comp_species_frac(self) -> np.ndarray:
        """numpy.ndarray: The occupant composition of the configuration, in species
        fraction, with [Va] = 0.0"""
        return self.parent._occupant_comp_calculator.species_frac(self.configuration)

    def occupant_sublat_comp_per_supercell(
        self,
        sublattice_index: Optional[int] = None,
    ) -> np.ndarray:
        """Calculate the occupant composition per supercell on a particular sublattice.

        Returns
        -------
        value: numpy.ndarray
            The occupant composition of the configuration, in number per
            supercell, on the requested sublattice.
        """
        return self.parent._occupant_comp_calculator.per_supercell(
            self.configuration,
            sublattice_index=sublattice_index,
        )

    def occupant_sublat_comp_per_unitcell(
        self,
        sublattice_index: Optional[int] = None,
    ) -> np.ndarray:
        """Calculate the occupant composition per unitcell on a particular sublattice.

        Returns
        -------
        value: numpy.ndarray
            The occupant composition of the configuration, in number per
            unitcell, on the requested sublattice.
        """
        return self.parent._occupant_comp_calculator.per_unitcell(
            self.configuration,
            sublattice_index=sublattice_index,
        )

    def occupant_sublat_comp_species_frac(
        self,
        sublattice_index: Optional[int] = None,
    ) -> np.ndarray:
        """Calculate the occupant composition as species fraction, with [Va] = 0.0
        on a particular sublattice.

        Returns
        -------
        value: numpy.ndarray
            The occupant composition of the configuration, in species fraction, with
            [Va] = 0.0, on the requested sublattice.
        """
        return self.parent._occupant_comp_calculator.species_frac(
            self.configuration,
            sublattice_index=sublattice_index,
        )

    @property
    def corr_per_unitcell(self) -> Optional[np.ndarray]:
        """Optional[numpy.ndarray]: The correlations of the configuration per unitcell,
        if a basis set exists."""
        _corr_calculator = self.parent._corr_calculator
        if _corr_calculator is None:
            return None

        return _corr_calculator.per_unitcell(self.configuration)

    @property
    def corr_per_supercell(self) -> Optional[np.ndarray]:
        """Optional[numpy.ndarray]: The correlations of the configuration per supercell,
        if a basis set exists."""
        _corr_calculator = self.parent._corr_calculator
        if _corr_calculator is None:
            return None

        return _corr_calculator.per_supercell(self.configuration)

    @property
    def calc_dir(self) -> Optional[pathlib.Path]:
        """Optional[pathlib.Path]: The calculation directory for this configuration,
        if a `clex` is given for the parent selection."""
        if self.parent.clex is None:
            return None

        return self._enum.proj.dir.enum_calc_dir(
            enum=self._enum.id,
            calctype=self.parent.clex.calctype,
            configname=self.name,
        )

    @property
    def calc_dir_tgz(self) -> Optional[pathlib.Path]:
        """Optional[pathlib.Path]: The path of the calculation directory archive
        for this configuration, if a `clex` is given for the parent selection."""
        if self.parent.clex is None:
            return None

        return pathlib.Path(str(self.calc_dir) + ".tgz")

    def compress_calc_dir(self):
        """Compress the calculation directory for this configuration into a gzipped
        archive, `<calc_dir>.tgz`, if it exists.

        Returns
        -------
        tgz_file: Optional[pathlib.Path]
            The path to the compressed .tgz file. If the calculation directory does not
            exist, returns None.
        """
        calc_dir = self.calc_dir
        if calc_dir is None or not calc_dir.exists():
            return None

        from casm.tools.shared.file_utils import compress

        compress(
            dir=self.calc_dir,
            quiet=True,
            remove_dir=True,
            extension=".tgz",
        )

    def uncompress_calc_dir(self):
        """Uncompress the calculation directory archive for this configuration, if it
        exists."""
        tgz_file = self.calc_dir_tgz

        if not tgz_file.exists():
            return

        from casm.tools.shared.file_utils import uncompress

        uncompress(tgz_file, quiet=True, remove_tgz_file=True)

    @property
    def calc_status_data(self) -> Optional[dict]:
        """Optional[dict]: Contents of the `status.json` file in the
        calculation directory, if it exists.
        """
        if self.calc_dir is None:
            # If no calculation directory is set, return None
            self._calc_status_data = None
            self._calc_status_data_mtime = None
            return None
        path = self.calc_dir / "status.json"
        if not path.exists():
            self._calc_status_data = None
            self._calc_status_data_mtime = None
            return None
        curr_mtime = path.stat().st_mtime
        if self._calc_status_data_mtime != curr_mtime:
            # If the mtime has changed, read the file again
            self._calc_status_data = read_optional(path)
            self._calc_status_data_mtime = curr_mtime
        return self._calc_status_data

    @property
    def calc_status(self) -> str:
        """str: The status of the configuration's calculation, as determined by
        checking a `status.json` file in the configuration's calculation directory.

        Returns the value of the `"status"` attribute in the `status.json` file. If
        no `clex` is given for the parent selection or the `status.json` file does
        not exist in the calculation directory, returns "none". If the file does
        exist, but the `"status"` attribute is not present, is not a str, or otherwise
        can't be read, an exception is raised.
        """
        data = self.calc_status_data
        if data is None:
            return "none"
        status = data.get("status")
        if status is None:
            return "none"
        elif not isinstance(status, str):
            raise ValueError(f"Invalid status: expected str, got {type(status)}")
        return status

    @property
    def calc_jobid(self) -> str:
        """str: The calculation's job ID, as determined by checking a `status.json`
        file in the configuration's calculation directory.

        Returns the value of the `"jobid"` attribute in the `status.json` file. If
        no `clex` is given for the parent selection or the `status.json` file does
        not exist in the calculation directory, or a `"jobid"` is not present,
        returns "none". If the file does exist, but the `"status"` attribute is not
        present, is not a str, or otherwise can't be read, an exception is raised.
        """
        data = self.calc_status_data
        if data is None:
            return "none"
        jobid = data.get("jobid")
        if jobid is None:
            return "none"
        elif not isinstance(jobid, str):
            raise ValueError(f"Invalid jobid: expected str, got {type(jobid)}")
        return jobid

    @property
    def calc_starttime(self) -> Optional[str]:
        """Optional[str]: The calculation's start time, as determined by checking a
        `status.json` file in the configuration's calculation directory.

        Returns the value of the `"starttime"` attribute in the `status.json` file.
        If no `clex` is given for the parent selection or the `status.json` file does
        not exist in the calculation directory, returns None. If the file does exist,
        but the `"starttime"` attribute is not present, is not a str, or otherwise
        can't be read, an exception is raised.
        """
        data = self.calc_status_data
        if data is None:
            return "none"
        starttime = data.get("starttime")
        if starttime is None:
            return "none"
        elif not isinstance(starttime, str):
            raise ValueError(f"Invalid starttime: expected str, got {type(starttime)}")
        return starttime

    @property
    def calc_stoptime(self) -> Optional[str]:
        """Optional[str]: The calculation's stop time, as determined by checking a
        `status.json` file in the configuration's calculation directory.

        Returns the value of the `"stoptime"` attribute in the `status.json` file.
        If no `clex` is given for the parent selection or the `status.json` file does
        not exist in the calculation directory, returns None. If the file does exist,
        but the `"stoptime"` attribute is not present, is not a str, or otherwise
        can't be read, an exception is raised.
        """
        data = self.calc_status_data
        if data is None:
            return "none"
        stoptime = data.get("stoptime")
        if stoptime is None:
            return "none"
        elif not isinstance(stoptime, str):
            raise ValueError(f"Invalid stoptime: expected str, got {type(stoptime)}")
        return stoptime

    @property
    def calc_runtime(self) -> Optional[float]:
        """Optional[str]: The calculation's runtime in HH:MM:SS format, as determined by
        checking a `status.json` file in the configuration's calculation directory.

        Calculates the runtime as the difference between `calc_stoptime` and
        `calc_starttime`, if both are available. If either is not available, returns
        None.
        """
        starttime = self.calc_starttime
        stoptime = self.calc_stoptime
        if starttime == "none":
            return "none"

        # If stoptime is "none", we assume the calculation is still running and
        # set stoptime to the current time.
        running = False
        if stoptime == "none":
            from datetime import datetime

            stoptime = datetime.now().isoformat()
            running = True

        # starttime and stoptime are expected to be in format generated by
        # `$(date +%Y-%m-%dT%H:%M:%S)` in a bash script, which is ISO 8601 format.
        from datetime import datetime

        try:
            start_dt = datetime.fromisoformat(starttime)
            stop_dt = datetime.fromisoformat(stoptime)
        except ValueError as e:
            raise ValueError(
                f"Invalid datetime format in status.json: "
                f"starttime='{starttime}', stoptime='{stoptime}'"
            ) from e
        runtime = stop_dt - start_dt

        # Runtime is in timedelta format. Convert to D-HH:MM:SS format:
        def formatted(runtime: datetime.timedelta) -> str:
            total_seconds = int(runtime.total_seconds())

            days = total_seconds // (24 * 3600)
            total_seconds %= 24 * 3600
            hours = total_seconds // 3600
            total_seconds %= 3600
            minutes = total_seconds // 60
            seconds = total_seconds % 60

            if days > 0:
                return f"{days}-{hours:02}:{minutes:02}:{seconds:02}"
            else:
                if hours > 0:
                    return f"{hours}:{minutes:02}:{seconds:02}"
                elif minutes > 0:
                    return f"{minutes}:{seconds:02}"
                else:
                    # Handles cases with only seconds, e.g., 30 seconds -> 0:30
                    return f"0:{seconds:02}"

        formatted_time = formatted(runtime)
        if running:
            formatted_time = f"{formatted_time}+"
        return formatted_time

    @property
    def is_calculated(self) -> bool:
        """bool: Whether the configuration has been calculated, as determined by
        checking for the presence of a `structure_with_properties.json` file in the
        configuration's calculation directory.

        .. warning::

            This does not check for custom structures that are equivalent to the
            configuration, other enumerations with equivalent configurations,
            configurations that relaxed to this configuration, configurations that have
            been calculated with different calculation type settings, etc.

        """
        calc_dir = self.calc_dir
        if calc_dir is None:
            return False

        structure_file = calc_dir / "structure_with_properties.json"
        return structure_file.exists()

    @property
    def calculated_structure_with_properties(self) -> Optional[xtal.Structure]:
        """Optional[xtal.Structure]: The structure with properties for the
        configuration, if it has been calculated, and saved in a
        `structure_with_properties.json` file in the configuration's calculation
        directory.

        Is None if the configuration has not been calculated or if the
        calculation directory does not exist.

        .. warning::

            This does not check for custom structures that are equivalent to the
            configuration, other enumerations with equivalent configurations,
            configurations that relaxed to this configuration, configurations that have
            been calculated with different calculation type settings, etc.

        """
        calc_dir = self.calc_dir
        if calc_dir is None:
            return None

        structure_file = calc_dir / "structure_with_properties.json"
        if not structure_file.exists():
            return None
        return xtal.Structure.from_dict(read_required(structure_file))

    def set(self, key: str, value: Any):
        """Set a custom key-value pair in the record.

        Notes
        -----
        This does not commit the change to disk. You must call `commit()` on the
        :class:`ConfigSelection` to save the change.

        Parameters
        ----------
        key : str
            The key to set.
        value : Any
            The value to set for the key. The value should be JSON serializable.
        """
        self.data[key] = value

    def get(self, key: str, default_value: Any = None) -> Any:
        """Get the value of a custom key-value pair from the record.

        Parameters
        ----------
        key : str
            The key to get.
        default_value : Any = None
            The default value to return if the key does not exist. Defaults to None.

        Returns
        -------
        Any
            The value associated with the key.
        """
        return self.data.get(key, default_value)

    def run_subprocess(
        self,
        args: Union[str, list[str], list[list[str]]],
        write_log: bool = False,
        capture_output: bool = False,
        text: Optional[bool] = None,
        shell: bool = False,
    ):
        """Run a subprocess command in the calculation directory (whether or not the
        configuration is selected)

        Parameters
        ----------
        args: Union[str, list[str], list[list[str]]]
            The arguments to run for one or more subprocesses. The subprocesses will be
            run in the calculation directory for each selected configuration.

            By default (if `shell` is False), a `list[str]` provides the arguments for
            one subprocess call and a `list[list[str]]` provides the arguments for a
            sequence of subprocess calls. If `shell` is True, a single `str` provides
            the command to run in a single subprocess, and a `list[str]` provides the
            commands to run in a sequence of subprocesses.

        write_log: bool = True
            If True, write the standard output and error of the command to files named
            `<log_base>.out.txt` and `<log_base>.err.txt` in the working
            directory. If False, the output is printed to the console.

        capture_output: bool = False
            If True, the standard output and error of the command will be captured and
            returned as a list of `subprocess.CompletedProcess` objects. The `write_log`
            argument may not be supplied at the same time as `capture_output`.

        text: Optional[bool] = None
            If True, the output will be captured as text (str) instead of bytes.

        shell: bool = False
            If True, the specified command will be executed through the shell.

        Returns
        -------
        completed_processes: list[subprocess.CompletedProcess]
            A list of completed subprocesses, one for each command run.
        """
        return _run_in(
            args=args,
            working_dir=self.calc_dir,
            write_log=write_log,
            capture_output=capture_output,
            text=text,
            shell=shell,
            log_base="subprocess",
        )

    def run_shell_script(
        self,
        script: pathlib.Path,
        write_log: bool = True,
    ):
        """Run a shell script in the calculation directory (whether or not the
        configuration is selected)

        Parameters
        ----------
        config_selection: ConfigSelection
            A selection of Configurations to run the script for. All selected
            configurations will have the script run.
        script: pathlib.Path
            The path to the shell script to run. The script will be copied into the
            the calculation directory for each selected configuration. The script will
            then be run with the working directory set to the calculation directory.
            The shell to use is determined by the `SHELL` environment variable,
            defaulting to `/bin/bash`.
        write_log: bool = True
            If True, write the standard output and error of the script to files named
            `<script_name>.out.txt` and `<script_name>.err.txt` in the calculation
            directory. If False, the output is printed to the console.

        Returns
        -------
        completed_processes: list[subprocess.CompletedProcess]
            A list of completed subprocesses, one for each command run.
        """
        import os
        import shutil

        # Detect the default shell
        default_shell = os.environ.get("SHELL", "/bin/bash")

        args = [default_shell, script.name]

        calc_dir = self.calc_dir
        calc_dir.mkdir(parents=True, exist_ok=True)

        # Copy the script to the calculation directory
        script_dest = calc_dir / script.name
        shutil.copy(script, script_dest)

        return _run_in(
            args=args,
            working_dir=calc_dir,
            write_log=write_log,
        )

    def run_python_script(
        self,
        script: pathlib.Path,
        write_log: bool = True,
    ):
        """Run a Python script in the calculation directory (whether or not the
        configuration is selected)

        Parameters
        ----------
        config_selection: ConfigSelection
            A selection of Configurations to run the script for. All selected
            configurations will have the script run.
        script: pathlib.Path
            The path to the Python script to run. The script will be copied into the
            calculation directory for each selected configuration. The script will then
            be run with the working directory set to the calculation directory.
        write_log: bool = True
            If True, write the standard output and error of the script to files named
            `<script_name>.out.txt` and `<script_name>.err.txt` in the calculation
            directory. If False, the output is printed to the console.

        Returns
        -------
        completed_processes: list[subprocess.CompletedProcess]
            A list of completed subprocesses, one for each command run.
        """
        import shutil

        args = ["python", script.name]

        calc_dir = self.calc_dir
        calc_dir.mkdir(parents=True, exist_ok=True)

        # Copy the script to the calculation directory
        script_dest = calc_dir / script.name
        shutil.copy(script, script_dest)

        return _run_in(
            args=args,
            working_dir=calc_dir,
            write_log=write_log,
        )


class SelectedRecords:
    def __init__(self, selection: "ConfigSelection"):
        """Iterate over selected records in a ConfigSelection.

        Parameters
        ----------
        selection : ConfigSelection
            The configuration selection to work with.
        """
        self.selection = selection

    def __iter__(self):
        for _record in self.selection._records:
            if _record["selected"]:
                yield ConfigSelectionRecord(parent=self.selection, data=_record)


class UnselectedRecords:
    def __init__(self, selection: "ConfigSelection"):
        """Iterate over unselected records in a ConfigSelection.

        Parameters
        ----------
        selection : ConfigSelection
            The configuration selection to work with.
        """
        self.selection = selection

    def __iter__(self):
        for _record in self.selection._records:
            if not _record["selected"]:
                yield ConfigSelectionRecord(parent=self.selection, data=_record)


class AllRecords:
    def __init__(self, selection: "ConfigSelection"):
        """Iterate over all records in a ConfigSelection.

        Parameters
        ----------
        selection : ConfigSelection
            The configuration selection to work with.
        """
        self.selection = selection

    def __iter__(self):
        for _record in self.selection._records:
            yield ConfigSelectionRecord(parent=self.selection, data=_record)


class ConfigSelection:
    """A selection of configurations from an enumeration.

    This class helps to select configurations from an enumeration and to query data,
    setup calculations, retrieve calculation results, calculate correlations, fit
    cluster expansion coefficients, etc.

    Notes
    -----

    - Selections are saved to a JSON file in the enumeration directory, allowing
      reuse. The file is named `config_selection.<name>.json` or
      `config_selection.<name>.json.gz`, if the compression option `gz` is set to True.
    - Selections are typically constructed and used via the
      :func:`EnumData.config_selection` method.
    - To save a newly constructed or modified selection, call the
      :func:`Selection.commit` method.

    .. rubric:: Special Methods

    - ``for record in selection``: Iterate over selected configurations, yielding
      :class:`ConfigSelectionRecord` for each selected configuration.
    - ``for record in selection.selected``: Same as ``for record in selection``, but
      stated explicitly that it only iterates over selected records.
    - ``for record in selection.unselected``: Iterate over unselected configurations,
      yielding :class:`ConfigSelectionRecord` for each unselected configuration.
    - ``for record in selection.all``: Iterate over all configurations, yielding
      :class:`ConfigSelectionRecord` for each configuration, regardless of selection
      status.


    """

    def __init__(
        self,
        enum: "EnumData",
        name: str,
        clex: Union[str, ClexDescription, None] = None,
        gz: bool = False,
        records: Union[list[dict], None] = None,
    ):
        """

        .. rubric:: Constructor

        Parameters
        ----------
        enum : EnumData
            The enumeration data.

        name : str
            The name of the configuration selection. This is used to save the selection
            to a JSON file. For example, if `name` is "main", the selection is
            saved as in the enumeration directory as `config_selection.main.json`.

        clex : Union[str, ClexDescription, None] = None
            Specifies the default cluster expansion settings to use when getting
            properties, working with calculations, calculating basis functions, etc.

            By default, the project's default cluster expansion is used. If a
            string is provided, it should be the name of a cluster expansion included in
            the :py:data:`ProjectSettings.cluster_expansions` dictionary of the
            project's settings. Otherwise, a custom :class:`ClexDescription` can be
            provided.

        gz : bool = False
            When constructing a new selection, if True, the selection is saved as a
            gzipped JSON file. If False (default), it is saved as a regular JSON file.
            If the selection already exists in files, this is ignored and detected from
            the file extension.

        records : Optional[list[dict]] = None
            When constructing a new selection, this may be used to initialize the
            selection. If the selection already is saved to a file, this is ignored and
            the records are read from the file. By default, a new selection is
            constructed with all configurations included and selected. If provided,
            it should be a list of dict:

            .. code-block:: Python

                [
                    {
                        "source": "config_set.json",
                        "name": "SCEL1_1_1_1_0_0_0/0",
                        "selected": True,
                        ...
                    },
                    {
                        "source": "config_list.json",
                        "name": "config_list/0",
                        "selected": True,
                        ...
                    }
                ]

            The records require "source", "name", and "selected" keys. Additional
            keys may be included.

        """
        self._enum: "EnumData" = enum
        """EnumData: The enumeration data containing configuration sets and lists."""

        self.name: str = name
        """str: The name of the configuration selection. 
        
        This is used to save the selection to a JSON file. For example, if `name` is 
        "main", the selection is saved as in the enumeration directory as 
        `config_selection.main.json`."""

        # Initialize the default cluster expansion ClexDescription

        if clex is None:
            # Use the default cluster expansion from the enumeration's project settings
            clex = self._enum.proj.settings.default_clex
        elif isinstance(clex, str):
            cluster_expansions = self._enum.proj.settings.cluster_expansions
            if clex not in cluster_expansions:
                raise ValueError(
                    f"Cluster expansion '{clex}' not found in project settings."
                )

            clex = cluster_expansions.get(clex)
        elif not isinstance(clex, ClexDescription):
            raise TypeError(
                f"Expected clex to be None, a string, or a ClexDescription, "
                f"got {type(clex)}"
            )

        self.clex: Optional[ClexDescription] = clex
        """Optional[ClexDescription]: The default cluster expansion settings to
        use when getting properties, working with calculations, etc., if present.
        """

        # Read existing records from file if available,
        # otherwise if records are provided, use those,
        # otherwise initialize with all configurations selected

        self._path = (
            pathlib.Path(self._enum.proj.dir.enum_dir(self._enum.id))
            / f"config_selection.{self.name}.json"
        )
        self._path_gz = (
            pathlib.Path(self._enum.proj.dir.enum_dir(self._enum.id))
            / f"config_selection.{self.name}.json.gz"
        )

        if self._path_gz.exists():
            self._gz = True
            records = read_required(path=self._path_gz, gz=True)
        elif self._path.exists():
            self._gz = False
            records = read_required(path=self._path)
        elif records is None:
            self._gz = gz
            records = []

            for record in self._enum.configuration_set:
                # Select all configurations by default
                records.append(
                    {
                        "source": "config_set.json",
                        "name": record.configuration_name,
                        "selected": True,
                    }
                )

            for i, config in enumerate(self._enum.configuration_list):
                # Select all configurations by default
                records.append(
                    {
                        "source": "config_list.json",
                        "name": f"config_list/{i}",
                        "selected": True,
                    }
                )
        else:
            self._gz = gz

        self._records: list[dict] = records
        """list[dict]: Records of selected configurations. Each record is a dict with
        "source", "name", and "selected" keys. Additional keys may be present."""

        # Initialize the index mapping for fast access by name

        self._index_by_name: dict[str, int] = {}
        for i, record in enumerate(self._records):
            name = record["name"]
            if name in self._index_by_name:
                raise ValueError(
                    f"Duplicate configuration name found in records: {name}"
                )
            self._index_by_name[name] = i
        """dict[str, int]: Index of each configuration record by its name."""

        # Initialize the chemical and occupant composition calculators for the default
        # project chemical and occupant composition axes

        self._chemical_comp_calculator = self._enum.proj.make_chemical_comp_calculator()
        """ConfigCompositionCalculator: Chemical composition calculator using the
        default project chemical composition axes.
        
        The "chemical composition" treats all :class:`~libcasm.xtal.Occupant` that
        have the same "chemical name" (:func:`~libcasm.xtal.Occupant.name`) as a
        single component, even if they have different magnetic spin, molecular
        orientation, etc."""

        self._occupant_comp_calculator = self._enum.proj.make_occupant_comp_calculator()
        """ConfigCompositionCalculator: Occupant composition calculator using the
        default project occupant composition axes.
        
        The "occupant composition" treats all :class:`~libcasm.xtal.Occupant` that
        have different magnetic spin, molecular orientation, etc. as distinct
        components.
        """

        # Initialize the correlation calculator for the default cluster expansion
        _corr_calculator = None
        if self.clex is not None:
            bset = self._enum.proj.bset.get(id=self.clex.bset)
            try:
                _corr_calculator = bset.make_corr_calculator()
            except Exception as e:
                if "No basis.json" not in str(e):
                    raise

        self._corr_calculator = _corr_calculator
        """Optional[ConfigCorrCalculator]: The correlations calculator for the default 
        cluster expansion's bset, if available."""

    @property
    def path(self) -> pathlib.Path:
        """pathlib.Path: The path to the configuration selection file."""
        return self._path if not self._gz else self._path_gz

    def commit(self, quiet: bool = False):
        """Save selection to file."""
        safe_dump(
            data=self._records,
            path=self.path,
            force=True,
            quiet=quiet,
            gz=self._gz,
        )

    def remove(self, quiet: bool = False):
        """Remove the selection file from disk."""
        from casm.tools.shared.json_io import printpathstr

        path = self.path
        if not quiet:
            print(f"Removed selection file: {printpathstr(self.path)}")
        if path.exists():
            path.unlink()

    def copy(
        self,
        name: str,
        clex: Union[str, ClexDescription, None] = None,
        clear_clex: bool = False,
    ):
        """Create a copy of the selection with a new name (does not commit).

        Parameters
        ----------
        name: str
            The name to use for the new configuration selection.
        clex: Union[str, ClexDescription, None] = None
            Optionally specify a new cluster expansion to use for the copy. If None, the
            current cluster expansion is used.
        clear_clex: bool = False
            If True, the copy will be created without any cluster expansion. If False
            (default), the cluster expansion used for the copy is determined by `clex`.

        Returns
        -------
        new_config_selection: ConfigSelection
            The new configuration selection with the same records as this one, but
            with a new name and optionally a new cluster expansion.
        """
        import copy

        if clear_clex:
            clex = None
        elif clex is None:
            # Use the current clex if not provided
            clex = self.clex

        return ConfigSelection(
            enum=self._enum,
            name=name,
            clex=clex,
            gz=self._gz,
            records=copy.deepcopy(self._records),
        )

    @property
    def chemical_components(self) -> list[str]:
        """list[str]: The order of components in chemical composition vector
        results."""
        return self._chemical_comp_calculator.components

    @property
    def occupant_components(self) -> list[str]:
        """list[str]: The order of components in occupant composition vector
        results."""
        return self._occupant_comp_calculator.components

    def get(self, name: str) -> Optional[ConfigSelectionRecord]:
        """Get a record by name.

        Parameters
        ----------
        name : str
            The name of the configuration selection record.

        Returns
        -------
        result: Optional[ConfigSelectionRecord]
            The configuration selection record if found, otherwise None.
        """
        index = self._index_by_name.get(name)
        if index is not None:
            return ConfigSelectionRecord(parent=self, data=self._records[index])
        return None

    def select(self, name: str):
        """Select a configuration by name.

        Notes
        -----
        This does not commit the change to disk. You must call `commit()` to save the
        change.

        Parameters
        ----------
        name : str
            The name of the configuration to select.
        """
        record = self.get(name)
        if record is not None:
            record.set_selected(True)
        else:
            raise ValueError(f"Configuration '{name}' not found in selection.")

    def select_all(self):
        """Select all configurations in the selection.

        Notes
        -----
        This does not commit the change to disk. You must call `commit()` to save the
        change.
        """
        for record in self._records:
            record["selected"] = True

    def select_if(self, f: Callable[[ConfigSelectionRecord], bool]):
        """Set some configurations to selected.

        Parameters
        ----------
        f : Callable[[ConfigSelectionRecord], bool]
            A function that takes a ConfigSelectionRecord and returns True if the
            configuration should be changed to be selected. Note that if the function
            returns False, the configuration's selection status is not changed.
        """
        for record in self._records:
            if not record["selected"] and f(ConfigSelectionRecord(self, record)):
                record["selected"] = True

    def set_selected(self, f: Callable[[ConfigSelectionRecord], bool]):
        """Set the selection status of all configurations.

        Parameters
        ----------
        f : Callable[[ConfigSelectionRecord], bool]
            A function that takes a ConfigSelectionRecord and returns True if the
            configuration should be selected, False if the configuration should be
            not selected.
        """
        for record in self._records:
            record["selected"] = f(ConfigSelectionRecord(self, record))

    def deselect(self, name: str):
        """Deselect a configuration by name.

        Notes
        -----
        This does not commit the change to disk. You must call `commit()` to save the
        change.

        Parameters
        ----------
        name : str
            The name of the configuration to deselect.
        """
        record = self.get(name)
        if record is not None:
            record.set_selected(False)
        else:
            raise ValueError(f"Configuration '{name}' not found in selection.")

    def deselect_all(self):
        """Deselect all configurations in the selection.

        Notes
        -----
        This does not commit the change to disk. You must call `commit()` to save the
        change.
        """
        for record in self._records:
            record["selected"] = False

    def deselect_if(self, f: Callable[[ConfigSelectionRecord], bool]):
        """Set some configurations to not selected.

        Parameters
        ----------
        f : Callable[[ConfigSelectionRecord], bool]
            A function that takes a ConfigSelectionRecord and returns True if the
            configuration should be deselected. Note that if the function returns
            False, the configuration's selection status is not changed.
        """
        for record in self._records:
            if record["selected"] and f(ConfigSelectionRecord(self, record)):
                record["selected"] = False

    def erase(self, name_or_names: Union[str, list[str]]):
        """Erase a configuration record by name.

        Notes
        -----
        This does not commit the change to disk. You must call `commit()` to save the
        change.

        Parameters
        ----------
        name_or_names : Union[str, list[str]]
            The name of the configuration to erase, or a list of names to erase.
            If a list is provided, all specified configurations are removed.

            If multiple configurations are going to be erased, it is preferable
            to erase them in a single call so that the name to index table is only
            rebuilt once.

            Configurations should not be erased while iterating over the selection.
        """
        if isinstance(name_or_names, str):
            name_or_names = [name_or_names]

        for name in name_or_names:
            index = self._index_by_name.pop(name, None)
            if index is not None:
                del self._records[index]
            else:
                raise ValueError(f"Configuration '{name}' not found in selection.")

        # Update the index mapping after all deletions
        self._index_by_name = {rec["name"]: i for i, rec in enumerate(self._records)}

    def insert(
        self,
        name: str,
        source: str,
        selected: bool = True,
        **kwargs,
    ):
        """Insert a new configuration record into the selection.

        Notes
        -----
        This does not commit the change to disk. You must call `commit()` to save the
        change.

        Parameters
        ----------
        name : str
            The name of the configuration. Should be
            :py:attr:`ConfigurationRecord.configuration_name` for members of
            the enumeration's configuration set, or a string like "config_list/0" for
            members of the enumeration's configuration list.
        source : str
            The source of the configuration, either "config_set.json" or
            "config_list.json".
        selected : bool = True
            Whether the configurations added are selected or not selected.
        **kwargs : Any
            Additional key-value pairs to include in the record. These should be
            JSON serializable.

        Raises
        ------
        ValueError
            If the source is not one of "config_set.json" or "config_list.json", or if
            the configuration name already exists in the selection.

        """
        if source not in {"config_set.json", "config_list.json"}:
            raise ValueError(
                f"Invalid source '{source}'. "
                "Must be 'config_set.json' or 'config_list.json'."
            )

        if name in self._index_by_name:
            raise ValueError(f"Configuration '{name}' already exists in selection.")

        record = {
            "source": source,
            "name": name,
            "selected": selected,
            **kwargs,
        }
        self._records.append(record)
        self._index_by_name[name] = len(self._records) - 1

    def insert_all(
        self,
        selected: bool = True,
    ):
        """Insert all configurations from the enumeration into the selection that are
        not already present.

        Notes
        -----
        This does not commit the change to disk. You must call `commit()` to save the
        change.

        Parameters
        ----------
        selected : bool = True
            Whether the configurations added are selected or not selected.
            Defaults to True, meaning all configurations inserted are selected.
        """
        source = "config_set.json"
        for record in self._enum.configuration_set:
            if record.configuration_name not in self._index_by_name:
                self.insert(
                    name=record.configuration_name,
                    source=source,
                    selected=selected,
                )

        source = "config_list.json"
        for i, config in enumerate(self._enum.configuration_list):
            name = f"config_list/{i}"
            if name not in self._index_by_name:
                self.insert(
                    name=name,
                    source=source,
                    selected=selected,
                )

    def clean(self):
        """Clean the selection by removing any configurations that are no longer in
        the enumeration.

        Notes
        -----
        This does not commit the change to disk. You must call `commit()` to save the
        change.
        """
        new_records = []
        new_index_by_name = {}

        for record in self._records:
            if record["source"] == "config_set.json":
                result = self._enum.configuration_set.get_by_name(record["name"])
                if result is not None:
                    new_records.append(record)
                    new_index_by_name[record["name"]] = len(new_records) - 1
            elif record["source"] == "config_list.json":
                index = int(record["name"].split("/")[-1])
                if index < len(self._enum.configuration_list):
                    new_records.append(record)
                    new_index_by_name[record["name"]] = len(new_records) - 1
            else:
                source = record["source"]
                raise ValueError(f"Unsupported source: {source}")

        self._records = new_records
        self._index_by_name = new_index_by_name

    def __len__(self) -> int:
        """Return the number of configuration records in the selection."""
        return len(self._records)

    def __iter__(self):
        """Iterate over the selected configuration records."""
        for record in self.selected:
            yield record

    @property
    def all(self):
        """AllRecords: An iterable of all configuration records in the selection.

        .. rubric:: Example Usage

        .. code-block:: Python

            for record in selection.all:
                print(record.name, record.is_selected)

        """
        return AllRecords(self)

    @property
    def selected(self):
        """SelectedRecords: An iterable of selected configuration records in the
        selection.

        .. rubric:: Example Usage

        .. code-block:: Python

            # Note that this is equivalent to using `for record in selection`
            for record in selection.selected:
                print(record.name, record.is_selected)

        """
        return SelectedRecords(self)

    @property
    def unselected(self):
        """UnselectedRecords: An iterable of unselected configuration records in the
        selection.

        .. rubric:: Example Usage

        .. code-block:: Python

            for record in selection.unselected:
                print(record.name, record.is_selected)

        """
        return UnselectedRecords(self)

    @property
    def n_selected(self) -> int:
        """int: The number of selected configurations in the selection."""
        return sum(1 for record in self._records if record["selected"])

    @property
    def n_unselected(self) -> int:
        """int: The number of unselected configurations in the selection."""
        return len(self._records) - self.n_selected

    @property
    def n_total(self) -> int:
        """int: The total number of configurations in the selection (equivalent to
        using `len`)."""
        return len(self._records)

    def run_subprocess(
        self,
        args: Union[str, list[str], list[list[str]]],
        write_log: bool = False,
        shell: bool = False,
    ):
        """Run a subprocess command in the calculation directory for each selected
        configuration.

        Parameters
        ----------
        args: Union[str, list[str], list[list[str]]]
            The arguments to run for one or more subprocesses. The subprocesses will be
            run in the calculation directory for each selected configuration.

            By default (if `shell` is False), a `list[str]` provides the arguments for
            one subprocess call and a `list[list[str]]` provides the arguments for a
            sequence of subprocess calls. If `shell` is True, a single `str` provides
            the command to run in a single subprocess, and a `list[str]` provides the
            commands to run in a sequence of subprocesses.

        write_log: bool = True
            If True, write the standard output and error of the command to files named
            `<log_base>.out.txt` and `<log_base>.err.txt` in the working
            directory. If False, the output is printed to the console.

        shell: bool = False
            If True, the specified command will be executed through the shell.
        """
        for record in self.selected:
            record.run_subprocess(
                args=args,
                write_log=write_log,
                shell=shell,
            )

    def run_shell_script(
        self,
        script: pathlib.Path,
        write_log: bool = True,
    ):
        """Run a shell script in the calculation directory for each selected
        configuration.

        Parameters
        ----------
        config_selection: ConfigSelection
            A selection of Configurations to run the script for. All selected
            configurations will have the script run.
        script: pathlib.Path
            The path to the shell script to run. The script will be copied into the
            the calculation directory for each selected configuration. The script will
            then be run with the working directory set to the calculation directory.
            The shell to use is determined by the `SHELL` environment variable,
            defaulting to `/bin/bash`.
        write_log: bool = True
            If True, write the standard output and error of the script to files named
            `<script_name>.out.txt` and `<script_name>.err.txt` in the calculation
            directory. If False, the output is printed to the console.
        """
        for record in self.selected:
            record.run_shell_script(
                script=script,
                write_log=write_log,
            )

    def run_python_script(
        self,
        script: pathlib.Path,
        write_log: bool = True,
    ):
        """Run a Python script in the calculation directory for each selected
        configuration.

        Parameters
        ----------
        config_selection: ConfigSelection
            A selection of Configurations to run the script for. All selected
            configurations will have the script run.
        script: pathlib.Path
            The path to the Python script to run. The script will be copied into the
            calculation directory for each selected configuration. The script will then
            be run with the working directory set to the calculation directory.
        write_log: bool = True
            If True, write the standard output and error of the script to files named
            `<script_name>.out.txt` and `<script_name>.err.txt` in the calculation
            directory. If False, the output is printed to the console.
        """
        for record in self.selected:
            record.run_python_script(
                script=script,
                write_log=write_log,
            )

    def __repr__(self):
        """Return a string representation of the selection."""
        s = "ConfigSelection:\n"
        s += f"- name: {self.name}\n"
        s += f"- enum: {self._enum.id}\n"
        s += f"- clex: {self.clex.name if self.clex else 'None'}\n"
        if self.clex is not None:
            s += f"  - calctype: {self.clex.calctype}\n"
            s += f"  - ref: {self.clex.ref}\n"
            s += f"  - bset: {self.clex.bset}\n"
            s += f"  - eci: {self.clex.eci}\n"
        s += f"- n_total: {self.n_total}\n"
        s += f"- n_selected: {self.n_selected}\n"
        s += f"- n_unselected: {self.n_unselected}"
        return s

    def tabulate_calc_status(self):
        """Collect and print a table of calculation statuses for selected
        configurations.

        .. rubric:: Example Output

        .. code-block:: text

            Status      Count
            --------  -------
            none            0
            setup           0
            started         0
            stopped         0
            complete      214


        """
        from tabulate import tabulate

        status_count = dict()
        for record in self.selected:
            status = record.calc_status
            if status in status_count:
                status_count[status] += 1
            else:
                status_count[status] = 1

        headers = ["Status", "Count"]
        status_list = [
            "none",
            "setup",
            "submitted",
            "started",
            "canceled",
            "stopped",
            "complete",
        ]
        for status in status_count:
            if status not in status_list:
                status_list.append(status)

        data = []
        for status in status_list:
            data.append([status, status_count.get(status, 0)])

        print(tabulate(data, headers=headers))
