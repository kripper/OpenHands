def get_test_code(instance_id: str):
    test_codes = {
        'astropy__astropy-12907': """
import os
os.chdir('/testbed')
from astropy.modeling import models as m
from astropy.modeling.separable import separability_matrix

cm = m.Linear1D(10) & m.Linear1D(5)

a= separability_matrix(m.Pix2Sky_TAN() & cm)

import numpy as np

expected_matrix = np.array([[ True,  True, False, False],
                            [ True,  True, False, False],
                            [False, False,  True,  False],
                            [False, False,  False,  True]])

assert np.array_equal(a, expected_matrix), "Matrix does not match expected structure"
""",
        'astropy__astropy-14182': """
from astropy.table import QTable
import astropy.units as u
import numpy as np
from io import StringIO

import sys
lines = [
    "======= ======== ====",
    "   wave response ints",
    "     nm       ct     ",
    "float64  float32 int8",
    "======= ======== ====",
    "  350.0      1.0    1",
    "  950.0      2.0    2",
    "======= ======== ====",
]
tbl = QTable.read(lines, format="ascii.rst", header_rows=["name", "unit", "dtype"])
assert tbl["wave"].unit == u.nm
assert tbl["response"].unit == u.ct
assert tbl["wave"].dtype == np.float64
assert tbl["response"].dtype == np.float32
assert tbl["ints"].dtype == np.int8

out = StringIO()
tbl.write(out, format="ascii.rst", header_rows=["name", "unit", "dtype"])
assert out.getvalue().splitlines() == lines
""",
    }
    return test_codes.get(instance_id, '')


if __name__ == '__main__':
    print(get_test_code('astropy__astropy-14182'))
