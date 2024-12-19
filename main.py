from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import io
import tempfile
import logging
import yt_dlp
from starlette.background import BackgroundTask

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()


class VideoURL(BaseModel):
    url: str


async def download_and_convert(url: str):
    try:
        logger.info(f"Starting download for URL: {url}")

        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': '%(id)s.%(ext)s'
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            ydl_opts['outtmpl'] = f'{temp_dir}/%(id)s.%(ext)s'

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info("Downloading and converting")
                info = ydl.extract_info(url, download=True)
                filename = f"{temp_dir}/{info['id']}.mp3"

                logger.info("Reading MP3 file")
                with open(filename, 'rb') as f:
                    mp3_data = f.read()
                return mp3_data

    except Exception as e:
        logger.error(f"Error during processing: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error during processing: {str(e)}")


@app.post("/download")
async def download(video: VideoURL):
    try:
        logger.info(f"Received request for URL: {video.url}")
        temp_dir = tempfile.mkdtemp()

        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': f'{temp_dir}/%(id)s.%(ext)s'
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video.url, download=True)
            filename = f"{temp_dir}/{info['id']}.mp3"

            async def file_iterator():
                with open(filename, 'rb') as f:
                    while chunk := f.read(8192):
                        yield chunk

            def cleanup():
                import os
                os.remove(filename)
                os.rmdir(temp_dir)
                logger.info(f"Cleaned up {filename}")

            return StreamingResponse(
                file_iterator(),
                media_type="audio/mpeg",
                headers={
                    "Content-Disposition": f'attachment; filename="audio.mp3"'},
                background=BackgroundTask(cleanup)
            )

    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
