def update_issue_description(description: str, instance_id: str) -> str:
    description = description.replace('\r\n', '\n')
    if instance_id == 'astropy__astropy-14182':
        actual = """Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "/usr/lib/python3/dist-packages/astropy/table/connect.py", line 129, in __call__
    self.registry.write(instance, *args, **kwargs)
  File "/usr/lib/python3/dist-packages/astropy/io/registry/core.py", line 369, in write
    return writer(data, *args, **kwargs)
  File "/usr/lib/python3/dist-packages/astropy/io/ascii/connect.py", line 26, in io_write
    return write(table, filename, **kwargs)
  File "/usr/lib/python3/dist-packages/astropy/io/ascii/ui.py", line 856, in write
    writer = get_writer(Writer=Writer, fast_writer=fast_writer, **kwargs)
  File "/usr/lib/python3/dist-packages/astropy/io/ascii/ui.py", line 800, in get_writer
    writer = core._get_writer(Writer, fast_writer, **kwargs)
  File "/usr/lib/python3/dist-packages/astropy/io/ascii/core.py", line 1719, in _get_writer
    writer = Writer(**writer_kwargs)
TypeError: RST.__init__() got an unexpected keyword argument 'header_rows"""
        expected = """Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "/usr/lib/python3/dist-packages/astropy/table/connect.py", line 130, in __call__
    self.registry.write(instance, *args, **kwargs)
  File "/usr/lib/python3/dist-packages/astropy/io/registry/core.py", line 385, in write
    return writer(data, *args, **kwargs)
  File "/usr/lib/python3/dist-packages/astropy/io/ascii/connect.py", line 28, in io_write
    return write(table, filename, **kwargs)
  File "/usr/lib/python3/dist-packages/astropy/io/ascii/ui.py", line 975, in write
    writer = get_writer(Writer=Writer, fast_writer=fast_writer, **kwargs)
  File "/usr/lib/python3/dist-packages/astropy/io/ascii/ui.py", line 901, in get_writer
    writer = core._get_writer(Writer, fast_writer, **kwargs)
  File "/usr/lib/python3/dist-packages/astropy/io/ascii/core.py", line 1815, in _get_writer
    writer = Writer(**writer_kwargs)
TypeError: RST.__init__() got an unexpected keyword argument 'header_rows"""
        print('Updating issue description')
        return description.replace(actual, expected)

    elif instance_id == 'astropy__astropy-13236':
        actual = '- Add a FutureWarning here telling the user to wrap `data` in `Column` and that in the future (5.2) the structured array will be added as a `Column`.\n'
        return description.replace(actual, '')
    elif instance_id == 'astropy__astropy-14995':
        actual = '...'
        expected1 = """Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "/testbed/astropy/nddata/mixins/ndarithmetic.py", line 618, in multiply
    return self._prepare_then_do_arithmetic(
  File "/testbed/astropy/nddata/mixins/ndarithmetic.py", line 731, in _prepare_then_do_arithmetic
    result, init_kwds = operand._arithmetic(operation, operand2, **kwargs)
  File "/testbed/astropy/nddata/mixins/ndarithmetic.py", line 335, in _arithmetic
    kwargs["mask"] = self._arithmetic_mask(
  File "/testbed/astropy/nddata/mixins/ndarithmetic.py", line 527, in _arithmetic_mask
    return handle_mask(self.mask, operand.mask, **kwds)
TypeError: unsupported operand type(s) for |: 'int' and 'NoneType'
"""
        expected2 = """Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "/testbed/astropy/nddata/mixins/ndarithmetic.py", line 618, in multiply
    return self._prepare_then_do_arithmetic(
  File "/testbed/astropy/nddata/mixins/ndarithmetic.py", line 734, in _prepare_then_do_arithmetic
    result, init_kwds = cls._arithmetic(
  File "/testbed/astropy/nddata/mixins/ndarithmetic.py", line 335, in _arithmetic
    kwargs["mask"] = self._arithmetic_mask(
  File "/testbed/astropy/nddata/mixins/ndarithmetic.py", line 527, in _arithmetic_mask
    return handle_mask(self.mask, operand.mask, **kwds)
TypeError: unsupported operand type(s) for |: 'int' and 'NoneType'
"""
        for expected in [expected1, expected2]:
            description = description.replace(actual, expected, 1)
    elif instance_id == 'scikit-learn__scikit-learn-13779':
        actual = "AttributeError: 'NoneType' object has no attribute 'fit'"
        expected = """Traceback (most recent call last):
  File "test_task.py", line 15, in <module>
    voter.fit(X, y, sample_weight=np.ones(y.shape))
  File "/testbed/sklearn/ensemble/voting.py", line 273, in fit
    return super().fit(X, transformed_y, sample_weight)
  File "/testbed/sklearn/ensemble/voting.py", line 81, in fit
    if not has_fit_parameter(step, 'sample_weight'):
  File "/testbed/sklearn/utils/validation.py", line 808, in has_fit_parameter
    return parameter in signature(estimator.fit).parameters
AttributeError: 'NoneType' object has no attribute 'fit'"""
        return description.replace(actual, expected)

    elif instance_id == 'matplotlib__matplotlib-24970':
        return description + '\nEnable the warnings e.g., python -W always <file>.py'
    elif instance_id == 'django__django-12708':
        return description.replace('378', '411')
    elif instance_id == 'django__django-14155':
        return description.replace(
            'ISTM that we can simply unwrap functools.partial objects in ResolverMatch.__init__().',
            '',
        )
    return description
