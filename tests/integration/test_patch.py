diffs = r"""
-Creates and opens a new file with the given name.
+Creates a file with the given name.
""".strip().splitlines()

test_patces = {'': ''}
for i in range(0, len(diffs), 2):
    test_patces[diffs[i][1:]] = diffs[i + 1][1:]

if __name__ == '__main__':
    print(test_patces)
