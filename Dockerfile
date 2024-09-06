# Dockerfile that builds a fully functional image of your app.
#
# This image installs all Python dependencies for your application. It's based
# on Almalinux (https://github.com/inveniosoftware/docker-invenio)
# and includes Pip, Pipenv, Node.js, NPM and some few standard libraries
# Invenio usually needs.
#
# Note: It is important to keep the commands in this file in sync with your
# bootstrap script located in ./scripts/bootstrap.

FROM registry.cern.ch/inveniosoftware/almalinux:1

COPY site ./site
COPY Pipfile Pipfile.lock ./
RUN pip install invenio-cli
RUN pipenv install --deploy --system
RUN pip install debugpy
RUN pip install celery

WORKDIR /app

ENV INVENIO_INSTANCE_PATH /opt/invenio/var/instance

COPY ./docker/uwsgi/ ${INVENIO_INSTANCE_PATH}
COPY ./docker/uwsgi/ ${INVENIO_INSTANCE_PATH}
COPY ./invenio.cfg ${INVENIO_INSTANCE_PATH}
COPY ./templates/ ${INVENIO_INSTANCE_PATH}/templates/
COPY ./app_data/ ${INVENIO_INSTANCE_PATH}/app_data/
COPY ./translations/ ${INVENIO_INSTANCE_PATH}/translations/
COPY ./ .

RUN cp -r ./static/. ${INVENIO_INSTANCE_PATH}/static/ && \
    cp -r ./assets/. ${INVENIO_INSTANCE_PATH}/assets/ && \
    invenio collect --verbose  && \
    invenio webpack buildall


CMD ["python", "-m", "debugpy", "--listen", "0.0.0.0:5678", "--wait-for-client", "invenio", "run", "--host", "0.0.0.0", "--port", "5000"]
