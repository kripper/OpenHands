import ast

from openhands.runtime.plugins.agent_skills.file_ops.file_utils import (
    find_base_class_file,
)


def find_imported_base_class(code, class_name):
    """Find the module from which a base class is imported."""
    tree = ast.parse(code)
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == class_name:
                    return node.module or alias.name
    return None


def find_base_classes_without_slots(file_path, target_class):
    """
    Recursively checks all base classes of a given class, including external imports,
    to identify which lack a __slots__ attribute.

    Parameters:
    file_path (str): The path to the file where the initial code is located.
    target_class (str): The name of the class to check.

    Returns:
    list: A list of base classes in the entire inheritance chain of the target class that do not have __slots__.
    """
    with open(file_path, 'r') as file:
        code = file.read()
    tree = ast.parse(code)
    class_defs = {
        node.name: node for node in tree.body if isinstance(node, ast.ClassDef)
    }
    bases_without_slots = []
    loaded_classes = {}  # Cache for loaded external classes

    def has_slots_attribute(node):
        """Checks if a class node or imported class has the __slots__ attribute."""
        if isinstance(node, ast.ClassDef):
            for stmt in node.body:
                if isinstance(stmt, ast.Assign) and any(
                    target.id == '__slots__'
                    for target in stmt.targets
                    if isinstance(target, ast.Name)
                ):
                    return True
            return False
        else:
            return hasattr(node, '__slots__')

    def load_external_class_from_file(base_name, base_class_module):
        """Attempt to load an external class by finding its file and parsing it."""
        base_class_file = find_base_class_file(file_path, base_class_module)
        if base_class_file and base_class_file not in loaded_classes:
            with open(base_class_file, 'r') as file:
                external_code = file.read()
                external_tree = ast.parse(external_code)
                for node in external_tree.body:
                    if isinstance(node, ast.ClassDef):
                        class_defs[node.name] = (
                            node  # Add the class to local definitions
                        )
            loaded_classes[base_class_file] = (
                external_code  # Cache file content for reuse
            )
        return class_defs.get(base_name), loaded_classes.get(base_class_file)

    def check_base_classes(class_name, current_code):
        """Recursively checks each base class for the __slots__ attribute."""
        if class_name in class_defs:
            node = class_defs[class_name]
            for base in node.bases:
                base_name = base.id if isinstance(base, ast.Name) else None
                if base_name:
                    # Check if the base class is defined locally or needs to be imported
                    base_node = class_defs.get(base_name)
                    if not base_node:
                        base_class_module = find_imported_base_class(
                            current_code, base_name
                        )
                        if base_class_module:
                            base_node, external_code = load_external_class_from_file(
                                base_name, base_class_module
                            )
                            if external_code:
                                check_base_classes(base_name, external_code)

                    if base_node:
                        if (
                            not has_slots_attribute(base_node)
                            and base_name not in bases_without_slots
                        ):
                            bases_without_slots.append(base_name)
                        check_base_classes(base_name, current_code)
                    else:
                        print(
                            f"Base class '{base_name}' for not found in the code or imported module."
                        )
        else:
            print(f"Class '{class_name}' not found in the code.")

    # Start with the target class and initial code
    if target_class in class_defs:
        check_base_classes(target_class, code)

    if bases_without_slots:
        print('The following base classes lack __slots__:')
        for base in bases_without_slots:
            print(base)
    else:
        print('No base classes lack __slots__')


if __name__ == '__main__':
    # Usage example
    file_name = r'C:\Users\smart\Desktop\GD\sympy\sympy\core\symbol.py'
    (
        find_base_classes_without_slots(
            file_name,
            'Symbol',
        )
    )
