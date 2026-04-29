from typing import Any
from core.models.node import CodeNode, CodeNodeType
from core.models.edge import CodeEdge, CodeEdgeType
from extractors.base_extractor import BaseExtractor
from tree_sitter import Tree
import hashlib

class PythonExtractor(BaseExtractor):

    def __init__(self, repo: str, project_modules: set[str] | None = None) -> None:
        self._repo = repo
        self._project_modules = project_modules or set()

    @property
    def language(self) -> str:
        return "python"
    
    def extract(self, tree: Tree, source: bytes, file_path: str) -> tuple[list[CodeNode], list[CodeEdge]]:
        nodes: list[CodeNode] = []
        edges: list[CodeEdge] = []
        
        root_node = tree.root_node
        module_node = self._hanlde_module(root_node, file_path, source)
        nodes.append(module_node)

        for node in root_node.children:
            
            # handling imports
            if node.type == "import_statement" or node.type == "import_from_statement":
                edges.extend(self._handle_import(node, file_path, source))
            
            elif node.type == "function_definition":
                function_node, function_edges = self._handle_function(
                    node,
                    source,
                    file_path,
                    module_node.id,
                    self._repo,
                )
                nodes.append(function_node)
                edges.extend(function_edges)

            elif node.type == "class_definition":
                class_nodes, class_edges = self._handle_class(
                    node,
                    source,
                    file_path,
                    module_node.id,
                    self._repo,
                )
                nodes.extend(class_nodes)
                edges.extend(class_edges)

            elif node.type == "decorated_definition":
                definition_node = node.child_by_field_name("definition")
                if definition_node is not None and definition_node.type == "function_definition":
                    function_node, function_edges = self._handle_function(
                        node,
                        source,
                        file_path,
                        module_node.id,
                        self._repo,
                    )
                    nodes.append(function_node)
                    edges.extend(function_edges)
                elif definition_node is not None and definition_node.type == "class_definition":
                    class_nodes, class_edges = self._handle_class(
                        node,
                        source,
                        file_path,
                        module_node.id,
                        self._repo,
                    )
                    nodes.extend(class_nodes)
                    edges.extend(class_edges)
        
        return nodes, edges   

    def _handle_import(self, node: Any, file_path: str, source: bytes) -> list[CodeEdge]:
        def node_text(child: Any) -> str:
            return source[child.start_byte:child.end_byte].decode("utf-8").strip()

        def is_project_module(module_name: str) -> bool:
            if not self._project_modules:
                return True
            return any(
                module_name == project_module
                or module_name.startswith(f"{project_module}.")
                or project_module.startswith(f"{module_name}.")
                for project_module in self._project_modules
            )

        def package_module(path: str) -> str:
            module_name = self._module_name_from_path(path)
            return module_name.rsplit(".", 1)[0] if "." in module_name else ""

        def parse_import_name(name_node: Any) -> tuple[str, str | None] | None:
            if name_node.type == "aliased_import":
                original_node = name_node.child_by_field_name("name")
                alias_node = name_node.child_by_field_name("alias")
                if original_node is None:
                    return None
                original_name = node_text(original_node)
                if not original_name:
                    return None
                alias = node_text(alias_node) if alias_node is not None else None
                return original_name, alias or None

            if name_node.type in {"dotted_name", "identifier"}:
                original_name = node_text(name_node)
                return (original_name, None) if original_name else None

            return None

        def resolve_relative(relative_node: Any, imported_name: str | None = None) -> str:
            prefix = next(
                (child for child in relative_node.children if child.type == "import_prefix"),
                None,
            )
            levels = len(node_text(prefix)) if prefix is not None else 0

            package_parts = [part for part in package_module(file_path).split(".") if part]
            up = max(levels - 1, 0)
            if up:
                package_parts = package_parts[:-up]

            module_part = next(
                (child for child in relative_node.children if child.type == "dotted_name"),
                None,
            )
            suffix = node_text(module_part) if module_part is not None else imported_name
            if suffix:
                package_parts.extend(part for part in suffix.split(".") if part)

            return ".".join(package_parts)

        imports: dict[str, dict[str, Any]] = {}

        def register_import(
            module_name: str,
            *,
            imported_name: str | None = None,
            alias: str | None = None,
            is_relative: bool = False,
            level: int = 0,
        ) -> None:
            if not module_name or not is_project_module(module_name):
                return
            import_data = imports.setdefault(
                module_name,
                {
                    "module": module_name,
                    "bindings": [],
                    "is_relative": is_relative,
                    "level": level,
                },
            )
            if imported_name is not None:
                import_data["bindings"].append(
                    {
                        "name": imported_name,
                        "alias": alias,
                    }
                )

        def relative_level(relative_node: Any) -> int:
            prefix = next(
                (child for child in relative_node.children if child.type == "import_prefix"),
                None,
            )
            return len(node_text(prefix)) if prefix is not None else 0

        if node.type == "import_statement":
            for name_node in node.children_by_field_name("name"):
                parsed = parse_import_name(name_node)
                if parsed is None:
                    continue
                module_name, alias = parsed
                register_import(module_name, imported_name=module_name, alias=alias)

        elif node.type == "import_from_statement":
            module_node = node.child_by_field_name("module_name")
            if module_node is None:
                return []

            imported_names = [
                parsed
                for name_node in node.children_by_field_name("name")
                for parsed in [parse_import_name(name_node)]
                if parsed is not None
            ]

            if module_node.type == "relative_import":
                level = relative_level(module_node)
                has_explicit_module = any(
                    child.type == "dotted_name" for child in module_node.children
                )
                if has_explicit_module:
                    module_name = resolve_relative(module_node)
                    register_import(
                        module_name,
                        is_relative=True,
                        level=level,
                    )
                    for imported_name, alias in imported_names:
                        register_import(
                            module_name,
                            imported_name=imported_name,
                            alias=alias,
                            is_relative=True,
                            level=level,
                        )
                else:
                    if imported_names:
                        for imported_name, alias in imported_names:
                            module_name = resolve_relative(module_node, imported_name)
                            register_import(
                                module_name,
                                imported_name=imported_name,
                                alias=alias,
                                is_relative=True,
                                level=level,
                            )
                    elif any(child.type == "wildcard_import" for child in node.children):
                        register_import(
                            resolve_relative(module_node),
                            imported_name="*",
                            is_relative=True,
                            level=level,
                        )
            else:
                module_name = node_text(module_node)
                register_import(module_name)
                for imported_name, alias in imported_names:
                    register_import(
                        module_name,
                        imported_name=imported_name,
                        alias=alias,
                    )

        edges: list[CodeEdge] = []
        for module_name, import_data in imports.items():
            edges.append(
                CodeEdge(
                    id=self._make_edge_id(file_path, module_name, CodeEdgeType.IMPORTS),
                    source_id=file_path,
                    target_id=None,
                    target_ref=module_name,
                    type=CodeEdgeType.IMPORTS,
                    attributes=import_data,
                )
            )

        return edges
    
    def _hanlde_module(self, node: Any, file_path: str, source: bytes) -> CodeNode:
        qualified_name = self._module_name_from_path(file_path)
        name = qualified_name.rsplit(".", 1)[-1] if qualified_name else file_path.replace("\\", "/").rsplit("/", 1)[-1].rsplit(".", 1)[0]
        return CodeNode(
            id=self._make_node_id(self._repo, file_path, qualified_name, 1),
            name=name,
            type=CodeNodeType.MODULE,
            start_byte=node.start_byte,
            end_byte=node.end_byte,
            language=self.language,
            path=file_path,
            qualified_name=qualified_name,
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
            raw_source=node.text.decode("utf-8"),
        )

    def _handle_class(self, node: Any, source: bytes, file_path: str, parent_id: str, repo: str,) -> tuple[list[CodeNode], list[CodeEdge]]:
        def node_text(child: Any) -> str:
            return source[child.start_byte:child.end_byte].decode("utf-8")

        if node.type == "decorated_definition":
            decorators = [
                node_text(child)[1:]
                for child in node.children
                if child.type == "decorator"
            ]
            class_node = node.child_by_field_name("definition")
            if class_node is None or class_node.type != "class_definition":
                raise ValueError("decorated_definition must wrap a class_definition.")
        elif node.type == "class_definition":
            decorators = []
            class_node = node
        else:
            raise ValueError("node must be a class_definition or decorated_definition.")

        name_node = class_node.child_by_field_name("name")
        if name_node is None:
            raise ValueError("class_definition is missing a name field.")

        superclasses_node = class_node.child_by_field_name("superclasses")
        base_nodes = []
        if superclasses_node is not None:
            base_nodes = list(superclasses_node.children_by_field_name("argument"))
            if not base_nodes:
                base_nodes = [child for child in superclasses_node.children if child.is_named]

        bases = [node_text(base_node) for base_node in base_nodes]
        name = node_text(name_node)
        module_qualified_name = self._module_name_from_path(file_path)
        class_qualified_name = f"{module_qualified_name}.{name}" if module_qualified_name else name
        start_line = node.start_point[0] + 1
        class_id = self._make_node_id(repo, file_path, class_qualified_name, start_line)

        code_node = CodeNode(
            id=class_id,
            name=name,
            type=CodeNodeType.CLASS,
            start_byte=node.start_byte,
            end_byte=node.end_byte,
            language=self.language,
            path=file_path,
            qualified_name=class_qualified_name,
            start_line=start_line,
            end_line=node.end_point[0] + 1,
            raw_source=node_text(node),
            attributes={
                "decorators": decorators,
                "bases": bases,
            },
        )

        edges = [
            CodeEdge(
                id=self._make_edge_id(parent_id, class_id, CodeEdgeType.DEFINES),
                source_id=parent_id,
                target_id=class_id,
                target_ref=class_qualified_name,
                type=CodeEdgeType.DEFINES,
                attributes={},
            )
        ]

        for base_name in bases:
            edges.append(
                CodeEdge(
                    id=self._make_edge_id(class_id, base_name, CodeEdgeType.INHERITS),
                    source_id=class_id,
                    target_id=None,
                    target_ref=base_name,
                    type=CodeEdgeType.INHERITS,
                    attributes={"source_file": file_path},
                )
            )

        nodes = [code_node]
        body_node = class_node.child_by_field_name("body")
        if body_node is not None:
            for child in body_node.children:
                if child.type == "function_definition":
                    method_ast = child
                elif child.type == "decorated_definition":
                    definition_node = child.child_by_field_name("definition")
                    if definition_node is None or definition_node.type != "function_definition":
                        continue
                    method_ast = child
                else:
                    continue

                method_node, method_edges = self._handle_function(
                    method_ast,
                    source,
                    file_path,
                    class_id,
                    repo,
                )
                method_node.qualified_name = f"{class_qualified_name}.{method_node.name}"
                for method_edge in method_edges:
                    if (
                        method_edge.type == CodeEdgeType.DEFINES
                        and method_edge.target_id == method_node.id
                    ):
                        method_edge.target_ref = method_node.qualified_name
                nodes.append(method_node)
                edges.extend(method_edges)

        return nodes, edges

    def _handle_function(self, node: Any, source: bytes, file_path: str, parent_id: str, repo: str,) -> tuple[CodeNode, list[CodeEdge]]:
        _ = source

        if node.type == "decorated_definition":
            decorators = [
                child.text.decode("utf-8")[1:]
                for child in node.children
                if child.type == "decorator"
            ]
            function_node = node.child_by_field_name("definition")
            if function_node is None or function_node.type != "function_definition":
                raise ValueError("decorated_definition must wrap a function_definition.")
        elif node.type == "function_definition":
            decorators = []
            function_node = node
        else:
            raise ValueError("node must be a function_definition or decorated_definition.")

        name_node = function_node.child_by_field_name("name")
        if name_node is None:
            raise ValueError("function_definition is missing a name field.")

        parameters_node = function_node.child_by_field_name("parameters")
        args: dict[str, str | None] = {}
        if parameters_node is not None:
            for parameter_node in parameters_node.children:
                parameter_name: str | None = None
                parameter_type: str | None = None

                if parameter_node.type == "identifier":
                    parameter_name = parameter_node.text.decode("utf-8")
                elif parameter_node.type in {
                    "typed_parameter",
                    "typed_default_parameter",
                    "default_parameter",
                    "list_splat_pattern",
                    "dictionary_splat_pattern",
                }:
                    for child in parameter_node.children:
                        if parameter_name is None and child.type == "identifier":
                            parameter_name = child.text.decode("utf-8")
                        elif parameter_type is None and child.type == "type":
                            parameter_type = child.text.decode("utf-8")

                if parameter_name:
                    args[parameter_name] = parameter_type

        returns_node = function_node.child_by_field_name("return_type")
        returns = returns_node.text.decode("utf-8") if returns_node is not None else None
        is_async = any(child.type == "async" for child in function_node.children)

        name = name_node.text.decode("utf-8")
        module_qualified_name = self._module_name_from_path(file_path)
        qualified_name = f"{module_qualified_name}.{name}" if module_qualified_name else name
        start_line = node.start_point[0] + 1
        function_id = self._make_node_id(repo, file_path, qualified_name, start_line)

        code_node = CodeNode(
            id=function_id,
            name=name,
            type=CodeNodeType.FUNCTION,
            start_byte=node.start_byte,
            end_byte=node.end_byte,
            language=self.language,
            path=file_path,
            qualified_name=qualified_name,
            start_line=start_line,
            end_line=node.end_point[0] + 1,
            raw_source=node.text.decode("utf-8"),
            attributes={
                "decorators": decorators,
                "args": args,
                "returns": returns,
                "is_async": is_async,
            },
        )

        edges = [
            CodeEdge(
                id=self._make_edge_id(parent_id, function_id, CodeEdgeType.DEFINES),
                source_id=parent_id,
                target_id=function_id,
                target_ref=qualified_name,
                type=CodeEdgeType.DEFINES,
                attributes={},
            )
        ]

        body_node = function_node.child_by_field_name("body")
        seen_calls: set[str] = set()
        if body_node is not None:
            for call_name in self._extract_calls(body_node):
                if not call_name or call_name in seen_calls:
                    continue
                seen_calls.add(call_name)
                edges.append(
                    CodeEdge(
                        id=self._make_edge_id(function_id, call_name, CodeEdgeType.CALLS),
                        source_id=function_id,
                        target_id=None,
                        target_ref=call_name,
                        type=CodeEdgeType.CALLS,
                        attributes={},
                    )
                )

        return code_node, edges

    def _extract_calls(self, node: Any) -> list[str]:
        calls: list[str] = []

        if node.type == "call":
            function_node = node.child_by_field_name("function")
            if function_node is not None:
                calls.append(function_node.text.decode("utf-8"))

        for child in node.children:
            calls.extend(self._extract_calls(child))

        return calls

    def _module_name_from_path(self, file_path: str) -> str:
        normalized = file_path.replace("\\", "/").strip("/")
        if normalized.endswith(".pyw"):
            normalized = normalized[:-4]
        elif normalized.endswith(".py"):
            normalized = normalized[:-3]
        return ".".join(part for part in normalized.split("/") if part)

    def _make_node_id(self, repo: str, path: str, qualified_name: str, start_line: int) -> str:
        raw = f"{repo}:{path}:{qualified_name}:{start_line}"
        return hashlib.sha1(raw.encode()).hexdigest()
    
    def _make_edge_id(self, source_id: str, target_ref: str, type: CodeEdgeType) -> str:
        raw = f"{source_id}:{target_ref}:{type}"
        return hashlib.sha1(raw.encode()).hexdigest()
    
__all__ = ["PythonExtractor"]
