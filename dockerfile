FROM python:3.10.6-slim-buster

RUN pip3 install python-dotenv 
RUN pip3 install discord-py-interactions
RUN pip3 install interactions-tasks