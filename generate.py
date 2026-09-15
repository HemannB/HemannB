import json
import os
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET


# ============================================================
# CONFIGURATION
# ============================================================

USERNAME = "HemannB"

ASCII_FILE = "ascii.txt"

SVG_FILES = [
    "dark_mode.svg",
    "light_mode.svg",
]

# ASCII positioning inside the SVG
ASCII_X = 40
ASCII_START_Y = 61
ASCII_LINE_HEIGHT = 5.15


# ============================================================
# STATIC PROFILE DATA
# ============================================================

STATIC_DATA = {
    "os_data": "Linux Mint",
    "focus_data": "Embedded / Full-stack",
    "languages_data": "C, C++, C#, Python, Java",
    "embedded_data": "STM32, ESP32, BLE",
    "tools_data": "Git, KiCad, emWin",
    "status_data": "Building things close to metal.",
}


# ============================================================
# GITHUB API
# ============================================================

def github_request(url):
    """
    Executes a request to the GitHub REST API.

    Authentication is optional locally.

    When executed through GitHub Actions, GITHUB_TOKEN can
    be supplied automatically by the workflow.
    """

    token = (
        os.getenv("GH_TOKEN")
        or os.getenv("GITHUB_TOKEN")
    )

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{USERNAME}-profile-readme",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(
        url,
        headers=headers,
    )

    try:
        with urllib.request.urlopen(request) as response:
            return json.loads(
                response.read().decode("utf-8")
            )

    except urllib.error.HTTPError as error:
        body = error.read().decode(
            "utf-8",
            errors="replace",
        )

        raise RuntimeError(
            f"GitHub API error {error.code}: {body}"
        ) from error

    except urllib.error.URLError as error:
        raise RuntimeError(
            f"Could not connect to GitHub API: {error}"
        ) from error


def fetch_user():
    url = f"https://api.github.com/users/{USERNAME}"

    return github_request(url)


def fetch_repositories():
    """
    Fetches every public repository owned by the user.

    GitHub returns at most 100 repositories per page,
    so pagination is handled automatically.
    """

    repositories = []

    page = 1

    while True:
        url = (
            f"https://api.github.com/users/{USERNAME}/repos"
            f"?type=owner"
            f"&per_page=100"
            f"&page={page}"
            f"&sort=updated"
        )

        data = github_request(url)

        if not data:
            break

        repositories.extend(data)

        if len(data) < 100:
            break

        page += 1

    return repositories


def calculate_repository_stats(repositories):
    """
    Forks are ignored for repository/star statistics.

    This makes the values represent projects actually
    maintained by the user rather than cloned forks.
    """

    original_repositories = [
        repo
        for repo in repositories
        if not repo.get("fork", False)
    ]

    stars = sum(
        repo.get("stargazers_count", 0)
        for repo in original_repositories
    )

    return {
        "repo_data": str(len(original_repositories)),
        "star_data": str(stars),
    }


def fetch_github_stats():
    print("Fetching GitHub statistics...")

    user = fetch_user()

    repositories = fetch_repositories()

    repository_stats = calculate_repository_stats(
        repositories
    )

    return {
        "follower_data": str(
            user.get("followers", 0)
        ),

        "following_data": str(
            user.get("following", 0)
        ),

        **repository_stats,
    }


# ============================================================
# ASCII PROCESSING
# ============================================================

def read_ascii():
    with open(
        ASCII_FILE,
        "r",
        encoding="utf-8",
    ) as file:
        return file.read()


def trim_empty_lines(lines):
    """
    Removes blank lines from the beginning and end
    without touching whitespace inside the ASCII art.
    """

    while lines and not lines[0].strip():
        lines.pop(0)

    while lines and not lines[-1].strip():
        lines.pop()

    return lines


def remove_common_indentation(lines):
    """
    Removes only the whitespace shared by every line.

    Internal spaces are preserved because they are part
    of the portrait.
    """

    non_empty_lines = [
        line
        for line in lines
        if line.strip()
    ]

    if not non_empty_lines:
        return lines

    indentation = min(
        len(line) - len(line.lstrip(" "))
        for line in non_empty_lines
    )

    return [
        line[indentation:]
        if len(line) >= indentation
        else line
        for line in lines
    ]


def clean_ascii(ascii_text):
    lines = ascii_text.splitlines()

    lines = trim_empty_lines(lines)

    lines = remove_common_indentation(lines)

    return lines


# ============================================================
# SVG HELPERS
# ============================================================

def find_element_by_id(root, element_id):
    """
    ElementTree introduces namespaces when parsing SVG.

    Searching manually by ID avoids having to worry
    about namespace prefixes.
    """

    for element in root.iter():
        if element.get("id") == element_id:
            return element

    return None


def replace_text(root, element_id, value):
    element = find_element_by_id(
        root,
        element_id,
    )

    if element is None:
        print(
            f"Warning: SVG element '{element_id}' "
            "was not found."
        )
        return

    element.text = value


def insert_ascii(root, ascii_lines):
    element = find_element_by_id(
        root,
        "ascii_art",
    )

    if element is None:
        raise RuntimeError(
            "SVG does not contain an element "
            "with id='ascii_art'."
        )

    # Remove previously generated lines
    for child in list(element):
        element.remove(child)

    element.text = None

    for index, line in enumerate(ascii_lines):

        y = (
            ASCII_START_Y
            + index * ASCII_LINE_HEIGHT
        )

        tspan = ET.SubElement(
            element,
            "tspan",
        )

        tspan.set(
            "x",
            str(ASCII_X),
        )

        tspan.set(
            "y",
            f"{y:.2f}",
        )

        # Preserve spaces exactly as they appear
        # in ascii.txt.
        tspan.set(
            "{http://www.w3.org/XML/1998/namespace}space",
            "preserve",
        )

        # ElementTree automatically escapes special
        # XML characters such as <, > and &.
        tspan.text = line


# ============================================================
# SVG GENERATION
# ============================================================

def update_svg(
    filename,
    values,
    ascii_lines,
):
    ET.register_namespace(
        "",
        "http://www.w3.org/2000/svg",
    )

    tree = ET.parse(filename)

    root = tree.getroot()

    # Update profile information and GitHub statistics
    for element_id, value in values.items():
        replace_text(
            root,
            element_id,
            value,
        )

    # Insert portrait
    insert_ascii(
        root,
        ascii_lines,
    )

    tree.write(
        filename,
        encoding="utf-8",
        xml_declaration=True,
    )

    print(f"Updated: {filename}")


# ============================================================
# MAIN
# ============================================================

def main():
    print()
    print("======================================")
    print("  HemannB GitHub Profile Generator")
    print("======================================")
    print()

    # ASCII
    ascii_text = read_ascii()

    ascii_lines = clean_ascii(
        ascii_text
    )

    print(
        f"ASCII loaded: {len(ascii_lines)} lines"
    )

    # GitHub
    github_stats = fetch_github_stats()

    values = {
        **STATIC_DATA,
        **github_stats,
    }

    print()
    print("GitHub statistics:")
    print(
        f"  Repositories : "
        f"{values['repo_data']}"
    )
    print(
        f"  Stars        : "
        f"{values['star_data']}"
    )
    print(
        f"  Followers    : "
        f"{values['follower_data']}"
    )
    print(
        f"  Following    : "
        f"{values['following_data']}"
    )

    print()

    # Update both themes
    for svg_file in SVG_FILES:
        update_svg(
            svg_file,
            values,
            ascii_lines,
        )

    print()
    print(
        "Profile generated successfully."
    )
    print()


if __name__ == "__main__":
    main()