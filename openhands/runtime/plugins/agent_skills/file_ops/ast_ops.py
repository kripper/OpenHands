import ast
import os


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


def find_base_class_file(base_class_module):
    # Assuming the module is in the current working directory or a standard path
    dir_name = os.path.dirname(file_name)
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
        base_class_file = find_base_class_file(base_class_module)
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


def get_base_class_name(file_name, class_name):
    code = read_file(file_name)
    tree = ast.parse(code)
    finder = BaseClassFinder()

    # Traverse to find the class definition
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            finder.visit(node)
            break

    return finder.base_class_name


class SelectiveClassInitModifier(ast.NodeTransformer):
    def __init__(self, file_name, class_name, param_name):
        self.file_name = file_name
        self.class_name = class_name
        self.param_name = param_name

    def visit_ClassDef(self, node):
        # Only modify the specified class
        if node.name == self.class_name:
            for n in node.body:
                if isinstance(n, ast.FunctionDef) and n.name == '__init__':
                    self.visit_FunctionDef(n)
        return node

    def visit_FunctionDef(self, node):
        # Add the new parameter to the __init__ method
        new_param = ast.arg(arg=self.param_name, annotation=None)
        node.args.args.append(new_param)

        # Add the parameter to the super().__init__ call

        if self.param_name in get_base_class_init_signature(
            self.file_name, get_base_class_name(self.file_name, self.class_name)
        ):
            for n in node.body:
                if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call):
                    if (
                        isinstance(n.value.func, ast.Attribute)
                        and n.value.func.attr == '__init__'
                    ):
                        kw = ast.keyword(
                            arg=self.param_name,
                            value=ast.Name(id=self.param_name, ctx=ast.Load()),
                        )
                        n.value.keywords.append(kw)
        return node


def add_param_to_init_in_subclass(file_name, class_name, param_name):
    """
    This function adds a new parameter to the __init__ method of a specified sub class in a given file and adds it to the super().__init__ call if the parameter is present in the base class __init__ method using AST.

    Args:
        file_name (str): The path to the file containing the class.
        class_name (str): The name of the subclass to modify.
        param_name (str): The name of the new parameter to add to the __init__ method.

    Returns:
        str: The modified code with the new parameter added to the __init__ method.
    """
    code = read_file(file_name)
    tree = ast.parse(code)
    modifier = SelectiveClassInitModifier(file_name, class_name, param_name)
    modified_tree = modifier.visit(tree)
    return ast.unparse(modified_tree)


if __name__ == '__main__':
    file_name = r'C:\Users\smart\Desktop\GD\astropy\astropy\io\ascii\rst.py'
    # print(get_base_class_init_signature(file_name, "FixedWidth"))

    modified_code_class_one = add_param_to_init_in_subclass(
        file_name, 'RST', 'header_rows'
    )
    print(modified_code_class_one)
