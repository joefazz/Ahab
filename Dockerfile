FROM python:3

ADD main.py /

ADD chron_sch.py /

ADD unused_containers.txt /

RUN pip install docker python-crontab

CMD [ "python", "/chron_sch.py" ]