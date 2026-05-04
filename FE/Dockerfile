FROM nginx:stable-alpine

ARG NGINX_CONFIG_PATH=/etc/nginx/conf.d/default.conf \
    NGINX_ASSETS_PATH=/usr/share/nginx/html \
    NGINX_CONFIG_FILE=./config/nginx.conf

COPY ./dist $NGINX_ASSETS_PATH

COPY $NGINX_CONFIG_FILE $NGINX_CONFIG_PATH

CMD ["nginx", "-g", "daemon off;"]