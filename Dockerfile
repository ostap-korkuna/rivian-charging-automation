FROM python:3.12

WORKDIR /usr/src/app

COPY charging_automation/* ./

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "-u", "./main.py"]
