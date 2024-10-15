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
if response.content != b"My Content":
    print(response.content)

assert response.content == b"My Content"
""",
        'psf__requests-2317': r"""
import requests

url = "https://httpbin.org/get"
method = b'GET'
response = requests.request(method, url)
if response.status_code != 200:
    print('Status code:', response.status_code)
assert response.status_code == 200
""",
        'sympy__sympy-13647': r"""
import sympy as sm
M = sm.eye(6)
V = 2 * sm.ones(6, 2)
result = M.col_insert(3, V)
assert result == sm.Matrix([[1, 0, 0, 2, 2, 0, 0, 0], [0, 1, 0, 2, 2, 0, 0, 0], [0, 0, 1, 2, 2, 0, 0, 0], [0, 0, 0, 2, 2, 1, 0, 0], [0, 0, 0, 2, 2, 0, 1, 0], [0, 0, 0, 2, 2, 0, 0, 1]])
""",
        'sympy__sympy-21379': r"""
from sympy import *
from sympy.core.cache import clear_cache

x, y, z = symbols('x y z', real=True)

clear_cache()
expr = exp(sinh(Piecewise((x, y > x), (y, True)) / z))
print(expr.subs({1: 1.0}))

""",
        'sympy__sympy-22714': r"""
import sympy as sp
with sp.evaluate(False):
  sp.S('Point2D(Integer(1),Integer(2))')
""",
        'sympy__sympy-23262': r"""
from sympy import lambdify
import inspect

output = inspect.getsource(lambdify([], tuple([1])))
assert output == 'def _lambdifygenerated():\\n    return (1,)\\n', f'Got:\\n{output}'
""",
        'sympy__sympy-24066': r"""
from sympy import exp
from sympy.physics import units
from sympy.physics.units.systems.si import SI

expr = units.second / (units.ohm * units.farad)
dim = SI._collect_factor_and_dimension(expr)[1]

assert SI.get_dimension_system().is_dimensionless(dim)

buggy_expr = 100 + exp(expr)
print(SI._collect_factor_and_dimension(buggy_expr))
""",
        'scikit-learn__scikit-learn-13142': r"""
import numpy as np
from sklearn.mixture import GaussianMixture
from sklearn.utils.testing import assert_array_equal
X = np.random.randn(1000, 5)
gm = GaussianMixture(n_components=5, n_init=5)
c1 = gm.fit_predict(X)
c2 = gm.predict(X)
assert_array_equal(c1, c2)
""",
        'scikit-learn__scikit-learn-14087': r"""
import sys
import sklearn
from sklearn.linear_model import LogisticRegressionCV
import numpy as np

np.random.seed(29)
X = np.random.normal(size=(1000, 3))
beta = np.random.normal(size=3)
intercept = np.random.normal(size=None)
y = np.sign(intercept + X @ beta)

LogisticRegressionCV(cv=5, solver='saga', tol=1e-2, refit=False).fit(X, y)
""",
        'scikit-learn__scikit-learn-14983': r"""
from sklearn.model_selection import RepeatedKFold, RepeatedStratifiedKFold
cond = repr(RepeatedKFold()) == 'RepeatedKFold(n_repeats=10, n_splits=5, random_state=None)'
if not cond:
    print(repr(RepeatedKFold()))
    assert repr(RepeatedKFold()) == 'RepeatedKFold(n_repeats=10, n_splits=5, random_state=None)'
cond = repr(RepeatedStratifiedKFold()) == 'RepeatedStratifiedKFold(n_repeats=10, n_splits=5, random_state=None)'
if not cond:
    print(repr(RepeatedStratifiedKFold()))
    assert repr(RepeatedStratifiedKFold()) == 'RepeatedStratifiedKFold(n_repeats=10, n_splits=5, random_state=None)'
""",
    }
    return test_codes.get(instance_id, '')


if __name__ == '__main__':
    print(get_test_code('django__django-11133'))
