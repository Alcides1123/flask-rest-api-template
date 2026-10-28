#!/bin/sh

echo "Start run entrypoint script..."

# WSGI entrypoint (module:variable); wsgi.py builds the app from APP_SETTINGS_MODULE
API_ENTRYPOINT="${API_ENTRYPOINT:-wsgi:app}"

echo "Database:" $DATABASE

if [ "$DATABASE" = "postgres" ]
then
    echo "Waiting for postgres..."

    while ! psql -h $BBDD_HOST -U $POSTGRES_USER -d $POSTGRES_DB
    do
        echo "Waiting for PostgreSQL..."
        sleep 0.5
    done

    echo "PostgreSQL started"
fi

echo "Enviroment:" $APP_ENV

if [ "$APP_ENV" = "local" ]; then
    echo "Start create database"
    flask create-db
    echo "Done create database"

    echo "Start check user-admin"
    flask create-user-admin
    echo "Done init user-admin"

    echo "Run app with gunicorn server..."
    gunicorn -c ./gunicorn/gunicorn_config.py "$API_ENTRYPOINT";
fi

if [ "$APP_ENV" = "production" ]; then
    echo "Run app with gunicorn server..."
    gunicorn --bind "$API_HOST:$API_PORT" "$API_ENTRYPOINT" --timeout 10 --workers 4;
fi
