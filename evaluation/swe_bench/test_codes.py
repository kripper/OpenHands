def get_test_code(instance_id: str):
    test_codes = {
        'astropy__astropy-12907': """
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
        'astropy__astropy-14182': r"""
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
actual,expected=out.getvalue().splitlines(),lines
if actual != expected:
    print("Expected:")
    print('\\n'.join(expected))
    print("Got:")
    print('\\n'.join(actual))
    import difflib
    print('Diff:')
    for line in difflib.unified_diff(actual, expected, fromfile='actual output', tofile='expected output', lineterm=''):
        print(line)

    assert actual == expected, "Output does not match expected structure"
""",
        'astropy__astropy-14539': r"""
from astropy.io import fits
col = fits.Column('a', format='QD', array=[[0], [0, 0]])
hdu = fits.BinTableHDU.from_columns([col])
hdu.writeto('/testbed/diffbug.fits', overwrite=True)

print(fits.FITSDiff('diffbug.fits', 'diffbug.fits').identical)
fits.printdiff('diffbug.fits', 'diffbug.fits')
assert fits.FITSDiff('diffbug.fits', 'diffbug.fits').identical
""",
        'django__django-11133': r"""from django.conf import settings;
settings.configure(DEFAULT_CHARSET='utf-8');
from django.http import HttpResponse
# memoryview content
response = HttpResponse(memoryview(b"My Content"))
print(response.content)

assert response.content == b"My Content"
""",
    }
    return test_codes.get(instance_id, '')


if __name__ == '__main__':
    print(get_test_code('django__django-11133'))
