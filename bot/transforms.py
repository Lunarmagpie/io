import re

RUST_FN_REGEX = re.compile(r"fn\s*main\s*\(\s*\)")


def transform_code(lang: str, code: str) -> str:
    """
    Converts the code into new code based on the language and some rules.
    """

    match lang:
        case "java":
            return code.replace("public class", "class")

        case "rust":
            if not RUST_FN_REGEX.match(code):
                return "fn main() {\n" f"{code}\n" "}"
            return code

        case _:
            return code
