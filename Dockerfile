FROM python:3.13.0-alpine3.20

RUN apk add --no-cache gcc python3-dev musl-dev linux-headers bash

WORKDIR /usr/src/app

COPY requirements.txt ./

RUN pip install --no-cache-dir --upgrade pip \
  && pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x setup.sh

CMD [ "/bin/bash", "/usr/src/app/setup.sh" ]
