import re


JAVA_PUBLIC_CLASS_REGEX = re.compile(r"public\s+class")
RUST_FN_REGEX = re.compile(r"fn\s+main\s*\(\s*\)")


def transform_code(lang: str, code: str) -> str:
    """
    Converts the code into new code based on the language and some rules.
    """

    match lang:
        case "java":
            if code.strip().startswith("public"):
                return JAVA_PUBLIC_CLASS_REGEX.sub("class", code, count=1)
            return code

        case "rust":
            if not RUST_FN_REGEX.match(code):
                return "fn main() {\n" f"{code}\n" "}"
            return code

        case _:
            return code
