# Accept a build argument to set the base image for building assets
ARG BASE_IMAGE=turath-inveniordm:latest

# Use the build argument for the base image in the first stage
FROM ${BASE_IMAGE} AS invenio

# Set the working directory and copy files
WORKDIR /opt/invenio/var/instance/static

# Use the official Nginx image for serving the built assets
FROM nginx:latest

COPY --from=invenio /opt/invenio/var/instance/static /opt/invenio/var/instance/static
# Copy the Nginx configuration
COPY invenio.conf /etc/nginx/conf.d/invenio.conf