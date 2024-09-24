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

lines = '''
===== ========
 wave response
 nm       ct
===== ========
350.0      0.7
950.0      1.2
===== ========
'''.strip().splitlines()
from astropy.table import QTable
import astropy.units as u
from io import StringIO

tbl = QTable({'wave': [350, 950] * u.nm, 'response': [0.7, 1.2]*u.count})

out = StringIO()
tbl.write(out,  format="ascii.rst", header_rows=["name", "unit"])
assert out.getvalue().splitlines() == lines
""",
    }
    return test_codes.get(instance_id, '')


if __name__ == '__main__':
    print(get_test_code('astropy__astropy-14182'))
