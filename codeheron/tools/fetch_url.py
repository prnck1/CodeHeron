from .base import Tool
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from bs4 import BeautifulSoup
import json

class FetchUrlTool(Tool):
    name = "fetch_url"
    description = "Fetch text content from a public webpage or API URL."

    parameters = {
        "type" : "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The HTTP or HTTPS URL to fetch.",
            },
        },
        "required" : ["url"],
    }

    def execute(self, url: str) -> str:
        if not isinstance(url,str) or not url.strip():
            return "Error: URL must be a non-empty string."
        url = url.strip()

        try:   
            parsed = urlsplit(url)

            if parsed.scheme not in {"http", "https"}:
                return "Error: only HTTP and HTTPS URLS are supported."

            if not parsed.hostname:
                return "Error: URL must contain a hostname."

            if parsed.username is not None or parsed.password is not None:
                return "Error: URLs containing credentials are not supported."

            _ = parsed.port

        except ValueError:
            return "Error: invalid URL."
            
        max_bytes = 1_000_000

        try:
            request = Request(
                url,
                headers={"User-Agent": "CodeHeron-Fetch/0.1"},
                method="GET",
            )
            with urlopen(request, timeout=10) as response:
                content_type = response.headers.get_content_type()
                is_text = content_type.startswith("text/")
                is_json = (
                    content_type == "application/json"
                    or content_type.endswith("+json")
                )

                if not (is_text or is_json):
                    return f"Error: unsupported content type: {content_type}"



                data = response.read(max_bytes + 1)

                if len(data) > max_bytes:
                    return "Error: response exceeds the 1,000,000-byte limit."

                encoding = response.headers.get_content_charset()  or "utf-8"
                text = data.decode(encoding, errors="replace")

                if content_type == "text/html":
                    soup = BeautifulSoup(text, "html.parser")

                    for tag in soup.find_all(["script", "style", "template"]):
                        tag.decompose()
                    text = soup.get_text(separator="\n", strip=True)

                elif is_json:
                    try:
                        value = json.loads(text)
                    except json.JSONDecodeError:
                        return "Error: response claims to be JSON but contains invalid JSON."

                    text = json.dumps(
                        value,
                        ensure_ascii=False,
                        indent=2,
                    )

                max_chars = 12_000

                if len(text) > max_chars:
                    text = (
                        text[:max_chars]
                        + "\n[Content truncated: showing the first 12000 characters.]"
                    )

                return text

        except HTTPError as e:
            return f"Error: HTTP sataus {e.code}."
        except URLError as e:
            return f"Error: request failed: {e.reason}"
        except TimeoutError:
            return "Error: network operation timed out."
        except (OSError, ValueError, LookupError) as e:
            return f"Error: could not read response: {e}"
        
