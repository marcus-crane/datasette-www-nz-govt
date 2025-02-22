#!/usr/bin/env bash

TABLES=$(sqlite-utils tables nz_government.db --csv --no-headers)
EXPORT_FOLDER="tables_csv"

mkdir -p "$EXPORT_FOLDER"

for table in $TABLES; do
    clean_table=$(echo "$table" | tr -d '?')
    echo "Exporting $clean_table to ${EXPORT_FOLDER}/${table}.csv"
    sqlite-utils query nz_government.db "SELECT * FROM $clean_table" --csv > "${EXPORT_FOLDER}/${clean_table}.csv"
done