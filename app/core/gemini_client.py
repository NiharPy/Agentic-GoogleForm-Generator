from google import genai
from app.core.settings import settings


class GeminiClient:
    def __init__(self):
        self.client = genai.Client(
            api_key=settings.GOOGLE_API_KEY,
            http_options={"api_version": "v1"}
        )

    async def generate(self, prompt: str) -> str:
        response = await self.client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )

        return response.text
