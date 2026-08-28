import os
from google import genai

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "./credentials.json"
os.environ["GOOGLE_CLOUD_PROJECT"] = "gd-gcp-gridu-genai"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"

if __name__ == '__main__':
    client = genai.Client(
        vertexai=True,
        project='gd-gcp-gridu-genai',
        location='us-central1'
    )

    response = client.models.generate_content(
        model='gemini-2.5-flash', 
        contents='Why is sky blue?'
    )
    print(response.text)
