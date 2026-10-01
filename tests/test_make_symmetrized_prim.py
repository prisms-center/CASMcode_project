import casm.project
import libcasm.xtal as xtal


def test_make_symmetrized_prim_diamond():
    prim = xtal.Prim.from_dict(
        {
            "basis": [
                {"coordinate": [0.0, 0.0, 0.0], "occupants": ["Si"]},
                {"coordinate": [0.25, 0.25, 0.25], "occupants": ["Si"]},
            ],
            "coordinate_mode": "Fractional",
            "lattice_vectors": [
                [0.0, 2.72, 2.72],
                [2.72, 0.0, 2.72],
                [2.72, 2.72, 0.0],
            ],
            "title": "Si",
        }
    )

    fg_1 = xtal.make_factor_group(prim)
    assert len(fg_1) == 48

    symmetrized_prim = casm.project.make_symmetrized_prim(
        prim=prim,
        tol=1e-5,
    ).xtal_prim

    fg_2 = xtal.make_factor_group(symmetrized_prim)
    assert len(fg_2) == 48
