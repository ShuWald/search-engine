from bs4 import BeautifulSoup

class ContentParser:
    def __init__(self, content):
        self.content = content
        self.soup = BeautifulSoup(content, "html.parser")

    def get_title(self) -> str | None:
        title = self.soup.find("title")
        return title.get_text(strip=True) if title else None

    # Currently no modifications for bolded text double returning
    # This will also read the title again
    def get_clean_text(self) -> str:
        return self.soup.get_text(separator="\n", strip=True)

    def parse(self) -> dict:
        return {
            "title": self.get_title(),
            "clean_text": self.get_clean_text()
        }
