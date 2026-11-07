from bs4 import BeautifulSoup

class ContentParser:
    def __init__(self, content):
        self.content = content
        self.soup = BeautifulSoup(content, "html.parser")

    def get_title(self) -> str | None:
        title = self.soup.find("title")
        return title.get_text(strip=True) if title else None

    def get_headers(self) -> list[str]:
        headers = self.soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]) 
        return " ".join(header.get_text(strip=True) for header in headers) if headers else None

    def get_bold_text(self) -> list[str]:
        bold = self.soup.find_all(["b", "strong"])
        return " ".join(element.get_text(strip=True) for element in bold) if bold else None

    # Currently no modifications for bolded text double returning
    # This will also read the title again
    def get_clean_text(self) -> str:
        return self.soup.get_text(separator="\n", strip=True)

    def parse(self) -> dict:
        return {
            "title": self.get_title(),
            "header": self.get_headers(),
            "bold" : self.get_bold(),
            "clean_text": self.get_clean_text()
        }
