"""Tree-sitter based multi-language source code analyzer.

Extracts classes, functions, methods, imports, inheritance, decorators,
and function-call relationships from JavaScript, TypeScript, Java, Kotlin,
and Go source files using tree-sitter grammars.

Falls back gracefully if a language grammar is unavailable.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from services.ast_analyzer import ClassInfo, FunctionInfo, FileAnalysisResult
from utils.helpers import safe_read, detect_language

logger = logging.getLogger(__name__)

# ── Tree-sitter lazy init ───────────────────────────────────────

_INITIALIZED = False
_AVAILABLE = False

# Map file extensions → tree-sitter language names
_EXT_TO_LANG = {
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".kt": "kotlin",
    ".go": "go",
}


def _init_tree_sitter() -> bool:
    """Initialize tree-sitter. Returns True if available."""
    global _INITIALIZED, _AVAILABLE

    if _INITIALIZED:
        return _AVAILABLE

    _INITIALIZED = True

    try:
        from tree_sitter_language_pack import get_parser
        _AVAILABLE = True
        logger.info("tree-sitter-language-pack loaded successfully")
        return True
    except ImportError:
        logger.warning(
            "tree-sitter-language-pack not installed. "
            "Multi-language analysis disabled. Install with: "
            "pip install tree-sitter tree-sitter-language-pack"
        )
        _AVAILABLE = False
        return False


def _get_parser(lang_name: str):
    """Get a tree-sitter parser for the given language."""
    try:
        from tree_sitter_language_pack import get_parser
        return get_parser(lang_name)
    except Exception as exc:
        logger.warning("Failed to get parser for %s: %s", lang_name, exc)
        return None


# ── Language-specific extractors ────────────────────────────────

def _extract_name(node) -> str:
    """Extract the text content of a node."""
    return node.text.decode("utf-8") if node else ""


def _get_docstring_from_body(node) -> str | None:
    """Try to extract a leading comment or doc-comment from a node's body."""
    for child in node.children:
        if child.type in ("comment", "line_comment", "block_comment"):
            text = child.text.decode("utf-8").strip()
            # Clean comment markers
            for prefix in ("//", "/*", "*/", "*", "#", "/**"):
                text = text.removeprefix(prefix)
            text = text.removesuffix("*/").strip()
            if text:
                return text
    return None


def _analyze_javascript(tree, source_bytes: bytes) -> tuple[list[ClassInfo], list[FunctionInfo], list[str]]:
    """Extract classes, functions, and imports from JS/TS."""
    classes: list[ClassInfo] = []
    functions: list[FunctionInfo] = []
    imports: list[str] = []

    root = tree.root_node

    for node in _walk_tree(root):
        # Imports
        if node.type in ("import_statement", "import_declaration"):
            source_node = node.child_by_field_name("source")
            if source_node:
                imports.append(_extract_name(source_node).strip("'\""))

        # Classes
        elif node.type == "class_declaration":
            name_node = node.child_by_field_name("name")
            name = _extract_name(name_node)

            bases = []
            heritage = node.child_by_field_name("heritage") or _find_child(node, "class_heritage")
            if heritage:
                for child in heritage.children:
                    if child.type == "identifier":
                        bases.append(_extract_name(child))

            methods = []
            body = node.child_by_field_name("body")
            if body:
                for child in body.children:
                    if child.type in ("method_definition", "public_field_definition"):
                        m_name = child.child_by_field_name("name")
                        if m_name:
                            methods.append(_extract_name(m_name))

            classes.append(ClassInfo(
                name=name, bases=bases, methods=methods,
                docstring=_get_docstring_from_body(node),
                line_start=node.start_point[0] + 1,
                line_end=node.end_point[0] + 1,
            ))

        # Functions (top-level)
        elif node.type in ("function_declaration", "arrow_function", "function"):
            name_node = node.child_by_field_name("name")
            if not name_node and node.parent and node.parent.type == "variable_declarator":
                name_node = node.parent.child_by_field_name("name")

            name = _extract_name(name_node) if name_node else "<anonymous>"
            if name == "<anonymous>":
                continue

            args = _extract_params(node)
            calls = _extract_calls(node)
            ret = _extract_return_type(node)

            functions.append(FunctionInfo(
                name=name, args=args, calls=calls, returns=ret,
                docstring=_get_docstring_from_body(node),
                line_start=node.start_point[0] + 1,
                line_end=node.end_point[0] + 1,
                is_method=False,
            ))

        # Export default function
        elif node.type == "export_statement":
            for child in node.children:
                if child.type == "function_declaration":
                    name_node = child.child_by_field_name("name")
                    name = _extract_name(name_node) if name_node else "default"
                    args = _extract_params(child)
                    calls = _extract_calls(child)
                    ret = _extract_return_type(child)
                    functions.append(FunctionInfo(
                        name=name, args=args, calls=calls, returns=ret,
                        line_start=child.start_point[0] + 1,
                        line_end=child.end_point[0] + 1,
                        is_method=False,
                    ))

    return classes, functions, imports


def _analyze_java_kotlin(tree, source_bytes: bytes, lang: str) -> tuple[list[ClassInfo], list[FunctionInfo], list[str]]:
    """Extract classes, functions, and imports from Java/Kotlin."""
    classes: list[ClassInfo] = []
    functions: list[FunctionInfo] = []
    imports: list[str] = []

    root = tree.root_node

    for node in _walk_tree(root):
        # Imports
        if node.type == "import_declaration":
            text = node.text.decode("utf-8").replace("import ", "").rstrip(";").strip()
            imports.append(text)

        # Classes
        elif node.type in ("class_declaration", "interface_declaration", "object_declaration"):
            name_node = node.child_by_field_name("name") or node.child_by_field_name("identifier")
            name = _extract_name(name_node) if name_node else "Unknown"

            bases = []
            for child in node.children:
                if child.type in ("superclass", "super_interfaces", "delegation_specifiers"):
                    for sub in child.children:
                        if sub.type in ("type_identifier", "identifier"):
                            bases.append(_extract_name(sub))

            methods = []
            body = node.child_by_field_name("body") or node.child_by_field_name("class_body")
            if body:
                for child in body.children:
                    if child.type in ("method_declaration", "function_declaration",
                                      "constructor_declaration"):
                        m_name = child.child_by_field_name("name") or child.child_by_field_name("identifier")
                        if m_name:
                            methods.append(_extract_name(m_name))
                            args = _extract_params(child)
                            calls = _extract_calls(child)
                            ret = _extract_return_type(child)
                            functions.append(FunctionInfo(
                                name=_extract_name(m_name), args=args,
                                calls=calls, returns=ret,
                                docstring=_get_docstring_from_body(child),
                                line_start=child.start_point[0] + 1,
                                line_end=child.end_point[0] + 1,
                                is_method=True,
                            ))

            classes.append(ClassInfo(
                name=name, bases=bases, methods=methods,
                docstring=_get_docstring_from_body(node),
                line_start=node.start_point[0] + 1,
                line_end=node.end_point[0] + 1,
            ))

        # Top-level functions
        elif node.type in ("function_declaration", "method_declaration") and \
                node.parent and node.parent.type in ("program", "source_file"):
            name_node = node.child_by_field_name("name") or node.child_by_field_name("identifier")
            name = _extract_name(name_node) if name_node else "unknown"
            args = _extract_params(node)
            calls = _extract_calls(node)
            ret = _extract_return_type(node)

            functions.append(FunctionInfo(
                name=name, args=args, calls=calls, returns=ret,
                docstring=_get_docstring_from_body(node),
                line_start=node.start_point[0] + 1,
                line_end=node.end_point[0] + 1,
                is_method=False,
            ))

    return classes, functions, imports


def _analyze_go(tree, source_bytes: bytes) -> tuple[list[ClassInfo], list[FunctionInfo], list[str]]:
    """Extract structs (as classes), functions, and imports from Go."""
    classes: list[ClassInfo] = []
    functions: list[FunctionInfo] = []
    imports: list[str] = []

    root = tree.root_node

    for node in _walk_tree(root):
        # Imports
        if node.type == "import_spec":
            path_node = node.child_by_field_name("path")
            if path_node:
                imports.append(_extract_name(path_node).strip('"'))

        # Struct types (treated as classes)
        elif node.type == "type_declaration":
            for child in node.children:
                if child.type == "type_spec":
                    name_node = child.child_by_field_name("name")
                    name = _extract_name(name_node) if name_node else "Unknown"
                    type_node = child.child_by_field_name("type")

                    if type_node and type_node.type == "struct_type":
                        fields = []
                        for fld in _walk_tree(type_node):
                            if fld.type == "field_declaration":
                                fn = fld.child_by_field_name("name")
                                if fn:
                                    fields.append(_extract_name(fn))

                        classes.append(ClassInfo(
                            name=name, bases=[], methods=fields,
                            docstring=_get_docstring_from_body(node),
                            line_start=node.start_point[0] + 1,
                            line_end=node.end_point[0] + 1,
                        ))

        # Functions and methods
        elif node.type in ("function_declaration", "method_declaration"):
            name_node = node.child_by_field_name("name")
            name = _extract_name(name_node) if name_node else "unknown"

            is_method = node.type == "method_declaration"
            args = _extract_params(node)
            calls = _extract_calls(node)
            ret = _extract_return_type(node)

            receiver = node.child_by_field_name("receiver")
            if receiver:
                is_method = True

            functions.append(FunctionInfo(
                name=name, args=args, calls=calls, returns=ret,
                docstring=_get_docstring_from_body(node),
                line_start=node.start_point[0] + 1,
                line_end=node.end_point[0] + 1,
                is_method=is_method,
            ))

    return classes, functions, imports


# ── Shared helpers ──────────────────────────────────────────────

def _walk_tree(node):
    """Depth-first walk of a tree-sitter node."""
    yield node
    for child in node.children:
        yield from _walk_tree(child)


def _find_child(node, type_name: str):
    """Find first child of given type."""
    for child in node.children:
        if child.type == type_name:
            return child
    return None


def _extract_params(node) -> list[str]:
    """Extract parameter names from a function node."""
    params = []
    param_node = node.child_by_field_name("parameters") or \
                 node.child_by_field_name("formal_parameters") or \
                 node.child_by_field_name("parameter_list") or \
                 _find_child(node, "formal_parameters")

    if param_node:
        for child in param_node.children:
            if child.type in ("identifier", "simple_parameter",
                              "required_parameter", "optional_parameter",
                              "formal_parameter", "parameter"):
                name_node = child.child_by_field_name("name") or \
                            child.child_by_field_name("identifier")
                if name_node:
                    name = _extract_name(name_node)
                    if name not in ("self", "this", "(", ")", ","):
                        params.append(name)
                elif child.type == "identifier":
                    name = _extract_name(child)
                    if name not in ("self", "this", "(", ")", ","):
                        params.append(name)
    return params


def _extract_return_type(node) -> str | None:
    """Extract the return type of a function/method."""
    ret_node = node.child_by_field_name("return_type") or \
               node.child_by_field_name("result") or \
               _find_child(node, "type_annotation")

    # Kotlin/TS often use ":" then the type
    if not ret_node:
        for child in node.children:
            if child.type == "type_annotation":
                ret_node = child
                break

    if ret_node:
        text = _extract_name(ret_node)
        # Clean up leading ":" or "->"
        return text.lstrip(": >-").strip()
    return None


def _extract_calls(node) -> list[str]:
    """Extract function call names from a node's subtree."""
    calls = []
    for child in _walk_tree(node):
        if child.type == "call_expression":
            func = child.child_by_field_name("function") or \
                   child.child_by_field_name("name")
            if func:
                name = _extract_name(func)
                if name and len(name) < 100:
                    calls.append(name)
    return calls


# ── Public API ──────────────────────────────────────────────────

def analyze_file_generic(file_path: Path, repo_root: Path) -> FileAnalysisResult | None:
    """Analyze a non-Python source file using tree-sitter.

    Returns None if the file can't be parsed or the language isn't supported.
    """
    if not _init_tree_sitter():
        return None

    ext = file_path.suffix.lower()
    lang_name = _EXT_TO_LANG.get(ext)
    if not lang_name:
        return None

    source = safe_read(file_path)
    if source is None:
        return None

    source_bytes = source.encode("utf-8")

    try:
        parser = _get_parser(lang_name)
        if parser is None:
            return None
        tree = parser.parse(source_bytes)
    except Exception as exc:
        logger.warning("tree-sitter parse error for %s: %s", file_path, exc)
        return None

    # Dispatch to language-specific extractor
    if lang_name in ("javascript", "typescript"):
        classes, functions, imports = _analyze_javascript(tree, source_bytes)
    elif lang_name in ("java", "kotlin"):
        classes, functions, imports = _analyze_java_kotlin(tree, source_bytes, lang_name)
    elif lang_name == "go":
        classes, functions, imports = _analyze_go(tree, source_bytes)
    else:
        return None

    return FileAnalysisResult(
        path=str(file_path.relative_to(repo_root)).replace("\\", "/"),
        imports=imports,
        classes=classes,
        functions=functions,
        line_count=source.count("\n") + 1,
        module_docstring=_get_docstring_from_body(tree.root_node),
    )
