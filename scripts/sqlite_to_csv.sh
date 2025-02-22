#!/usr/bin/env bash

TABLES=$(sqlite-utils tables nz_government.db --csv --no-headers | tr -d '\r')
EXPORT_FOLDER="tables_csv"

mkdir -p "$EXPORT_FOLDER"

for table in $TABLES; do
    echo "Exporting $table to ${EXPORT_FOLDER}/${table}.csv"
    sqlite-utils query nz_government.db "SELECT * FROM $table" --csv > "${EXPORT_FOLDER}/${table}.csv"
done