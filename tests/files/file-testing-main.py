from parsers.python_parser import PythonParser

def main():
    parser = PythonParser()

    # Parse file-1
    with open("tests/files/test-1.py", "r") as f:
        source_1 = f.read()
    tree_1 = parser.parse(source_1, "tests/files/test-1.py")

    if tree_1 is None:
        print("Failed to parse test-1.py")
        return

    root_node = tree_1.root_node
    # print(f"Root node type: {root_node.type}")
    
    print(f"{root_node.children[2].type}")

if __name__ == "__main__":
    main()