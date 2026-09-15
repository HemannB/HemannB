import os
import requests
import xml.etree.ElementTree as ET

GITHUB_USERNAME = "HemannB"
GITHUB_TOKEN = os.getenv("GH_TOKEN")

SVG_FILES = ["dark_mode.svg", "light_mode.svg"]
ASCII_FILE = "ascii.txt"

GRAPHQL_QUERY = """
query($login: String!) {
  user(login: $login) {
    login
    followers {
      totalCount
    }
    following {
      totalCount
    }
    repositories(ownerAffiliations: OWNER, isFork: false) {
      totalCount
      nodes {
        stargazerCount
      }
    }
  }
}
"""

def fetch_github_data():
    headers = {
        "Authorization": f"bearer {GITHUB_TOKEN}",
        "Content-Type": "application/json"
    }

    response = requests.post(
        "https://api.github.com/graphql",
        json={
            "query": GRAPHQL_QUERY,
            "variables": {"login": GITHUB_USERNAME}
        },
        headers=headers
    )

    response.raise_for_status()
    data = response.json()["data"]["user"]

    repos = data["repositories"]["totalCount"]
    stars = sum(repo["stargazerCount"] for repo in data["repositories"]["nodes"])
    followers = data["followers"]["totalCount"]
    following = data["following"]["totalCount"]

    return {
        "repo_data": str(repos),
        "star_data": str(stars),
        "follower_data": str(followers),
        "following_data": str(following),
        "os_data": "Linux",
        "focus_data": "Embedded / Full-stack",
        "lang_data": "C, C++, C#, Python, Java",
        "embedded_data": "STM32, ESP32, BLE",
        "status_data": "Building things close to metal."
    }

def build_ascii_tspans(ascii_text, x=55, start_y=95, line_height=14):
    lines = ascii_text.splitlines()
    tspans = []
    y = start_y
    for line in lines:
        tspan = ET.Element("tspan", x=str(x), y=str(y))
        tspan.text = line
        tspans.append(tspan)
        y += line_height
    return tspans

def update_svg(svg_file, replacements, ascii_text):
    tree = ET.parse(svg_file)
    root = tree.getroot()

    ns = {"svg": "http://www.w3.org/2000/svg"}

    # Atualiza campos simples
    for element_id, value in replacements.items():
        elem = root.find(f".//*[@id='{element_id}']")
        if elem is not None:
            elem.text = value

    # Atualiza ASCII
    ascii_elem = root.find(".//*[@id='ascii_art']")
    if ascii_elem is not None:
        ascii_elem.clear()
        ascii_elem.set("id", "ascii_art")
        ascii_elem.set("x", "55")
        ascii_elem.set("y", "95")
        ascii_elem.set("class", "ascii")

        for tspan in build_ascii_tspans(ascii_text):
            ascii_elem.append(tspan)

    tree.write(svg_file, encoding="utf-8", xml_declaration=False)

def main():
    if not GITHUB_TOKEN:
        raise RuntimeError("GH_TOKEN não definido nas variáveis de ambiente.")

    with open(ASCII_FILE, "r", encoding="utf-8") as f:
        ascii_text = f.read()

    replacements = fetch_github_data()

    for svg_file in SVG_FILES:
        update_svg(svg_file, replacements, ascii_text)

    print("SVGs atualizados com sucesso.")

if __name__ == "__main__":
    main()