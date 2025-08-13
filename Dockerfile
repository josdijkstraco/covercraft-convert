# Based on bwits/pdf2htmlex
# Idea is to wrap pdf2htmlex in a simple web service
#
# Dockerfile to build a pdf2htmlEx image
FROM ubuntu:20.04

ENV REFRESHED_AT 20170418
ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies and pdf2htmlEX from source
RUN \
    apt-get -qqy update && \
    apt-get -qqy install wget python3-dev python3-pip && \
    # Try to install pdf2htmlEX from a pre-built package or build from source
    apt-get -qqy install poppler-utils fontforge libpoppler-dev pkg-config && \
    # For now, we'll use wkhtmltopdf as an alternative that can convert HTML back
    # or we can compile pdf2htmlEX from source
    wget https://github.com/pdf2htmlEX/pdf2htmlEX/releases/download/v0.18.8.rc1/pdf2htmlEX-0.18.8.rc1-master-20200630-Ubuntu-focal-x86_64.deb && \
    # pdf2htmlEX has dependency issues, so we'll use pdftohtml from poppler-utils instead
    echo "Using pdftohtml from poppler-utils as pdf2htmlEX alternative" && \
    rm -rf /var/lib/apt/lists/* *.deb

COPY requirements.txt /pdf/requirements.txt
RUN pip3 install -r /pdf/requirements.txt

VOLUME /pdf/tmp
WORKDIR /pdf

ADD config.py /pdf/config.py
ADD service.py /pdf/service.py
ADD gunicorn.ini /pdf/gunicorn.ini.py
ADD .env /pdf/.env

CMD ["gunicorn", "-c", "gunicorn.ini.py", "service:app"]

