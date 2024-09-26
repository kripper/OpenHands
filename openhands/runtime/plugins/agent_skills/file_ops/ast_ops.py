import ast
import os

import libcst as cst


# Converting the AST 'arguments' object to a readable format
def format_signature(args):
    return [arg.arg for arg in args.args]


class BaseClassInitFinder(ast.NodeVisitor):
    def __init__(self):
        self.init_signature = None

    def visit_FunctionDef(self, node):
        # Find the __init__ method and get its signature
        if node.name == '__init__':
            self.init_signature = node.args
        return node


def find_imported_base_class(code, class_name):
    tree = ast.parse(code)
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == class_name:
                    return node.module
    return None


def read_file(file_path):
    with open(file_path, 'r') as f:
        return f.read()


def find_base_class_file(file_path, base_class_module):
    # Assuming the module is in the current working directory or a standard path
    dir_name = os.path.dirname(file_path)
    if dir_name == '':
        dir_name = os.getcwd()
    possible_paths = [
        os.path.join(dir_name, base_class_module.replace('.', '/') + '.py'),
        # You can add more paths if necessary
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None


def get_base_class_init_signature_from_code(code, class_name):
    tree = ast.parse(code)
    finder = BaseClassInitFinder()

    # Traverse to find the class definition
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            finder.visit(node)
            break

    return finder.init_signature


def process_file_for_base_class_init(file_path, base_class_name):
    code = read_file(file_path)
    return get_base_class_init_signature_from_code(code, base_class_name)


# Example usage
def get_base_class_init_signature(file_path, base_class_name):
    current_code = read_file(file_path)
    base_class_module = find_imported_base_class(current_code, base_class_name)
    if base_class_module:
        base_class_file = find_base_class_file(file_path, base_class_module)
        if base_class_file:
            base_init_signature = process_file_for_base_class_init(
                base_class_file, base_class_name
            )
            if base_init_signature:
                formatted_signature = format_signature(base_init_signature)
                return formatted_signature
            else:
                return None
        else:
            print('Base class file not found.')
    else:
        print('Base class is not imported.')


class BaseClassFinder(ast.NodeVisitor):
    def __init__(self):
        self.base_class_name = None

    def visit_ClassDef(self, node):
        # Check if the class has a base class
        if node.bases:
            self.base_class_name = node.bases[
                0
            ].id  # Assume the first base class is the one we want
        return node


def get_base_class_name(file_path, class_name):
    code = read_file(file_path)
    tree = ast.parse(code)
    finder = BaseClassFinder()

    # Traverse to find the class definition
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            finder.visit(node)
            break

    return finder.base_class_name


class InitMethodModifier(cst.CSTTransformer):
    def __init__(self, file_path, class_name, param_name):
        self.file_path = file_path
        self.class_name = class_name
        self.param_name = param_name
        self.inside_target_class = False

    def readable_params(self, params):
        return [param.name.value for param in params]

    def readable_args(self, args):
        return [arg.keyword.value for arg in args]

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        # Modify only if we are inside the target class's __init__ method
        if self.inside_target_class and original_node.name.value == '__init__':
            # Add the new parameter to the __init__ method
            new_param = cst.Param(cst.Name(self.param_name))
            if self.param_name not in self.readable_params(updated_node.params.params):
                new_params = updated_node.params.with_changes(
                    params=[*updated_node.params.params, new_param]
                )

                # Update the __init__ function with the new parameter
                return updated_node.with_changes(params=new_params)
            else:
                print(
                    f'{self.param_name} already present in the __init__ method of the {self.class_name} class in the {self.file_path} file.'
                )
                self.already_added = True

        return updated_node

    def leave_ClassDef(self, original_node: cst.ClassDef, updated_node: cst.ClassDef):
        # Exit the target class after processing
        self.inside_target_class = False
        return updated_node

    def visit_ClassDef(self, node: cst.ClassDef):
        # Enter the target class
        if node.name.value == self.class_name:
            self.inside_target_class = True

    def leave_Expr(self, original_node: cst.Expr, updated_node: cst.Expr) -> cst.Expr:
        # if self.already_added:
        # return updated_node
        if self.param_name not in (
            get_base_class_init_signature(
                self.file_path, get_base_class_name(self.file_path, self.class_name)
            )
            or []
        ):
            return updated_node
        # Modify the super().__init__ call to include the new parameter
        if self.inside_target_class and isinstance(original_node.value, cst.Call):
            if isinstance(original_node.value.func, cst.Attribute):
                if original_node.value.func.attr.value == '__init__':
                    # Check if existing arguments contain keyword arguments
                    has_keyword_args = any(
                        isinstance(arg, cst.Arg) and arg.keyword
                        for arg in original_node.value.args
                    )
                    # if the param is already present, do not add it again
                    if self.param_name in self.readable_args(original_node.value.args):
                        return updated_node
                    if has_keyword_args:
                        # Add the new parameter as a keyword argument to avoid positional after keyword error
                        new_arg = cst.Arg(
                            keyword=cst.Name(self.param_name),
                            value=cst.Name(self.param_name),
                        )
                    else:
                        # Add the new parameter as a positional argument
                        new_arg = cst.Arg(value=cst.Name(self.param_name))

                    new_args = [*original_node.value.args, new_arg]
                    new_call = updated_node.value.with_changes(args=new_args)
                    return updated_node.with_changes(value=new_call)

        return updated_node


def add_param_to_init_in_subclass(file_path, class_name, param_name):
    """
    This function adds a new parameter to the __init__ method of a specified sub class in a given file and adds it to the super().__init__ call automatically by checking if the parameter is present in the base class __init__ method using AST.

    Args:
        file_path (str): The path to the file containing the class.
        class_name (str): The name of the subclass to modify.
        param_name (str): The name of the new parameter to add to the __init__ method.

    """
    code = read_file(file_path)
    # Parse the code into a CST tree
    tree = cst.parse_module(code)

    # Create the transformer to modify the __init__ method
    transformer = InitMethodModifier(file_path, class_name, param_name)

    # Apply the transformation
    modified_tree = tree.visit(transformer)
    new_code = modified_tree.code
    if new_code != code:
        with open(file_path, 'w') as f:
            f.write(modified_tree.code)
        print(
            f'{param_name} added to the __init__ method of the {class_name} class in the {file_path} file.'
        )


if __name__ == '__main__':
    file_name = r'C:\Users\smart\Desktop\GD\astropy\astropy\io\ascii\rst.py'
    # print(get_base_class_init_signature(file_path, "FixedWidth"))

    add_param_to_init_in_subclass(file_name, 'RST', 'header_rows')
