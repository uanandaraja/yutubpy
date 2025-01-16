from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import boto3
import logging
from botocore.config import Config
import yt_dlp
import tempfile
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://rangkumin.xyz", "http://localhost:4000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure R2 client
s3 = boto3.client(
    's3',
    endpoint_url=os.getenv('R2_ENDPOINT'),
    aws_access_key_id=os.getenv('R2_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('R2_SECRET_ACCESS_KEY'),
    config=Config(signature_version='s3v4'),
    region_name='auto'
)


class VideoURL(BaseModel):
    url: str


@app.post("/download")
async def download(video: VideoURL):
    try:
        temp_dir = tempfile.mkdtemp()

        ydl_opts = {
            'format': 'bestaudio[ext=mp3]/bestaudio',
            'cookiefile': '/app/cookies.txt',
            'outtmpl': f'{temp_dir}/%(id)s.%(ext)s'
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video.url, download=True)
            ext = info['ext']
            filename = f"{temp_dir}/{info['id']}.{ext}"

            # Upload to R2
            bucket_name = os.getenv('R2_BUCKET_NAME')
            object_key = f"{info['id']}.{ext}"

            s3.upload_file(filename, bucket_name, object_key)

            # Generate signed URL
            url = s3.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': bucket_name,
                    'Key': object_key
                },
                ExpiresIn=3600  # URL expires in 1 hour
            )

            # Cleanup
            os.remove(filename)
            os.rmdir(temp_dir)

            return {"url": url}

    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "7000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
