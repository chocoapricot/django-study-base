import os
import ast
import subprocess
import re

# Django-specific names that might be used implicitly
DJANGO_SPECIAL_METHODS = {
    'get_absolute_url',
    '__str__',
    '__unicode__',
    'save',
    'delete',
    'clean',
    'validate_unique',
    'get_queryset',
    'get_context_data',
    'form_valid',
    'form_invalid',
    'get_success_url',
    'get_object',
    'get_form_class',
    'get_form',
    'get_initial',
    'setup',
    'dispatch',
    'http_method_not_allowed',
    'get_template_names',
    'create', 'update', 'delete',
    'to_representation', 'to_internal_value',
}

def get_python_files(root_dir):
    """Recursively finds all Python files in a directory."""
    py_files = []
    for root, _, files in os.walk(root_dir):
        for file in files:
            if file.endswith('.py'):
                py_files.append(os.path.join(root, file))
    return py_files

def separate_files(files):
    """Separates files into production and test files."""
    prod_files = []
    test_files = []
    for f in files:
        if '/tests/' in f or f.startswith('tests/'):
            test_files.append(f)
        else:
            prod_files.append(f)
    return prod_files, test_files

class FunctionVisitor(ast.NodeVisitor):
    """AST visitor to find function and class method definitions."""
    def __init__(self, filepath):
        self.filepath = filepath
        self.functions = []
        self.current_class = None

    def visit_ClassDef(self, node):
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = None

    def visit_FunctionDef(self, node):
        # Ignore private methods for now
        if not node.name.startswith('_'):
             self.functions.append({
                'name': node.name,
                'file': self.filepath,
                'class': self.current_class,
                'lineno': node.lineno
            })
        self.generic_visit(node)

def get_definitions(files):
    """Parses files to get all function and method definitions."""
    definitions = []
    for f in files:
        try:
            with open(f, 'r', encoding='utf-8') as reader:
                content = reader.read()
                # DEBUGGING
                if "get_qa_text" in content:
                    print(f"\n[DEBUG] Found 'get_qa_text' in file content of {f}")

                tree = ast.parse(content, filename=f)
                visitor = FunctionVisitor(f)
                visitor.visit(tree)

                # DEBUGGING
                for func in visitor.functions:
                    if func['name'] == 'get_qa_text':
                        print(f"\n[DEBUG] AST visitor found 'get_qa_text' in {f}")

                definitions.extend(visitor.functions)
        except Exception as e:
            print(f"Error parsing {f}: {e}")
    return definitions

def find_usages(name, search_paths):
    """Finds where a function/method name is used."""
    try:
        command = ['grep', '-rwl', name] + search_paths
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        # Ensure result.stdout is not empty before splitting
        if result.stdout:
            return result.stdout.strip().split('\n')
        return []
    except subprocess.CalledProcessError:
        return []

def is_django_special_method(name, class_name):
    """Check if the method is a Django special method."""
    if name in DJANGO_SPECIAL_METHODS:
        return True
    if name.startswith('clean_') or name.startswith('validate_'):
        return True
    if class_name and class_name.endswith('Manager'):
        return True
    return False

def main():
    """Main function to find unused code."""
    root_dir = 'apps'
    template_dir = 'templates'

    all_py_files = get_python_files(root_dir)
    prod_files, _ = separate_files(all_py_files)

    print(f"Found {len(prod_files)} production Python files.")

    definitions = get_definitions(prod_files)
    print(f"Found {len(definitions)} function/method definitions in production code.")

    unused_candidates = []

    for i, definition in enumerate(definitions):
        name = definition['name']
        file = definition['file']
        class_name = definition['class']

        print(f"Checking {i+1}/{len(definitions)}: {class_name or ''}::{name} in {file}...", end='\r')

        if is_django_special_method(name, class_name):
            continue

        usage_files = find_usages(name, [root_dir, template_dir])

        prod_usage_files = []
        # Filter out the definition file itself and test files
        # Also handle empty strings that might come from find_usages
        for f in usage_files:
            if f and f != file and '/tests/' not in f and not f.endswith('.html'):
                 prod_usage_files.append(f)

        template_usage = any(f.endswith('.html') for f in usage_files if f)

        if not prod_usage_files and not template_usage:
            test_usage = any('/tests/' in f for f in usage_files if f)
            if test_usage:
                unused_candidates.append(definition)

    print("\n\n--- Analysis Complete ---")
    if unused_candidates:
        print("Found potential functions/methods used only in tests:")
        for func in unused_candidates:
            class_info = f" in class {func['class']}" if func['class'] else ""
            print(f"  - File: {func['file']}:{func['lineno']}")
            print(f"    Function/Method: {func['name']}{class_info}\n")
    else:
        print("No functions/methods found that are only used in tests.")

if __name__ == "__main__":
    main()
