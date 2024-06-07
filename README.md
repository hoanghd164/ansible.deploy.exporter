**Node Exporter Deployment**
# Deploy
ansible-playbook playbook/node-exporter-playbook.yml \
    -i ../inventory.ini \
    --user hoanghd3 \
    --key-file /home/hoanghd3/.ssh/id_rsa \
    -e "host_group=groups-vng-lab run_deploy_node_exporter=true" \
    --tag node_exporter \
    --become \
    --ask-become-pass \
    -l "backup-infra-21-4 backup-infra-21-5"

# Destroy
ansible-playbook playbook/node-exporter-playbook.yml \
    -i ../inventory.ini \
    --user root \
    --key-file ./sshkey/id_rsa \
    -e "host_group=groups-vng-lab run_destroy_node_exporter=true" \
    --tag node_exporter \
    -l "staging-pri-81 staging-pri-82 staging-pri-83"

**Backup Infras Exporter Deployment**
# Deploy
ansible-playbook playbook/backup-infras-exporter-playbook.yml \
    -i ../inventory.ini \
    --user hoanghd3 \
    --key-file /home/hoanghd3/.ssh/id_rsa \
    -e "host_group=groups-backup-infras run_deploy_backup_infras_exporter=true" \
    --tags backup_infras_exporter \
    --become \
    --ask-become-pass \
    -l "backup-infra-21-4 backup-infra-21-5"

# Destroy
ansible-playbook playbook/backup-infras-exporter-playbook.yml \
    -i ../inventory.ini \
    --user root \
    --key-file ./sshkey/id_rsa \
    -e "host_group=groups-vng-lab run_destroy_backup_infras_exporter=true" \
    --tag backup_infras_exporter \
    -l "staging-pri-81 staging-pri-82 staging-pri-83 staging-pri-84 staging-pri-85"