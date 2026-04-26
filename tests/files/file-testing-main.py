from parsers.python_parser import PythonParser

def main():
    parser = PythonParser()

    # Parse file-1
    with open("tests/files/test-1.py", "r") as f:
        source_1 = f.read()
    tree_1 = parser.parse(source_1, "tests/files/test-1.py")
    print("File-1 parsed successfully")
    print(f"Tree: {tree_1}")

    # Parse file-2
    with open("tests/files/test-2.py", "r") as f:
        source_2 = f.read()
    tree_2 = parser.parse(source_2, "tests/files/test-2.py")
    print("File-2 parsed successfully")
    print(f"Tree: {tree_2}")

if __name__ == "__main__":
    main()