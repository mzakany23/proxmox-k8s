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

output "k3s_token" {
  description = "K3s cluster token (sensitive)"
  value       = random_password.k3s_token.result
  sensitive   = true
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
    }
  )
}

output "kubeconfig_command" {
  description = "Command to retrieve kubeconfig"
  value       = "ssh ${var.vm_user}@${try(proxmox_virtual_environment_vm.control_plane.ipv4_addresses[1][0], "pending")} 'sudo cat /etc/rancher/k3s/k3s.yaml'"
}
