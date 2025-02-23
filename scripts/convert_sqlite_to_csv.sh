#!/usr/bin/env bash

# For some reason, table names have \r in them?
TABLES=$(sqlite-utils tables nz_government_v2.db --csv --no-headers | tr -d '\r')
EXPORT_FOLDER="tables_csv_v2"

mkdir -p "$EXPORT_FOLDER"

for table in $TABLES; do
    echo "Exporting $table to ${EXPORT_FOLDER}/${table}.csv"
    sqlite-utils query nz_government_v2.db "SELECT * FROM $table" --csv > "${EXPORT_FOLDER}/${table}.csv"
done