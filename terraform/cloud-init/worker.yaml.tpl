#cloud-config
hostname: ${hostname}
manage_etc_hosts: true

# Update packages and install dependencies
package_update: true
package_upgrade: true

packages:
  - curl
  - wget
  - git
  - vim
  - htop
  - net-tools
  - qemu-guest-agent

# Write k3s token to file
write_files:
  - path: /etc/rancher/k3s/k3s-token
    content: ${k3s_token}
    permissions: '0600'

# Install and configure k3s worker
runcmd:
  # Start qemu-guest-agent
  - systemctl enable qemu-guest-agent
  - systemctl start qemu-guest-agent

  # Disable swap (required for k8s)
  - swapoff -a
  - sed -i '/ swap / s/^\(.*\)$/#\1/g' /etc/fstab

  # Load required kernel modules
  - modprobe br_netfilter
  - modprobe overlay
  - echo "br_netfilter" > /etc/modules-load.d/k8s.conf
  - echo "overlay" >> /etc/modules-load.d/k8s.conf

  # Configure sysctl for k8s
  - |
    cat <<EOF > /etc/sysctl.d/k8s.conf
    net.bridge.bridge-nf-call-iptables = 1
    net.bridge.bridge-nf-call-ip6tables = 1
    net.ipv4.ip_forward = 1
    EOF
  - sysctl --system

  # Wait for control plane to be ready
  - sleep 60

  # Install k3s agent (worker)
  - curl -sfL https://get.k3s.io | INSTALL_K3S_CHANNEL=${k3s_version} K3S_URL=https://${control_plane_ip}:6443 K3S_TOKEN=${k3s_token} sh -

  # Create completion message
  - echo "K3s worker node installation complete!" > /var/log/k3s-setup-complete.log
  - date >> /var/log/k3s-setup-complete.log

# Set timezone
timezone: UTC

# Final message
final_message: "K3s worker node is ready after $UPTIME seconds"
