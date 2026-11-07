from urllib.parse import urlsplit, urlunsplit


class Url:
    def __init__(self, url: str):
        self.url = self._normalize(url)

    # Hello isn't this familiar
    # Normalize a URL, lowercases the scheme and netloc, ensures a path, and optionally keeps the query and fragment
    # Dunno if the urls will even have queries or fragments, @ archbird can grep? or we can log and look for hits
    def _normalize(self, url, keepQuery=True, keepFragment=True):
        parts = urlsplit(url)
        scheme = parts.scheme.lower()
        netloc = parts.netloc.lower()
        path = parts.path.rstrip("/") or "/"
        query = parts.query if keepQuery else ""
        fragment = parts.fragment if keepFragment else ""

        # Someone needs to check to see if these are even necessary.
        # @archbird can use grep? or we can just add logging and see if it ever hits for big dataset
        if netloc.startswith("www."):
            netloc = netloc[4:]
        if scheme == "https" and netloc.endswith(":443"):
            netloc = netloc[:-4]
        elif scheme == "http" and netloc.endswith(":80"):
            netloc = netloc[:-3]

        return urlunsplit((scheme, netloc, path, query, fragment))



class DocuID:
    def __init__(self, url: Url = None, url_string: str = None):
        if url is None:
            url = Url(url_string)
        self.url = url
        self.doc_id = self._hash_url(url)

    def _hash_url(self, url: Url) -> int:
        return hash(url.url)