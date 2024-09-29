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
    return description
