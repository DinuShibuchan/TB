import httpx
from typing import Optional

class WikipediaService:
    async def get_summary(self, title: str) -> Optional[str]:
        if not title:
            return None
        # Format the title for Wikipedia (e.g., replace spaces with underscores)
        formatted_title = title.strip().replace(" ", "_")
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{formatted_title}"
        headers = {
            "User-Agent": "AITravelPlanner/1.0 (contact@example.com)"
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, timeout=5.0)
                if response.status_code == 200:
                    data = response.json()
                    return data.get("extract")
                return None
        except Exception:
            return None
