#!/bin/bash

# vars
BACKUP_DIR=~/Workplace/odoo_backups
ODOO_DATABASE=afromerge_0.2
S3_BUCKET=afromerge-backup

# create a backup directory
mkdir -p ${BACKUP_DIR}

# create a backup
wget --post-data 'master_pwd=2L$@DrliYD8lg282&name=afromerge_0.2&backup_format=zip' -O ${BACKUP_DIR}/${ODOO_DATABASE}.$(date +%F).zip http://localhost:8069/web/database/backup

aws s3 cp ${BACKUP_DIR}/${ODOO_DATABASE}.$(date +%F).zip s3://${S3_BUCKET}/

# delete old backups
find ${BACKUP_DIR} -type f -mtime +7 -name "${ODOO_DATABASE}.*.zip" -delete
