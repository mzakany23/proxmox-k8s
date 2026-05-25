#cloud-config
hostname: ${hostname}
manage_etc_hosts: true

users:
  - name: ${username}
    groups: sudo
    shell: /bin/bash
    sudo: ALL=(ALL) NOPASSWD:ALL
    ssh_authorized_keys:
      - ${ssh_public_key}

# Update packages and install dependencies
package_update: true
package_upgrade: true

packages:
  - curl
  - wget
  - vim
  - htop
  - net-tools
  - qemu-guest-agent

# MinIO server installation (standalone, systemd-managed).
# Initial root credentials are placeholders — operator MUST rotate
# before exposing this service. See PR description for the runbook.
write_files:
  - path: /etc/default/minio
    permissions: '0600'
    owner: root:root
    content: |
      # MinIO server configuration
      # ROTATE THESE BEFORE ANY CONSUMER POINTS AT THIS HOST.
      MINIO_ROOT_USER=admin
      MINIO_ROOT_PASSWORD=changeme-rotate-on-first-boot
      MINIO_VOLUMES=/var/lib/minio/data
      MINIO_OPTS="--address :9000 --console-address :9001"

  - path: /etc/systemd/system/minio.service
    permissions: '0644'
    owner: root:root
    content: |
      [Unit]
      Description=MinIO Object Storage
      Documentation=https://min.io/docs/minio/linux/index.html
      Wants=network-online.target
      After=network-online.target
      AssertFileIsExecutable=/usr/local/bin/minio

      [Service]
      User=minio-user
      Group=minio-user
      ProtectProc=invisible
      EnvironmentFile=/etc/default/minio
      ExecStart=/usr/local/bin/minio server $MINIO_OPTS $MINIO_VOLUMES
      Restart=always
      RestartSec=5s
      LimitNOFILE=1048576
      TasksMax=infinity
      TimeoutStopSec=30s
      SendSIGRTMIN+15=no

      [Install]
      WantedBy=multi-user.target

runcmd:
  # Start qemu-guest-agent so Terraform/Proxmox can see the VM's IP
  - systemctl enable qemu-guest-agent
  - systemctl start qemu-guest-agent

  # Create the minio system user + data directory
  - groupadd -r minio-user || true
  - useradd -M -r -g minio-user -s /usr/sbin/nologin minio-user || true
  - mkdir -p /var/lib/minio/data
  - chown -R minio-user:minio-user /var/lib/minio

  # Download and install the MinIO server binary
  # Pin to the same release the in-cluster MinIO runs so behavior matches
  - wget -q -O /usr/local/bin/minio https://dl.min.io/server/minio/release/linux-amd64/archive/minio.RELEASE.2024-12-18T13-15-44Z
  - chmod +x /usr/local/bin/minio

  # Optional: mc client for local administration
  - wget -q -O /usr/local/bin/mc https://dl.min.io/client/mc/release/linux-amd64/mc
  - chmod +x /usr/local/bin/mc

  # Enable + start MinIO
  - systemctl daemon-reload
  - systemctl enable minio
  - systemctl start minio

  # Completion marker
  - echo "MinIO standalone install complete at $(date)" > /var/log/minio-setup-complete.log
  - echo "ROTATE THE ROOT PASSWORD: edit /etc/default/minio then 'systemctl restart minio'" >> /var/log/minio-setup-complete.log

# Set timezone
timezone: UTC

# Final message
final_message: "Storage node ready in $UPTIME seconds. MinIO listening on :9000 (S3) and :9001 (console). ROTATE THE ROOT PASSWORD."
