FROM python:3.10-slim-bullseye

RUN mkdir /workspace \
    && pip install scrapy selenium-screenshot selenium webdriver-manager
RUN apt update \
    && apt install -y -qq --no-install-recommends --no-install-suggests \
           firefox-esr
ADD screenshotter.py /workspace
WORKDIR /workspace

ENTRYPOINT ["python3", "/workspace/screenshotter.py"]
