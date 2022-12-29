FROM python:3.7.16-slim-bullseye

RUN pip install pydrive

RUN pip install numpy

RUN apt-get update

RUN apt-get install ffmpeg libsm6 libxext6 -y

RUN pip install opencv-python