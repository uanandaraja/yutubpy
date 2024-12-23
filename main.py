from fastapi import FastAPI, HTTPException
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
            'format': 'worstaudio',
            'cookiesfile': 'cookies.txt',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '64',
            }],
            'outtmpl': f'{temp_dir}/%(id)s.%(ext)s'
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video.url, download=True)
            filename = f"{temp_dir}/{info['id']}.mp3"

            # Upload to R2
            bucket_name = os.getenv('R2_BUCKET_NAME')
            object_key = f"{info['id']}.mp3"

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
    uvicorn.run(app, host="0.0.0.0", port=8080)
