output "control_plane_ip" {
  description = "Control plane node IP address"
  value       = try(proxmox_virtual_environment_vm.control_plane.ipv4_addresses[1][0], "pending")
}

output "control_plane_name" {
  description = "Control plane node name"
  value       = proxmox_virtual_environment_vm.control_plane.name
}

output "worker_ips" {
  description = "Worker node IP addresses"
  value = {
    for idx, worker in proxmox_virtual_environment_vm.workers :
    worker.name => try(worker.ipv4_addresses[1][0], "pending")
  }
}

output "milvus_ip" {
  description = "Milvus node IP address"
  value       = try(proxmox_virtual_environment_vm.milvus_node.ipv4_addresses[1][0], "pending")
}

output "inference_ip" {
  description = "Inference node IP address"
  value       = try(proxmox_virtual_environment_vm.inference_node.ipv4_addresses[1][0], "pending")
}

output "ssh_connection_strings" {
  description = "SSH connection strings for all nodes"
  value = merge(
    {
      (proxmox_virtual_environment_vm.control_plane.name) = "ssh ${var.vm_user}@${try(proxmox_virtual_environment_vm.control_plane.ipv4_addresses[1][0], "pending")}"
    },
    {
      for idx, worker in proxmox_virtual_environment_vm.workers :
      worker.name => "ssh ${var.vm_user}@${try(worker.ipv4_addresses[1][0], "pending")}"
    },
    {
      (proxmox_virtual_environment_vm.milvus_node.name) = "ssh ${var.vm_user}@${try(proxmox_virtual_environment_vm.milvus_node.ipv4_addresses[1][0], "pending")}"
    },
    {
      (proxmox_virtual_environment_vm.inference_node.name) = "ssh ${var.vm_user}@${try(proxmox_virtual_environment_vm.inference_node.ipv4_addresses[1][0], "pending")}"
    }
  )
}

output "kubeconfig_command" {
  description = "Command to retrieve kubeconfig"
  value       = "ssh ${var.vm_user}@${try(proxmox_virtual_environment_vm.control_plane.ipv4_addresses[1][0], "pending")} 'sudo cat /etc/rancher/k3s/k3s.yaml'"
}

output "storage_node_ip" {
  description = "Storage node (MinIO host) IP address"
  value       = try(proxmox_virtual_environment_vm.storage_node.ipv4_addresses[1][0], "pending")
}

output "storage_node_ssh" {
  description = "SSH command for the storage node"
  value       = "ssh ${var.vm_user}@${try(proxmox_virtual_environment_vm.storage_node.ipv4_addresses[1][0], "pending")}"
}

output "minio_rotate_password_runbook" {
  description = "First-boot runbook: rotate MinIO root credentials"
  value       = <<-EOT
    Storage node provisions MinIO with placeholder credentials (admin / changeme-rotate-on-first-boot).
    Before any consumer points at this host, rotate the password:

    ssh ubuntu@${try(proxmox_virtual_environment_vm.storage_node.ipv4_addresses[1][0], "<storage-node-ip>")}
    sudo vim /etc/default/minio
      # set MINIO_ROOT_USER / MINIO_ROOT_PASSWORD to match the in-cluster MinIO secret
      # (kubectl -n minio get secret minio -o jsonpath='{.data.rootUser}' | base64 -d)
      # (kubectl -n minio get secret minio -o jsonpath='{.data.rootPassword}' | base64 -d)
    sudo systemctl restart minio
    curl http://localhost:9000/minio/health/live   # expect HTTP 200
  EOT
}
