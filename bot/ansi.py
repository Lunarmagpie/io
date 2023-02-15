import math
import re

__all__: list[str] = ["approximate_ansi"]

color_map = {
    (255, 255, 255): "97",  # white
    (0, 0, 0): "30",  # black
    (128, 0, 0): "31",  # dark red
    (0, 128, 0): "32",  # dark green
    (128, 128, 0): "33",  # dark yellow
    (0, 0, 128): "34",  # dark blue
    (128, 0, 128): "35",  # dark magenta
    (0, 128, 128): "36",  # dark cyan
    (192, 192, 192): "37",  # light gray
    (128, 128, 128): "30",  # dark gray
    (255, 0, 0): "31",  # bright red
    (0, 255, 0): "32",  # bright green
    (255, 255, 0): "33",  # bright yellow
    (0, 0, 255): "34",  # bright blue
    (255, 0, 255): "35",  # bright magenta
    (0, 255, 255): "36",  # bright cyan
}


def ansi_8_bit_to_rgb(ansi_code: int) -> tuple[int, int, int] | str:
    if not 0 <= ansi_code <= 255:
        raise ValueError("Input must be an integer between 0 and 255")

    if 0 <= ansi_code <= 7:
        return f"{30+ansi_code}"

    if 8 <= ansi_code <= 15:
        return f"{30+ansi_code-8}"

    if 232 <= ansi_code <= 255:
        step = int(float(255 / 24) * (255 - ansi_code))
        return (step, step, step)

    return web_safe_color(ansi_code - 16)


def web_safe_color(n: int) -> tuple[int, int, int]:
    g = (n % 36) // 6
    b = n % 6
    r = (n - g - b) // 36

    return (r * 51, g * 51, b * 51)


ansi_escape_regex = re.compile(
    r"\033\[(?:(3[0-7]|[012][0-7])|4(?:[0-7]|8[0-5])|38;5;([0-9]+)|38;2;(\d+;\d+;\d+))m"
)


def approximate_ansi(string: str):
    def replace_color(match: re.Match[str]) -> str:
        m = match.group().split(";")

        if len(m) >= 3:
            rgb: tuple[int, int, int] | str
            if m[1] == "5":
                # 8 Bit
                rgb = ansi_8_bit_to_rgb(int(m[2].removesuffix("m")))
            elif m[1] == "2":
                # 24 Bit
                rgb = tuple(map(int, (m[2], m[3], m[4].removesuffix("m"))))
            else:
                raise ValueError("The ANSI was not valid")

            if not isinstance(rgb, str):
                closest = min(color_map.keys(), key=lambda x: math.dist(rgb, x))
                color = color_map[closest]
            else:
                color = rgb

            return f"\x1b[1;{color}m"

        else:
            # ansi must be 3 or 4 bit
            return ";".join(m)

    return ansi_escape_regex.sub(replace_color, string)